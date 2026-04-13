import logging

from fastapi import APIRouter, Depends

from admin_api.common import load_admin_config_values, upsert_admin_config, verify_admin_token
from admin_api.settings_service import (
    build_admin_settings,
    load_payment_network_rows,
    replace_payment_network_rows,
)
from config import get_settings
from services.guild_settings import load_guild_settings_rows, replace_guild_settings_rows
from database import get_session
from schemas import AdminSettings, AdminSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/settings", response_model=AdminSettings)
async def get_settings_endpoint(_subject: str = Depends(verify_admin_token)):
    env_settings = get_settings()
    async with get_session() as session:
        config_values = await load_admin_config_values(session)
        payment_network_rows = await load_payment_network_rows(session)
        guild_settings_rows = await load_guild_settings_rows(session)
    return build_admin_settings(config_values, payment_network_rows, guild_settings_rows, env_settings)


@router.put("/settings", response_model=AdminSettings)
async def update_settings_endpoint(
    request: AdminSettingsUpdate,
    _subject: str = Depends(verify_admin_token),
):
    env_settings = get_settings()
    async with get_session() as session:
        if request.wallets is not None:
            await upsert_admin_config(session, "wallets", request.wallets)
            logger.info("Updated wallets configuration")

        if request.payment_networks is not None:
            await replace_payment_network_rows(session, [network.model_dump() for network in request.payment_networks])
            logger.info("Updated payment network configuration")

        if request.guild_settings is not None:
            await replace_guild_settings_rows(session, [guild_settings.model_dump() for guild_settings in request.guild_settings])
            logger.info("Updated guild settings configuration")

        if request.smtp_host is not None:
            await upsert_admin_config(session, "smtp_host", request.smtp_host)
            logger.info("Updated SMTP host")

        if request.smtp_port is not None:
            await upsert_admin_config(session, "smtp_port", request.smtp_port)
            logger.info("Updated SMTP port")

        if request.smtp_user is not None:
            await upsert_admin_config(session, "smtp_user", request.smtp_user)
            logger.info("Updated SMTP user")

        if request.smtp_pass is not None:
            await upsert_admin_config(session, "smtp_pass", request.smtp_pass)
            logger.warning("SMTP password updated in admin_config")

        if request.admin_email is not None:
            await upsert_admin_config(session, "admin_email", request.admin_email)
            logger.info("Updated admin email")

        if request.price_per_month_usd is not None:
            await upsert_admin_config(session, "price_per_month_usd", request.price_per_month_usd)
            logger.info("Updated price per month: $%s", request.price_per_month_usd)

        if request.payment_tolerance_usd is not None:
            await upsert_admin_config(
                session,
                "payment_tolerance_usd",
                request.payment_tolerance_usd,
            )
            logger.info("Updated payment tolerance: $%s", request.payment_tolerance_usd)

        config_values = await load_admin_config_values(session)
        payment_network_rows = await load_payment_network_rows(session)
        guild_settings_rows = await load_guild_settings_rows(session)

    return build_admin_settings(config_values, payment_network_rows, guild_settings_rows, env_settings)
