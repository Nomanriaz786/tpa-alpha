"""
Discord interactions webhook router
Handles: slash command interactions, button interactions
Requires: Ed25519 signature verification
"""
import logging
import json
from fastapi import APIRouter, HTTPException, Request, status
import nacl.signing
import nacl.exceptions

try:
    from backend.config import get_settings
except ImportError:
    from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Discord interaction types
INTERACTION_TYPE_PING = 1
INTERACTION_TYPE_APPLICATION_COMMAND = 2
INTERACTION_TYPE_MESSAGE_COMPONENT = 3

# Discord response types
INTERACTION_RESPONSE_PONG = 1
INTERACTION_RESPONSE_CHANNEL_MESSAGE_WITH_SOURCE = 4


async def verify_discord_signature(request: Request) -> dict:
    """
    Verify Discord interaction signature per Discord security guidelines
    https://discord.com/developers/docs/interactions/receiving-and-responding#security
    
    Requires:
    - X-Signature-Ed25519 header
    - X-Signature-Timestamp header
    - Valid Ed25519 signature
    """
    settings = get_settings()
    
    # Get headers
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature headers"
        )
    
    # Get body
    body = await request.body()
    
    # Reconstruct message for verification
    message = timestamp.encode() + body
    
    try:
        # Verify signature
        public_key_hex = settings.DISCORD_APPLICATION_ID  # Or use actual public key
        verify_key = nacl.signing.VerifyKey(public_key_hex.encode())
        verify_key.verify(message, bytes.fromhex(signature))
        
        logger.debug("✓ Discord signature verified")
        
    except (nacl.exceptions.BadSignatureError, Exception) as e:
        logger.warning(f"✗ Discord signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse body
    return json.loads(body)


@router.post("/interactions")
async def handle_interaction(request: Request):
    """
    Handle Discord interactions (slash commands, buttons, etc.)
    
    This endpoint is registered in Discord Developer Portal:
    Interactions Endpoint URL: https://example.com/api/discord/interactions
    """
    try:
        # Verify signature
        interaction = await verify_discord_signature(request)
        
        interaction_type = interaction.get("type")
        
        # Handle PING (Discord heartbeat)
        if interaction_type == INTERACTION_TYPE_PING:
            logger.debug("✓ Discord PING received")
            return {"type": INTERACTION_RESPONSE_PONG}
        
        # Handle slash commands (application commands)
        elif interaction_type == INTERACTION_TYPE_APPLICATION_COMMAND:
            command_name = interaction.get("data", {}).get("name")
            logger.info(f"Slash command received: /{command_name}")
            
            # Route to command handlers
            # Note: In production, these are handled by discord.py bot directly
            # This webhook is mainly for signature verification + logging
            
            return {"type": INTERACTION_RESPONSE_CHANNEL_MESSAGE_WITH_SOURCE, "data": {
                "content": f"Command /{command_name} received. (Handled by discord.py bot)"
            }}
        
        # Handle button interactions
        elif interaction_type == INTERACTION_TYPE_MESSAGE_COMPONENT:
            custom_id = interaction.get("data", {}).get("custom_id")
            logger.info(f"Button interaction received: {custom_id}")
            
            # Route to button handlers
            # Note: In production, these are handled by discord.py bot directly
            
            return {"type": INTERACTION_RESPONSE_CHANNEL_MESSAGE_WITH_SOURCE, "data": {
                "content": f"Button {custom_id} clicked. (Handled by discord.py bot)"
            }}
        
        else:
            logger.warning(f"Unknown interaction type: {interaction_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown interaction type"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Discord interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle interaction"
        )


# Note on discord.py vs Webhook:
# 
# discord.py bot handles interactions through its built-in event listeners.
# This webhook endpoint is optional and mainly serves for:
# - Signature verification logging
# - Request inspection
# - Custom processing if needed
#
# In our implementation:
# - Discord slash commands are handled by discord.py (admin_commands.py cog)
# - Button interactions are handled by discord.py (interactions.py cog)
# - No need to manually handle interactions here
#
# To enable this webhook:
# 1. Insert into Discord Developer Portal:
#    Interactions Endpoint URL: https://yourapp.com/api/discord/interactions
# 2. Discord will send a PING to verify
# 3. Add public key to config.json for signature verification
