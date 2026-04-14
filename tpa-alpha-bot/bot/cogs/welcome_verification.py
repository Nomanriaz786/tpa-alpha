"""
Welcome & Verification cog
Handles: member join event and DM-based verification button.
"""
import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class WelcomeVerification(commands.Cog):
    """Handle member welcome and verification"""
    
    def __init__(self, bot):
        self.bot = bot
        self.verified_users = set()  # Track verified users in this session

    async def _get_guild_settings(self) -> "GuildSettingsConfig":
        return await self.bot.get_guild_settings()

    def _resolve_role_by_name(self, guild: discord.Guild, role_name: str) -> discord.Role | None:
        for role in guild.roles:
            if role.name == role_name:
                return role
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
                # Create verification view
                view = discord.ui.View(timeout=None)
                button = discord.ui.Button(
                    label="Verify Account",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"verify_new_user_{member.id}"
                )
                view.add_item(button)
                
                # Send the verification button only via DM.
                dm = await member.create_dm()
                await dm.send(
                    "You're in the right place. Click the Verify Account button below to continue.",
                    view=view,
                )
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
            
            await interaction.response.send_message(
                "Verification complete. You can now access the community.",
                ephemeral=False
            )
            
            logger.info(f"Verification completed for user {interaction.user} ({user_id})")
        
        except Exception as e:
            logger.error(f"New user verification error: {e}")
            await interaction.response.send_message(
                f"An error occurred during verification. Please try again.",
                ephemeral=True
            )
    

async def setup(bot):
    """Load cog"""
    await bot.add_cog(WelcomeVerification(bot))
