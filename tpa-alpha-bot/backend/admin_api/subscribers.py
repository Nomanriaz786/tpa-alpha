import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from admin_api.common import build_affiliate_link, utcnow, verify_admin_token
from config import get_settings
from database import get_session
from schemas import SubscriberExtendRequest, SubscriberListResponse, SubscriberResponse
from services.discord_service import get_discord_service
from services.guild_settings import load_effective_guild_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def build_subscriber_where_sql(search: Optional[str], active_only: bool) -> tuple[str, dict[str, object]]:
    where_clauses = []
    params: dict[str, object] = {}

    if active_only:
        where_clauses.append("subscribers.is_active = TRUE AND subscribers.expires_at > NOW()")

    if search:
        where_clauses.append(
            """
            (
                subscribers.discord_username ILIKE :search
                OR subscribers.discord_id ILIKE :search
                OR subscribers.tradingview_username ILIKE :search
                OR subscribers.email ILIKE :search
                OR member_affiliate.code ILIKE :search
            )
            """
        )
        params["search"] = f"%{search}%"

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return where_sql, params


@router.get("/subscribers", response_model=SubscriberListResponse)
async def list_subscribers(
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    active_only: bool = False,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        where_sql, params = build_subscriber_where_sql(search=search, active_only=active_only)

        total = int(
            await session.scalar(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM subscribers
                    LEFT JOIN affiliates AS member_affiliate
                        ON member_affiliate.discord_id = subscribers.discord_id
                        AND member_affiliate.type = 'member'
                        AND member_affiliate.is_active = TRUE
                    {where_sql}
                    """
                ),
                params,
            )
            or 0
        )
        per_page = 20
        offset = (page - 1) * per_page
        params["limit"] = per_page
        params["offset"] = offset

        result = await session.execute(
            text(
                f"""
                SELECT
                    subscribers.*,
                    member_affiliate.code AS owned_referral_code
                FROM subscribers
                LEFT JOIN affiliates AS member_affiliate
                    ON member_affiliate.discord_id = subscribers.discord_id
                    AND member_affiliate.type = 'member'
                    AND member_affiliate.is_active = TRUE
                {where_sql}
                ORDER BY subscribers.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        subscribers = []
        for row in result.mappings().all():
            subscriber = SubscriberResponse.model_validate(dict(row)).model_copy(
                update={
                    "owned_referral_code": row.get("owned_referral_code"),
                    "owned_referral_link": build_affiliate_link(row.get("owned_referral_code")),
                }
            )
            subscribers.append(subscriber)

    return SubscriberListResponse(items=subscribers, total=total, page=page, per_page=per_page)


@router.post("/subscribers/{subscriber_id}/extend")
async def extend_subscriber(
    subscriber_id: str,
    request: SubscriberExtendRequest,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        discord_service = get_discord_service()
        result = await session.execute(
            text("SELECT * FROM subscribers WHERE id = :id"),
            {"id": subscriber_id},
        )
        subscriber_row = result.mappings().one_or_none()

        if not subscriber_row:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        expires_at = subscriber_row["expires_at"]
        new_expires = (
            expires_at + timedelta(days=30 * request.months)
            if expires_at
            else utcnow() + timedelta(days=30 * request.months)
        )
        months_paid = subscriber_row["months_paid"] + request.months

        await session.execute(
            text(
                "UPDATE subscribers SET expires_at = :expires_at, months_paid = :months_paid WHERE id = :id"
            ),
            {"expires_at": new_expires, "months_paid": months_paid, "id": subscriber_id},
        )

        await discord_service.dm_user(
            subscriber_row["discord_id"],
            f"Your TPA Alpha membership has been extended by {request.months} month(s). New expiry date: {new_expires.strftime('%B %d, %Y')}",
        )
        logger.info(
            "Extended subscriber %s by %s months",
            subscriber_row["tradingview_username"],
            request.months,
        )

        return {"status": "extended", "new_expires": new_expires}


@router.delete("/subscribers/{subscriber_id}")
async def revoke_subscriber(
    subscriber_id: str,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        discord_service = get_discord_service()
        settings = get_settings()
        result = await session.execute(
            text("SELECT * FROM subscribers WHERE id = :id"),
            {"id": subscriber_id},
        )
        subscriber_row = result.mappings().one_or_none()

        if not subscriber_row:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        guild_settings = await load_effective_guild_settings(session)
        vip_role_id = guild_settings.vip_role_id or settings.VIP_ROLE_ID
        if vip_role_id:
            await discord_service.remove_role(subscriber_row["discord_id"], vip_role_id)
        else:
            logger.warning("VIP role is not configured; skipping Discord role removal for %s", subscriber_row["discord_id"])
        await session.execute(
            text("UPDATE subscribers SET is_active = FALSE WHERE id = :id"),
            {"id": subscriber_id},
        )
        await discord_service.dm_user(
            subscriber_row["discord_id"],
            "Your TPA Alpha subscription has been revoked by an administrator.",
        )
        logger.info("Revoked subscriber %s", subscriber_row["tradingview_username"])
        return {"status": "revoked"}
