import logging
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import text

from admin_api.common import verify_admin_token
from database import get_session
from schemas import DashboardResponse, DashboardStats, SubscriberResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(_subject: str = Depends(verify_admin_token)):
    logger.info("Fetching dashboard")

    async with get_session() as session:
        total_subscribers = int(
            await session.scalar(text("SELECT COUNT(*) FROM subscribers")) or 0
        )
        active_subscribers = int(
            await session.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM subscribers
                    WHERE is_active = TRUE
                      AND (expires_at IS NULL OR expires_at > NOW())
                    """
                )
            )
            or 0
        )
        monthly_revenue = Decimal(
            str(
                await session.scalar(
                    text(
                        """
                        SELECT COALESCE(SUM(amount_usd), 0)
                        FROM payments
                        WHERE detected_at >= NOW() - INTERVAL '30 days'
                        """
                    )
                )
                or 0
            )
        )
        unpaid_commissions = Decimal(
            str(
                await session.scalar(
                    text(
                        """
                        SELECT COALESCE(SUM(amount_owed), 0)
                        FROM commissions
                        WHERE is_paid = FALSE
                        """
                    )
                )
                or 0
            )
        )

        recent_result = await session.execute(
            text(
                """
                SELECT *
                FROM subscribers
                ORDER BY created_at DESC
                LIMIT 5
                """
            )
        )
        recent_subscribers = [
            SubscriberResponse.model_validate(dict(row))
            for row in recent_result.mappings().all()
        ]

    return DashboardResponse(
        stats=DashboardStats(
            total_subscribers=total_subscribers,
            active_subscribers=active_subscribers,
            monthly_revenue_usd=float(monthly_revenue),
            unpaid_commissions_usd=float(unpaid_commissions),
        ),
        recent_subscribers=recent_subscribers,
    )
