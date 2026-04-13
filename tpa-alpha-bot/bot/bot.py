"""
TPA Alpha Bot - Discord Bot Entry Point
discord.py 2.x with app_commands (slash commands)
"""
import os
import sys
import logging
from pathlib import Path

import discord
from discord.ext import commands

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.config import get_settings
from backend.database import get_session
from backend.schemas import GuildSettingsConfig
from backend.services.guild_settings import load_effective_guild_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TPAAlphaBot(commands.Bot):
    """TPA Alpha Bot - manages subscriptions via Discord"""
    
    def __init__(self, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            **kwargs
        )
        
        self.settings = get_settings()
        self._guild_settings_cache: GuildSettingsConfig | None = None

    async def get_guild_settings(self) -> GuildSettingsConfig:
        """Refresh the active guild settings row and fall back to the last known copy if needed."""
        try:
            async with get_session() as session:
                self._guild_settings_cache = await load_effective_guild_settings(
                    session,
                    env_settings=self.settings,
                )
        except Exception as exc:
            logger.warning("Falling back to environment guild settings: %s", exc)
            if self._guild_settings_cache is None:
                self._guild_settings_cache = GuildSettingsConfig(
                    guild_id=self.settings.GUILD_ID,
                    vip_role_id=self.settings.VIP_ROLE_ID or None,
                    community_role_id=None,
                    welcome_channel_id=None,
                    setup_channel_id=None,
                    admin_channel_id=None,
                    support_channel_id=None,
                    is_active=True,
                )

        return self._guild_settings_cache
    
    async def setup_hook(self):
        """Called when bot is initializing"""
        logger.info("🤖 Bot setup hook starting...")

        await self.get_guild_settings()

        # Load cogs
        await self.load_cogs()

        # Debug: Log command tree
        logger.info(f"📋 Commands in tree: {len(self.tree._get_all_commands())}")
        for cmd in self.tree._get_all_commands():
            logger.info(f"   - {cmd.name}: {cmd.description}")

        # Sync slash commands globally (not guild-specific)
        try:
            global_synced = await self.tree.sync()
            logger.info(f"✓ Synced {len(global_synced)} commands globally")
            if global_synced:
                for cmd in global_synced:
                    logger.info(f"   ✓ {cmd.name}")
        except Exception as e:
            logger.error(f"✗ Failed to sync commands: {e}", exc_info=True)
    
    async def load_cogs(self):
        """Load all cogs from cogs directory"""
        cogs_dir = Path(__file__).parent / "cogs"
        logger.info(f"📁 Loading cogs from: {cogs_dir}")

        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue

            cog_name = f"cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                logger.info(f"✓ Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"✗ Failed to load cog {cog_name}: {e}", exc_info=True)
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"✓ Bot logged in as {self.user}")
        guild_settings = await self.get_guild_settings()
        logger.info(f"✓ Connected to guild: {guild_settings.guild_id}")

    async def on_error(self, event, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in {event}:", exc_info=True)

    async def on_interaction(self, interaction: discord.Interaction):
        """Catch ALL interactions (lowest level)"""
        interaction_data = interaction.data or {}
        logger.info(
            "🔔 Interaction received: type=%s user=%s guild=%s command=%s custom_id=%s",
            interaction.type,
            interaction.user,
            interaction.guild_id,
            interaction_data.get("name"),
            interaction_data.get("custom_id"),
        )

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle app command errors"""
        logger.error(f"App command error in {interaction.command.name}: {error}", exc_info=True)

        # Always respond to interaction to prevent timeout
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Command error: {str(error)[:100]}",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")


async def main():
    """Main entry point"""
    settings = get_settings()
    
    # Verify required settings
    required_fields = ["DISCORD_BOT_TOKEN", "GUILD_ID"]
    for field in required_fields:
        if not getattr(settings, field, None):
            logger.error(f"✗ Missing configuration: {field}")
            sys.exit(1)
    
    logger.info("🚀 TPA Alpha Bot starting...")
    logger.info(f"   Guild ID: {settings.GUILD_ID}")
    
    bot = TPAAlphaBot()

    try:
        guild_settings = await bot.get_guild_settings()
        vip_role_display = guild_settings.vip_role_id or settings.VIP_ROLE_ID or f"name:{settings.VIP_ROLE_NAME}"
        logger.info(f"   VIP Role ID: {vip_role_display}")
    except Exception:
        vip_role_display = settings.VIP_ROLE_ID or f"name:{settings.VIP_ROLE_NAME}"
        logger.info(f"   VIP Role ID: {vip_role_display}")
    
    try:
        await bot.start(settings.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("⏹️  Bot shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"✗ Bot error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
