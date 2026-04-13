"""
Button interactions cog
Handles: subscribe_button click
"""
import logging

import discord
from discord.ext import commands

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings

logger = logging.getLogger(__name__)


class ButtonInteractions(commands.Cog):
    """Handle message button interactions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings = get_settings()
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle any interaction"""
        # Check if it's a button interaction
        if not interaction.type == discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        
        if custom_id == "subscribe_button":
            await self.handle_subscribe_button(interaction)
    
    async def handle_subscribe_button(self, interaction: discord.Interaction):
        """Handle subscribe button click"""
        try:
            # Build payment URL
            payment_url = (
                f"{self.settings.WEB_BASE_URL}/subscribe?"
                f"discord_id={interaction.user.id}"
                f"&discord_username={interaction.user.name}"
            )
            
            # Send ephemeral message with link
            await interaction.response.send_message(
                f"🎯 **Complete your subscription**\n\n"
                f"Click the link below to proceed to the payment page:\n\n"
                f"[🌐 Open Payment Page]({payment_url})\n\n"
                f"**What to expect:**\n"
                f"1. Enter your TradingView username\n"
                f"2. Select your payment network\n"
                f"3. Send the required amount\n"
                f"4. Your access will be activated automatically\n\n"
                f"_Link opens in a new tab_",
                ephemeral=True
            )
            
            logger.info(
                f"✓ Subscribe button clicked by {interaction.user} ({interaction.user.id})"
            )
        
        except Exception as e:
            logger.error(f"✗ Subscribe button error: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred. Please try again.",
                ephemeral=True
            )


async def setup(bot):
    """Load cog"""
    await bot.add_cog(ButtonInteractions(bot))
