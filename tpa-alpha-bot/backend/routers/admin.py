"""Admin router aggregator."""

from fastapi import APIRouter

from admin_api.affiliates import router as affiliates_router
from admin_api.auth import router as auth_router
from admin_api.dashboard import router as dashboard_router
from admin_api.settings import router as settings_router
from admin_api.subscribers import router as subscribers_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(subscribers_router)
router.include_router(affiliates_router)
router.include_router(settings_router)
