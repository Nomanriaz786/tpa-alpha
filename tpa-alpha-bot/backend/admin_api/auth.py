import bcrypt
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from admin_api.common import create_admin_token, verify_admin_token
from admin_api.settings_service import (
    current_admin_password_version,
    load_admin_security_row,
    resolve_admin_password_hash,
    save_admin_security_row,
)
from database import get_session
from schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminPasswordChangeRequest,
    AdminPasswordChangeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

LEGACY_ADMIN_PASSWORD_KEY = "admin_password_hash"


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    password = (request.password or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    async with get_session() as session:
        admin_security_row = await load_admin_security_row(session)
        legacy_hash = await session.scalar(
            text("SELECT value FROM admin_config WHERE key = :key"),
            {"key": LEGACY_ADMIN_PASSWORD_KEY},
        )
        existing_hash = resolve_admin_password_hash(
            admin_security_row,
            {LEGACY_ADMIN_PASSWORD_KEY: legacy_hash} if legacy_hash else {},
        )

        if existing_hash:
            if not bcrypt.checkpw(password.encode(), str(existing_hash).encode()):
                logger.warning("Admin login failed - invalid password")
                raise HTTPException(status_code=401, detail="Invalid password")

            if not admin_security_row:
                await save_admin_security_row(session, str(existing_hash), 1)
        else:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            await save_admin_security_row(session, password_hash, 1)
            logger.info("Admin password initialized")

        password_version = await current_admin_password_version(session)

    token, expires_at = create_admin_token(password_version)
    logger.info("Admin login successful")
    return AdminLoginResponse(token=token, expires_at=expires_at)


@router.post("/password", response_model=AdminPasswordChangeResponse)
async def change_admin_password(
    request: AdminPasswordChangeRequest,
    _subject: str = Depends(verify_admin_token),
):
    current_password = (request.current_password or "").strip()
    new_password = (request.new_password or "").strip()
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    async with get_session() as session:
        admin_security_row = await load_admin_security_row(session)
        legacy_hash = await session.scalar(
            text("SELECT value FROM admin_config WHERE key = :key"),
            {"key": LEGACY_ADMIN_PASSWORD_KEY},
        )
        existing_hash = resolve_admin_password_hash(
            admin_security_row,
            {LEGACY_ADMIN_PASSWORD_KEY: legacy_hash} if legacy_hash else {},
        )

        if not existing_hash or not bcrypt.checkpw(current_password.encode(), str(existing_hash).encode()):
            raise HTTPException(status_code=401, detail="Invalid current password")

        current_version = await current_admin_password_version(session)
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        saved_row = await save_admin_security_row(session, new_hash, current_version + 1)

    logger.info("Admin password changed successfully")
    return AdminPasswordChangeResponse(
        status="password_updated",
        password_version=int(saved_row.get("password_version") or current_version + 1),
        updated_at=saved_row.get("updated_at"),
    )


@router.post("/logout")
async def admin_logout(_subject: str = Depends(verify_admin_token)):
    logger.info("Admin logout")
    return {"status": "logged out"}