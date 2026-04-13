"""
Welcome & Verification cog
Handles: member join event, verification button, welcome message
Features: Auto-role assignment, DM verification, ephemeral verification
"""
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

# Add parent directories to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

try:
    from backend.config import get_settings
except ImportError:
    from config import get_settings

logger = logging.getLogger(__name__)


class WelcomeVerification(commands.Cog):
    """Handle member welcome and verification"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings = get_settings()
        self.verified_users = set()  # Track verified users in this session

    async def _get_guild_settings(self) -> "GuildSettingsConfig":
        return await self.bot.get_guild_settings()

    def _resolve_role_by_name(self, guild: discord.Guild, role_name: str) -> discord.Role | None:
        for role in guild.roles:
            if role.name == role_name:
                return role
        return None

    def _resolve_channel_by_name(self, guild: discord.Guild, channel_name: str) -> discord.TextChannel | None:
        for channel in guild.text_channels:
            if channel.name == channel_name:
                return channel
        return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically assign TPA Community role and send verification"""
        try:
            guild_settings = await self._get_guild_settings()

            # Only process in configured guild
            if member.guild.id != int(guild_settings.guild_id):
                return
            
            # Skip if bot
            if member.bot:
                return
            
            # Get TPA Community role
            community_role = None
            if guild_settings.community_role_id:
                try:
                    community_role = member.guild.get_role(int(guild_settings.community_role_id))
                except (TypeError, ValueError):
                    community_role = None

            if community_role is None:
                community_role = self._resolve_role_by_name(member.guild, "TPA Community")
            
            if not community_role:
                logger.warning(f"⚠️ TPA Community role not found in guild")
                return
            
            # Assign role
            await member.add_roles(community_role)
            logger.info(f"Auto-assigned TPA Community role to {member} ({member.id})")
            
            # Send verification via DM (private, only user sees)
            try:
                # Professional welcome embed - no emojis
                welcome_embed = discord.Embed(
                    title="Welcome to TPA Trading Community",
                    description="We are a professional trading community dedicated to market analysis, signal sharing, and strategic discussions.",
                    color=discord.Color.from_str("#1F2937")
                )
                welcome_embed.add_field(
                    name="What We Offer",
                    value="- Professional market analysis and trading signals\n- Collaborative member discussions\n- VIP exclusive content and resources",
                    inline=False
                )
                
                # Verification embed with button - professional, no emojis
                verify_embed = discord.Embed(
                    title="Account Verification Required",
                    description="To access the full community, please complete account verification by clicking the button below.",
                    color=discord.Color.from_str("#2563EB")
                )
                verify_embed.add_field(
                    name="After Verification",
                    value="- Access all public community channels\n- View VIP-only previews\n- Subscribe for premium membership",
                    inline=False
                )
                
                # Create verification view
                view = discord.ui.View(timeout=None)
                button = discord.ui.Button(
                    label="Verify Account",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"verify_new_user_{member.id}"
                )
                view.add_item(button)
                
                # Send welcome via DM
                dm = await member.create_dm()
                await dm.send(embed=welcome_embed)
                await dm.send(embed=verify_embed, view=view)
                logger.info(f"Verification DM sent to {member} ({member.id})")
                
            except Exception as e:
                logger.error(f"Failed to send verification DM: {e}")
        
        except Exception as e:
            logger.error(f"✗ Member join handler error: {e}")
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle verification button click"""
        if not interaction.type == discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        
        # Handle DM verification for new users
        if custom_id and custom_id.startswith("verify_new_user_"):
            await self.handle_new_user_verification(interaction)
        # Handle welcome channel verification
        elif custom_id == "verify_button":
            await self.handle_verify_button(interaction)
    
    async def handle_new_user_verification(self, interaction: discord.Interaction):
        """Handle new user verification in DM"""
        try:
            user_id = int(interaction.data.get("custom_id").replace("verify_new_user_", ""))
            
            if interaction.user.id != user_id:
                await interaction.response.send_message(
                    "This verification is for another user.",
                    ephemeral=True
                )
                return
            
            # Mark user as verified
            self.verified_users.add(user_id)
            
            # Send professional confirmation
            confirmation_embed = discord.Embed(
                title="Verification Complete",
                description="Your account has been successfully verified.",
                color=discord.Color.from_str("#059669")
            )
            confirmation_embed.add_field(
                name="Access Granted",
                value="- All public community channels\n- VIP preview channels (read-only)\n- Premium subscription options",
                inline=False
            )
            confirmation_embed.add_field(
                name="Community Standards",
                value="- Respectful, professional discourse\n- Focused on trading and analysis\n- No spam or off-topic promotion",
                inline=False
            )
            confirmation_embed.add_field(
                name="Quick Start",
                value="1. Visit general-chat to introduce yourself\n2. Check announcements for market updates\n3. Review resources in key channels",
                inline=False
            )
            
            await interaction.response.send_message(
                embed=confirmation_embed,
                ephemeral=False
            )
            
            logger.info(f"Verification completed for user {interaction.user} ({user_id})")
            
            # Try to move user to general-chat (get the channel)
            try:
                guild = interaction.guild or self.bot.get_guild(int(self.settings.GUILD_ID))
                if guild:
                    general_channel = None
                    for channel in guild.text_channels:
                        if channel.name == "general-chat":
                            general_channel = channel
                            break
                    
                    if general_channel:
                        # Send message to general-chat announcing new verified member
                        embed = discord.Embed(
                            title="New Community Member",
                            description=f"Welcoming {interaction.user.mention} to the TPA Trading Community.",
                            color=discord.Color.from_str("#3B82F6")
                        )
                        await general_channel.send(embed=embed)
                        logger.info(f"Welcome notification posted for {interaction.user}")
            except Exception as e:
                logger.warning(f"⚠️ Could not post to general-chat: {e}")
        
        except Exception as e:
            logger.error(f"New user verification error: {e}")
            await interaction.response.send_message(
                f"An error occurred during verification. Please try again.",
                ephemeral=True
            )
    
    async def handle_verify_button(self, interaction: discord.Interaction):
        """Handle verify button click in welcome channel"""
        try:
            verification_embed = discord.Embed(
                title="Verification Complete",
                description="Your verification has been processed successfully.",
                color=discord.Color.from_str("#059669")
            )
            verification_embed.add_field(
                name="Access Granted",
                value="- Community channels now accessible\n- VIP preview content available\n- Premium subscriptions ready",
                inline=False
            )
            
            await interaction.response.send_message(
                embed=verification_embed,
                ephemeral=True
            )
            
            logger.info(f"Verification completed: {interaction.user} ({interaction.user.id})")
        
        except Exception as e:
            logger.error(f"Verification error: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="An error occurred during verification. Please try again.",
                color=discord.Color.from_str("#DC2626")
            )
            await interaction.response.send_message(
                embed=error_embed,
                ephemeral=True
            )
    

async def setup(bot):
    """Load cog"""
    await bot.add_cog(WelcomeVerification(bot))
