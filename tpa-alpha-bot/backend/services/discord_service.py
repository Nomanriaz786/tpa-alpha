"""
Discord REST API service
Handles role assignment, DM sending, member queries
"""
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from config import get_settings
import time

logger = logging.getLogger(__name__)

# Discord API base URL
DISCORD_API_BASE = "https://discord.com/api/v10"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds


def _normalize_channel_lookup_name(value: str) -> str:
    return "".join(ch for ch in (value or "").strip().lower() if ch not in {"-", "_", " "})


class DiscordService:
    """Service for Discord REST API calls"""
    
    def __init__(self):
        self.settings = get_settings()
        self.bot_token = self.settings.DISCORD_BOT_TOKEN
        self.guild_id = self.settings.GUILD_ID
        self.headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to Discord API with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/users/@me")
            **kwargs: Additional arguments for httpx request
        
        Returns:
            Response JSON or None if request failed
        """
        url = f"{DISCORD_API_BASE}{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, headers=self.headers, timeout=10, **kwargs
                    )
                
                # Check for rate limit
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 1))
                    logger.warning(f"Rate limited. Waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                # 204 No Content
                if response.status_code == 204:
                    return True
                
                # Success
                if 200 <= response.status_code < 300:
                    try:
                        return response.json()
                    except ValueError:
                        return True  # No JSON body
                
                # 404 Not Found
                if response.status_code == 404:
                    logger.warning(f"Discord API 404: {method} {endpoint}")
                    return None
                
                # 401 Unauthorized
                if response.status_code == 401:
                    logger.error("Discord bot token is invalid")
                    raise PermissionError("Invalid Discord bot token")
                
                # Other errors - retry
                logger.warning(
                    f"Discord API error ({response.status_code}): {response.text}"
                )
                
                if attempt < MAX_RETRIES - 1:
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    await asyncio.sleep(backoff)
                    continue
                
                return None
            
            except httpx.TimeoutException:
                logger.warning(f"Discord API timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
                    continue
                return None
            
            except Exception as e:
                logger.error(f"Discord API error: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
                    continue
                return None
        
        return None
    
    async def assign_role(self, discord_id: str, role_id: str) -> bool:
        """
        Assign role to guild member
        
        PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}
        """
        endpoint = f"/guilds/{self.guild_id}/members/{discord_id}/roles/{role_id}"
        result = await self._request("PUT", endpoint, json={})
        
        if result is True:
            logger.info(f"✓ Role assigned to {discord_id}")
            return True
        else:
            logger.error(f"✗ Failed to assign role to {discord_id}")
            return False
    
    async def remove_role(self, discord_id: str, role_id: str) -> bool:
        """
        Remove role from guild member
        
        DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id}
        """
        endpoint = f"/guilds/{self.guild_id}/members/{discord_id}/roles/{role_id}"
        result = await self._request("DELETE", endpoint)
        
        if result is True:
            logger.info(f"✓ Role removed from {discord_id}")
            return True
        else:
            logger.error(f"✗ Failed to remove role from {discord_id}")
            return False
    
    async def dm_user(self, discord_id: str, message: str) -> bool:
        """
        Send direct message to user
        
        1. POST /users/@me/channels  →  create DM channel
        2. POST /channels/{channel_id}/messages  →  send message
        """
        try:
            # Step 1: Create DM channel
            channel_response = await self._request(
                "POST",
                "/users/@me/channels",
                json={"recipient_id": discord_id}
            )
            
            if not channel_response or "id" not in channel_response:
                logger.error(f"Failed to create DM channel for {discord_id}")
                return False
            
            channel_id = channel_response["id"]
            
            # Step 2: Send message
            msg_response = await self._request(
                "POST",
                f"/channels/{channel_id}/messages",
                json={"content": message}
            )
            
            if msg_response and "id" in msg_response:
                logger.info(f"✓ DM sent to {discord_id}")
                return True
            else:
                logger.error(f"Failed to send DM to {discord_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending DM to {discord_id}: {e}")
            return False
    
    async def get_member(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """
        Get guild member details
        
        GET /guilds/{guild_id}/members/{user_id}
        """
        endpoint = f"/guilds/{self.guild_id}/members/{discord_id}"
        result = await self._request("GET", endpoint)
        
        if result:
            logger.debug(f"Retrieved member info for {discord_id}")
            return result
        
        logger.warning(f"Member {discord_id} not found in guild")
        return None
    
    async def get_bot_user(self) -> Optional[Dict[str, Any]]:
        """
        Get bot user info (for verification)
        
        GET /users/@me
        """
        return await self._request("GET", "/users/@me")

    async def find_guild_channel_by_names(self, names: list[str] | tuple[str, ...]) -> Optional[str]:
        """Find a guild channel by any of the supplied names."""
        result = await self._request("GET", f"/guilds/{self.guild_id}/channels")
        if not isinstance(result, list):
            logger.warning("Failed to list guild channels while resolving payment log channel")
            return None

        normalized_names = {
            _normalize_channel_lookup_name(name)
            for name in names
            if _normalize_channel_lookup_name(name)
        }

        for channel in result:
            if not isinstance(channel, dict):
                continue
            channel_name = _normalize_channel_lookup_name(str(channel.get("name") or ""))
            channel_id = str(channel.get("id") or "").strip()
            if channel_id and channel_name in normalized_names:
                return channel_id

        return None
    
    async def send_embed(
        self,
        channel_id: str,
        title: str,
        description: str,
        color: int = 0xFFD700,  # Gold
        fields: Optional[list] = None,
    ) -> bool:
        """
        Send embed message to channel
        
        Used by subscribe button endpoint
        """
        embed = {
            "title": title,
            "description": description,
            "color": color,
        }
        
        if fields:
            embed["fields"] = fields
        
        result = await self._request(
            "POST",
            f"/channels/{channel_id}/messages",
            json={"embeds": [embed]}
        )
        
        return result is not None


# Global instance
_discord_service = None


def get_discord_service() -> DiscordService:
    """Get Discord service instance"""
    global _discord_service
    if _discord_service is None:
        _discord_service = DiscordService()
    return _discord_service
