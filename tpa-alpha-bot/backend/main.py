"""
TPA Alpha Bot - FastAPI Backend
Main application entry point
"""
import logging
import asyncio
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys

# Import database and configuration
from database import init_db, close_db, verify_db_connection
from config import get_settings
from services.discord_service import get_discord_service
from services.blockchain import run_auto_payment_verification_loop
from database import get_session
from admin_api.settings_service import build_network_info_list, load_current_payment_networks, load_payment_network_rows, normalize_payment_network_rows

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan
    Startup: init database, verify connections
    Shutdown: cleanup
    """
    logger.info("🚀 TPA Alpha Bot starting...")
    
    verifier_task: asyncio.Task | None = None
    verifier_stop = asyncio.Event()

    try:
        # Initialize database
        await init_db()
        
        # Verify database connection
        if not await verify_db_connection():
            logger.warning("⚠ Database connection verification failed (continuing)")
        
        # Verify Discord bot token
        discord_service = get_discord_service()
        bot_user = await discord_service.get_bot_user()
        if bot_user:
            logger.info(f"✓ Discord bot verified: {bot_user.get('username')}")
        else:
            logger.warning("⚠ Discord bot token verification failed (continuing)")
        
        # Verify at least one wallet is configured
        settings = get_settings()
        async with get_session() as session:
            configured_networks = await load_current_payment_networks(session, settings)
        configured_wallets = [network.wallet for network in configured_networks if network.wallet]
        if not configured_wallets:
            logger.warning("⚠ No wallets configured - payment detection will not work")
        else:
            logger.info(f"✓ {len(configured_wallets)} wallet(s) configured")

        verifier_task = asyncio.create_task(run_auto_payment_verification_loop(verifier_stop))
        logger.info("✓ Auto payment verification loop started")
        
        logger.info("✓ Startup verification complete")
        
    except Exception as e:
        logger.error(f"✗ Startup failed: {e}")
        # Continue anyway - don't crash the app
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if verifier_task is not None:
        verifier_stop.set()
        try:
            await verifier_task
        except Exception as exc:
            logger.warning(f"Auto verifier shutdown warning: {exc}")
    await close_db()
    logger.info("✓ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="TPA Alpha Bot API",
    description="Discord subscription management system",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# CORS Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://3-93-192-182.nip.io",
    ],
    allow_origin_regex=r"https://.*\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": None  # Don't expose stack traces in production
        }
    )


# ============================================================================
# Health Check Routes
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    settings = get_settings()
    discord_service = get_discord_service()
    
    # Quick health check without blocking
    try:
        bot_user = await discord_service.get_bot_user()
        discord_ok = bot_user is not None
    except:
        discord_ok = False
    
    return {
        "status": "ok",
        "discord_bot": "connected" if discord_ok else "disconnected",
        "database": "configured",
    }


@app.get("/config/networks")
async def get_networks():
    """Get configured payment networks"""
    async with get_session() as session:
        payment_network_rows = await load_payment_network_rows(session)
    payment_networks = normalize_payment_network_rows(payment_network_rows)
    return {"networks": build_network_info_list(payment_networks)}


# ============================================================================
# Import and include routers
# ============================================================================

# Import routers
from routers import webhook, admin, payment

# Include routers with their prefixes
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(webhook.router, prefix="/api/discord", tags=["discord"])
app.include_router(payment.router, prefix="/api/payment", tags=["payment"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
