"""
Admin commands cog
Slash commands: /setup, /grant, /revoke, /status
"""
import logging
from datetime import datetime
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
    from backend.services.discord_service import get_discord_service
except ImportError:
    from config import get_settings
    from services.discord_service import get_discord_service

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog):
    """Admin-only commands for TPA Alpha Bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings = get_settings()
        self.discord_service = get_discord_service()

    async def _resolve_vip_role(self, guild: discord.Guild | None) -> discord.Role | None:
        if guild is None:
            return None

        guild_settings = await self.bot.get_guild_settings()
        vip_role_id = guild_settings.vip_role_id or self.settings.VIP_ROLE_ID
        if vip_role_id:
            try:
                role = guild.get_role(int(vip_role_id))
                if role:
                    return role
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid VIP role ID: %s", vip_role_id)

        for role in guild.roles:
            if role.name == self.settings.VIP_ROLE_NAME:
                return role

        return None
    
    @app_commands.command(
        name="setup",
        description="Post the subscribe button in a channel"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Post subscription button embed to specified channel"""
        logger.info(f"📌 /setup command invoked by {interaction.user} in #{channel.name}")
        try:
            # Create embed
            embed = discord.Embed(
                title="TPA Alpha Membership",
                description="Get access to exclusive trading signals and professional analysis. VIP members receive:\n\n"
                           "✨ Daily trading setups\n"
                           "📊 Technical analysis\n"
                           "🎯 Price targets\n"
                           "💼 Professional guidance",
                color=discord.Color.from_str("#FFD700")  # Gold
            )
            embed.set_footer(text="Powered by TPA Alpha Bot")
            
            # Create view with button
            view = discord.ui.View()
            button = discord.ui.Button(
                label="Subscribe Now",
                style=discord.ButtonStyle.primary,
                custom_id="subscribe_button"
            )
            view.add_item(button)
            
            # Send embed with button
            await channel.send(embed=embed, view=view)
            
            logger.info(f"✓ Subscribe button posted to #{channel.name}")
            
            # Respond to command (ephemeral)
            await interaction.response.send_message(
                f"✓ Subscribe button posted to {channel.mention}",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"✗ Setup command error: {e}")
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="grant",
        description="Manually grant VIP role to a member"
    )
    @app_commands.default_permissions(administrator=True)
    async def grant(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Grant VIP role to a user"""
        try:
            role = await self._resolve_vip_role(interaction.guild)
            if not role:
                raise ValueError(f"VIP role not found in guild")
            
            # Add role
            await user.add_roles(role)
            
            logger.info(f"✓ VIP role granted to {user} ({user.id})")
            
            # Try to DM user
            try:
                dm = await user.create_dm()
                await dm.send(
                    f"🎉 Your TPA Alpha VIP access has been granted by an administrator.\n\n"
                    f"You now have access to exclusive trading signals and analysis."
                )
            except:
                pass  # User may have DMs disabled
            
            # Respond to command (ephemeral)
            await interaction.response.send_message(
                f"✓ VIP role granted to {user.mention}",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"✗ Grant command error: {e}")
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="revoke",
        description="Manually revoke VIP role from a member"
    )
    @app_commands.default_permissions(administrator=True)
    async def revoke(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Revoke VIP role from a user"""
        try:
            role = await self._resolve_vip_role(interaction.guild)
            if not role:
                raise ValueError(f"VIP Role not found")
            
            # Remove role
            await user.remove_roles(role)
            
            logger.info(f"✓ VIP role revoked from {user} ({user.id})")
            
            # Try to DM user
            try:
                dm = await user.create_dm()
                await dm.send(
                    f"⚠️ Your TPA Alpha VIP access has been revoked.\n\n"
                    f"You can renew your membership anytime."
                )
            except:
                pass
            
            # Respond to command
            await interaction.response.send_message(
                f"✓ VIP role revoked from {user.mention}",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"✗ Revoke command error: {e}")
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="status",
        description="Check your subscription status and remaining days"
    )
    async def status(self, interaction: discord.Interaction):
        """Check your subscription status (self only)"""
        try:
            user_discord_id = str(interaction.user.id)
            
            # Query database for subscriber info
            from sqlalchemy import text
            from backend.database import get_session
            from datetime import datetime, timezone
            
            async with get_session() as session:
                subscriber_result = await session.execute(
                    text("""
                        SELECT is_active, expires_at, discord_username, tradingview_username
                        FROM subscribers
                        WHERE discord_id = :discord_id
                    """),
                    {"discord_id": user_discord_id}
                )
                subscriber = subscriber_result.mappings().one_or_none()
            
            # Check if user has VIP role
            role = await self._resolve_vip_role(interaction.guild)
            has_vip = role in interaction.user.roles if role else False
            
            # Calculate remaining days
            remaining_days = None
            if subscriber and subscriber["expires_at"]:
                expiry = subscriber["expires_at"]
                # Make sure expiry is timezone aware
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                remaining = (expiry - now).days
                remaining_days = max(0, remaining)
            
            # Create response embed
            if has_vip and subscriber and subscriber["is_active"]:
                embed = discord.Embed(
                    title="VIP Member",
                    description="Your subscription is active",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Status",
                    value="Active",
                    inline=True
                )
                
                if remaining_days is not None:
                    embed.add_field(
                        name="Days Remaining",
                        value=f"{remaining_days} days",
                        inline=True
                    )
                
                if subscriber.get("tradingview_username"):
                    embed.add_field(
                        name="TradingView Username",
                        value=subscriber["tradingview_username"],
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="Not a VIP Member",
                    description="You do not have active TPA Alpha access",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Status",
                    value="Inactive",
                    inline=False
                )
                embed.add_field(
                    name="Subscribe",
                    value="Use the subscribe button to activate membership",
                    inline=False
                )
            
            # Always ephemeral - only visible to user
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
            logger.info(f"Status check for {interaction.user} ({user_discord_id}): VIP={has_vip}")
        
        except Exception as e:
            logger.error(f"Status command error: {e}")
            await interaction.response.send_message(
                f"Error checking status: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="affiliate-status",
        description="Check your affiliate referral and commission status"
    )
    async def affiliate_status(self, interaction: discord.Interaction):
        """Check affiliate status - members with referral codes only"""
        try:
            user_discord_id = str(interaction.user.id)
            
            # Query database for affiliate info
            from sqlalchemy import text
            from backend.database import get_session
            
            async with get_session() as session:
                # Get affiliate code for this user - only select columns that exist
                affiliate_result = await session.execute(
                    text("""
                        SELECT id, code, name, type, commission_percent, is_active
                        FROM affiliates
                        WHERE discord_id = :discord_id
                        LIMIT 1
                    """),
                    {"discord_id": user_discord_id}
                )
                affiliate_row = affiliate_result.mappings().one_or_none()
                
                if not affiliate_row:
                    await interaction.response.send_message(
                        "You do not have an affiliate code. Contact an admin to set one up.",
                        ephemeral=True
                    )
                    return
                
                # Get active members count
                active_members = int(
                    await session.scalar(
                        text("""
                            SELECT COUNT(*)
                            FROM subscribers
                            WHERE affiliate_code_used = :code
                              AND is_active = TRUE
                              AND (expires_at IS NULL OR expires_at > NOW())
                        """),
                        {"code": affiliate_row["code"]}
                    ) or 0
                )
                
                # Get total members ever used this code
                total_members = int(
                    await session.scalar(
                        text("""
                            SELECT COUNT(*)
                            FROM subscribers
                            WHERE affiliate_code_used = :code
                        """),
                        {"code": affiliate_row["code"]}
                    ) or 0
                )
                
                # Get unpaid commissions
                total_commissions_owed = float(
                    await session.scalar(
                        text("""
                            SELECT COALESCE(SUM(amount_owed), 0)
                            FROM commissions
                            WHERE affiliate_id = :affiliate_id AND is_paid = FALSE
                        """),
                        {"affiliate_id": affiliate_row["id"]}
                    ) or 0
                )
                
                # Get paid commissions
                total_commissions_paid = float(
                    await session.scalar(
                        text("""
                            SELECT COALESCE(SUM(amount_owed), 0)
                            FROM commissions
                            WHERE affiliate_id = :affiliate_id AND is_paid = TRUE
                        """),
                        {"affiliate_id": affiliate_row["id"]}
                    ) or 0
                )
            
            # Create professional status embed
            embed = discord.Embed(
                title="Affiliate Status",
                description=f"Code: `{affiliate_row['code']}`",
                color=discord.Color.from_str("#3B82F6")
            )
            
            embed.add_field(
                name="Active Members",
                value=f"{active_members}",
                inline=True
            )
            
            embed.add_field(
                name="Total Members",
                value=f"{total_members}",
                inline=True
            )
            
            embed.add_field(
                name="Commission Rate",
                value=f"{affiliate_row['commission_percent']}%",
                inline=True
            )
            
            embed.add_field(
                name="Commission Owed",
                value=f"${total_commissions_owed:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Commission Paid",
                value=f"${total_commissions_paid:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Total Earned",
                value=f"${(total_commissions_owed + total_commissions_paid):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Status",
                value="Active" if affiliate_row['is_active'] else "Inactive",
                inline=True
            )
            
            embed.set_footer(text="Contact admin for payout requests")
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
            logger.info(f"Affiliate status checked for {interaction.user} ({user_discord_id})")
        
        except Exception as e:
            logger.error(f"Affiliate status command error: {e}")
            await interaction.response.send_message(
                f"Error checking affiliate status: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="welcome",
        description="Post comprehensive welcome message with rules and membership info"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome(self, interaction: discord.Interaction):
        """Post comprehensive welcome message"""
        try:
            channel = interaction.channel
            
            # Embed 1: Welcome & Introduction
            embed1 = discord.Embed(
                title="Welcome to TPA",
                description="This server is a professional trading community focused on Trend + Price Action (TPA) strategies across crypto, stocks, forex, and global financial markets.",
                color=discord.Color.from_str("#3B82F6")
            )
            embed1.add_field(
                name="Our Mission",
                value="Create a focused environment where traders can learn structured trading methods, improve discipline, and execute high-quality setups using proper risk management.",
                inline=False
            )
            embed1.add_field(
                name="Server Agreement",
                value="By remaining in this server, you agree to the rules, policies, and disclaimers listed below.",
                inline=False
            )
            embed1.add_field(
                name="Verification",
                value="Check your DMs for the Verify Account button. Verification only happens in DM, not in this channel. If you do not see a DM, enable DMs from server members and contact staff.",
                inline=False
            )
            
            # Embed 2: Premium Membership
            embed2 = discord.Embed(
                title="Premium Membership",
                description="Premium members receive full access to:",
                color=discord.Color.from_str("#8B5CF6")
            )
            embed2.add_field(
                name="Access Includes",
                value="• The TPA Trading Strategy\n"
                      "• All TPA proprietary indicators\n"
                      "• Trade signals and setups\n"
                      "• Live trading sessions\n"
                      "• Private members-only discussion channels",
                inline=False
            )
            embed2.add_field(
                name="Membership Price",
                value="100 USDT per month",
                inline=False
            )
            embed2.add_field(
                name="Important Note",
                value="The goal of this community is not only to share setups but also to teach traders how to understand and apply the TPA strategy independently.",
                inline=False
            )
            embed2.add_field(
                name="Access Activation",
                value="Premium access is granted after payment confirmation and role assignment.",
                inline=False
            )
            
            # Embed 3: Community Rules
            embed3 = discord.Embed(
                title="Community Rules",
                color=discord.Color.from_str("#EF4444")
            )
            embed3.add_field(
                name="Rules to Follow",
                value="1. Respect all members — no harassment or toxic behavior\n"
                      "2. Keep discussions related to trading and financial markets\n"
                      "3. No spam, promotions, or advertising without approval\n"
                      "4. Post content in the appropriate channels\n"
                      "5. No scams, pump groups, or misleading information\n"
                      "6. Staff decisions regarding moderation are final",
                inline=False
            )
            embed3.add_field(
                name="Enforcement",
                value="Failure to follow these rules may result in warnings, mute, or removal from the server permanently.",
                inline=False
            )
            
            # Embed 4: Legal Disclaimer
            embed4 = discord.Embed(
                title="Important Legal Disclaimer",
                color=discord.Color.from_str("#FBBF24")
            )
            embed4.add_field(
                name="Transparency Notice",
                value="• All content in this server is provided for educational purposes only\n"
                      "• Nothing shared here constitutes financial or investment advice\n"
                      "• Trading financial markets involves significant risk and potential loss",
                inline=False
            )
            embed4.add_field(
                name="Member Responsibility",
                value="Every member is fully responsible for their own trading decisions and risk management.",
                inline=False
            )
            
            # Embed 5: Membership & Refund Policy
            embed5 = discord.Embed(
                title="Membership & Refund Policy",
                color=discord.Color.from_str("#10B981")
            )
            embed5.add_field(
                name="What You Get",
                value="Premium membership grants access to TPA strategies, indicators, educational material, and private trading content.",
                inline=False
            )
            embed5.add_field(
                name="Terms of Purchase",
                value="By purchasing a membership you agree that:\n"
                      "• All payments are final\n"
                      "• No refunds will be issued under any circumstances\n"
                      "• Access may be revoked if community rules are violated",
                inline=False
            )
            
            # Embed 6: Trading Philosophy
            embed6 = discord.Embed(
                title="Trading Philosophy",
                description="Trading is a marathon, not a sprint.",
                color=discord.Color.from_str("#06B6D4")
            )
            embed6.add_field(
                name="Path to Success",
                value="Long-term success in the markets comes from discipline, patience, risk management, and consistency.",
                inline=False
            )
            embed6.add_field(
                name="Focus on Process",
                value="Focus on process over outcome, and the results will follow.",
                inline=False
            )
            
            # Respond to interaction immediately (required within 3 seconds by Discord)
            await interaction.response.send_message(
                "Welcome message posted successfully",
                ephemeral=True
            )
            
            # Send all embeds after responding (no timeout pressure)
            # NOTE: Verification button is sent privately to new users via DM, not in public channel
            await channel.send(embed=embed1)
            await channel.send(embed=embed2)
            await channel.send(embed=embed3)
            await channel.send(embed=embed4)
            await channel.send(embed=embed5)
            await channel.send(embed=embed6)
            
            logger.info(f"Welcome message posted to #{channel.name}")
        
        except Exception as e:
            logger.error(f"Welcome command error: {e}")
            await interaction.response.send_message(
                f"Error posting welcome message: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    """Load cog"""
    await bot.add_cog(AdminCommands(bot))
