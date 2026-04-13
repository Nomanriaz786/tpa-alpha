import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from admin_api.common import build_affiliate_link, utcnow, verify_admin_token
from database import get_session
from schemas import (
    AffiliateCreate,
    AffiliateDetailResponse,
    AffiliateListResponse,
    AffiliateResponse,
    AffiliateUpdate,
    CommissionMarkPaidRequest,
    SubscriberListResponse,
    SubscriberResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/affiliates", response_model=AffiliateListResponse)
async def list_affiliates(
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    active_only: bool = False,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        where_clauses = []
        params: dict[str, object] = {}

        if active_only:
            where_clauses.append("is_active = TRUE")

        if search:
            where_clauses.append("(code ILIKE :search OR name ILIKE :search OR discord_id ILIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        total = int(
            await session.scalar(text(f"SELECT COUNT(*) FROM affiliates{where_sql}"), params) or 0
        )
        per_page = 20
        offset = (page - 1) * per_page
        params["limit"] = per_page
        params["offset"] = offset

        result = await session.execute(
            text(
                f"SELECT * FROM affiliates{where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        affiliates = []
        for row in result.mappings().all():
            affiliate = AffiliateResponse.model_validate(dict(row)).model_copy(
                update={"affiliate_link": build_affiliate_link(row["code"])}
            )
            affiliates.append(affiliate)

    return AffiliateListResponse(items=affiliates, total=total, page=page, per_page=per_page)


@router.post("/affiliates", response_model=AffiliateResponse)
async def create_affiliate(
    request: AffiliateCreate,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        affiliate_id = str(uuid.uuid4())
        created_at = utcnow()
        # Default commission to 0 for new promos (not used for discount-only codes)
        commission_percent = 0.0
        
        await session.execute(
            text(
                """
                INSERT INTO affiliates (
                    id, code, discord_id, name, type, parent_id, discount_percent,
                    commission_percent, usage_limit, is_active, created_at
                )
                VALUES (
                    :id, :code, :discord_id, :name, :type, :parent_id, :discount_percent,
                    :commission_percent, :usage_limit, :is_active, :created_at
                )
                """
            ),
            {
                "id": affiliate_id,
                "code": request.code,
                "discord_id": request.discord_id,
                "name": request.name,
                "type": request.type,
                "parent_id": request.parent_id,
                "discount_percent": float(request.discount_percent),
                "commission_percent": commission_percent,
                "usage_limit": request.usage_limit,
                "is_active": request.is_active,
                "created_at": created_at,
            },
        )
        logger.info("Created affiliate %s with code %s", request.name, request.code)

    return AffiliateResponse(
        id=affiliate_id,
        code=request.code,
        discord_id=request.discord_id,
        name=request.name,
        type=request.type,
        discount_percent=float(request.discount_percent),
        commission_percent=commission_percent,
        payout_wallet=None,
        usage_limit=request.usage_limit,
        is_active=request.is_active,
        created_at=created_at,
        affiliate_link=build_affiliate_link(request.code),
    )


@router.get("/affiliates/{affiliate_id}", response_model=AffiliateDetailResponse)
async def get_affiliate(
    affiliate_id: str,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        active_members = int(
            await session.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM subscribers
                    WHERE affiliate_code_used = :code
                      AND is_active = TRUE
                      AND (expires_at IS NULL OR expires_at > NOW())
                    """
                ),
                {"code": affiliate_row["code"]},
            )
            or 0
        )
        # Count all members who have ever used this code
        usage_count = int(
            await session.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM subscribers
                    WHERE affiliate_code_used = :code
                    """
                ),
                {"code": affiliate_row["code"]},
            )
            or 0
        )
        total_commissions_owed = float(
            await session.scalar(
                text(
                    """
                    SELECT COALESCE(SUM(amount_owed), 0)
                    FROM commissions
                    WHERE affiliate_id = :id AND is_paid = FALSE
                    """
                ),
                {"id": affiliate_id},
            )
            or 0
        )
        total_commissions_paid = float(
            await session.scalar(
                text(
                    """
                    SELECT COALESCE(SUM(amount_owed), 0)
                    FROM commissions
                    WHERE affiliate_id = :id AND is_paid = TRUE
                    """
                ),
                {"id": affiliate_id},
            )
            or 0
        )
        
        # Safely get optional columns that might not exist in older databases
        try:
            payout_wallet = affiliate_row["payout_wallet"]
        except:
            payout_wallet = None
        
        try:
            usage_limit = affiliate_row["usage_limit"]
        except:
            usage_limit = None

    return AffiliateDetailResponse(
        id=affiliate_row["id"],
        code=affiliate_row["code"],
        discord_id=affiliate_row["discord_id"],
        name=affiliate_row["name"],
        type=affiliate_row["type"],
        discount_percent=float(affiliate_row["discount_percent"]),
        commission_percent=float(affiliate_row["commission_percent"]),
        payout_wallet=payout_wallet,
        usage_limit=usage_limit,
        is_active=affiliate_row["is_active"],
        created_at=affiliate_row["created_at"],
        affiliate_link=build_affiliate_link(affiliate_row["code"]),
        active_members=active_members,
        usage_count=usage_count,
        total_commissions_owed=total_commissions_owed,
        total_commissions_paid=total_commissions_paid,
    )


@router.put("/affiliates/{affiliate_id}", response_model=AffiliateResponse)
async def update_affiliate(
    affiliate_id: str,
    request: AffiliateUpdate,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        update_fields: dict[str, object] = {}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.discount_percent is not None:
            update_fields["discount_percent"] = float(request.discount_percent)
        if request.commission_percent is not None:
            update_fields["commission_percent"] = float(request.commission_percent)
        if request.payout_wallet is not None:
            update_fields["payout_wallet"] = request.payout_wallet
        if request.usage_limit is not None:
            update_fields["usage_limit"] = request.usage_limit
        if request.is_active is not None:
            update_fields["is_active"] = request.is_active

        if update_fields:
            set_clauses = ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
            update_fields["id"] = affiliate_id
            await session.execute(
                text(f"UPDATE affiliates SET {set_clauses} WHERE id = :id"),
                update_fields,
            )
            logger.info("Updated affiliate %s", affiliate_id)

        # Safely get optional columns that might not exist in older databases
        try:
            payout_wallet = affiliate_row["payout_wallet"]
        except:
            payout_wallet = None
        
        try:
            usage_limit = affiliate_row["usage_limit"]
        except:
            usage_limit = None

    return AffiliateResponse(
        id=affiliate_row["id"],
        code=affiliate_row["code"],
        discord_id=affiliate_row["discord_id"],
        name=update_fields.get("name", affiliate_row["name"]),
        type=affiliate_row["type"],
        discount_percent=float(update_fields.get("discount_percent", affiliate_row["discount_percent"])),
        commission_percent=float(
            update_fields.get("commission_percent", affiliate_row["commission_percent"])
        ),
        payout_wallet=update_fields.get("payout_wallet", payout_wallet),
        usage_limit=update_fields.get("usage_limit", usage_limit),
        is_active=update_fields.get("is_active", affiliate_row["is_active"]),
        created_at=affiliate_row["created_at"],
        affiliate_link=build_affiliate_link(affiliate_row["code"]),
    )


@router.delete("/affiliates/{affiliate_id}")
async def delete_affiliate(
    affiliate_id: str,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        await session.execute(text("DELETE FROM affiliates WHERE id = :id"), {"id": affiliate_id})
        logger.info("Deleted affiliate %s", affiliate_id)

    return {"status": "deleted"}


@router.get("/affiliates/{affiliate_id}/members", response_model=SubscriberListResponse)
async def get_affiliate_members(
    affiliate_id: str,
    page: int = Query(1, ge=1),
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        total = int(
            await session.scalar(
                text("SELECT COUNT(*) FROM subscribers WHERE affiliate_code_used = :code"),
                {"code": affiliate_row["code"]},
            )
            or 0
        )
        per_page = 20
        offset = (page - 1) * per_page
        result = await session.execute(
            text(
                """
                SELECT *
                FROM subscribers
                WHERE affiliate_code_used = :code
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"code": affiliate_row["code"], "limit": per_page, "offset": offset},
        )
        members = [
            SubscriberResponse.model_validate(dict(row))
            for row in result.mappings().all()
        ]
        logger.info("Fetched %s members for affiliate %s", len(members), affiliate_id)

    return SubscriberListResponse(items=members, total=total, page=page, per_page=per_page)


@router.post("/affiliates/{affiliate_id}/mark-paid")
async def mark_commissions_paid(
    affiliate_id: str,
    request: CommissionMarkPaidRequest,
    _subject: str = Depends(verify_admin_token),
):
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        for commission_id in request.commission_ids:
            await session.execute(
                text(
                    """
                    UPDATE commissions
                    SET is_paid = TRUE, paid_at = :paid_at
                    WHERE id = :id AND affiliate_id = :affiliate_id
                    """
                ),
                {"id": commission_id, "affiliate_id": affiliate_id, "paid_at": utcnow()},
            )

        total_paid = float(
            await session.scalar(
                text(
                    """
                    SELECT COALESCE(SUM(amount_owed), 0)
                    FROM commissions
                    WHERE affiliate_id = :id AND is_paid = TRUE
                    """
                ),
                {"id": affiliate_id},
            )
            or 0
        )
        logger.info(
            "Marked %s commissions as paid for affiliate %s",
            len(request.commission_ids),
            affiliate_id,
        )

    return {
        "status": "paid",
        "commission_count": len(request.commission_ids),
        "total_paid": total_paid,
    }


@router.post("/affiliates/{affiliate_id}/mark-all-paid")
async def mark_all_commissions_paid(
    affiliate_id: str,
    _subject: str = Depends(verify_admin_token),
):
    """Mark all unpaid commissions for an affiliate as paid"""
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM affiliates WHERE id = :id"),
            {"id": affiliate_id},
        )
        affiliate_row = result.mappings().one_or_none()
        if not affiliate_row:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        # Get unpaid commission IDs
        result = await session.execute(
            text(
                """
                SELECT id FROM commissions
                WHERE affiliate_id = :affiliate_id AND is_paid = FALSE
                """
            ),
            {"affiliate_id": affiliate_id},
        )
        unpaid_ids = [str(row['id']) for row in result.mappings().all()]

        if not unpaid_ids:
            logger.info("No unpaid commissions for affiliate %s", affiliate_id)
            return {"status": "success", "commission_count": 0, "message": "No unpaid commissions found"}

        # Mark all unpaid commissions as paid
        await session.execute(
            text(
                """
                UPDATE commissions
                SET is_paid = TRUE, paid_at = :paid_at
                WHERE affiliate_id = :affiliate_id AND is_paid = FALSE
                """
            ),
            {"affiliate_id": affiliate_id, "paid_at": utcnow()},
        )

        await session.commit()

        total_paid = float(
            await session.scalar(
                text(
                    """
                    SELECT COALESCE(SUM(amount_owed), 0)
                    FROM commissions
                    WHERE affiliate_id = :id AND is_paid = TRUE
                    """
                ),
                {"id": affiliate_id},
            )
            or 0
        )
        logger.info(
            "Marked all unpaid commissions as paid for affiliate %s (%s commissions, total: $%s)",
            affiliate_id,
            len(unpaid_ids),
            total_paid,
        )

    return {
        "status": "success",
        "commission_count": len(unpaid_ids),
        "message": f"Successfully marked {len(unpaid_ids)} commission{'s' if len(unpaid_ids) != 1 else ''} as paid",
    }
