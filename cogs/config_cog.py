import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class ConfigCog(commands.Cog):
    """設定関連のコマンドを管理するCog"""
    
    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
    
    def get_server_config(self, guild_id):
        """サーバー固有の設定を取得"""
        config = self.config_manager.get_config()
        guild_id_str = str(guild_id)
        if guild_id_str in config["servers"]:
            return config["servers"][guild_id_str]
        return None
    
    @commands.command(name='setup')
    async def setup_channel(self, ctx, channel: discord.TextChannel = None):
        """通知チャンネルの設定"""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
            return
        
        if channel is None:
            channel = ctx.channel
        
        guild_id = str(ctx.guild.id)
        
        # 設定の更新
        def update_server_config(config):
            if guild_id not in config["servers"]:
                config["servers"][guild_id] = {}
            
            config["servers"][guild_id]["channel_id"] = str(channel.id)
            config["servers"][guild_id]["enabled"] = True
            config["servers"][guild_id]["timezone_offset"] = config["default_settings"]["timezone_offset"]
        
        self.config_manager.update_config(update_server_config)
        
        embed = discord.Embed(
            title="✅ 設定完了",
            description=f"ボイスチャンネル通知を {channel.mention} に設定しました。",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='disable')
    async def disable_notifications(self, ctx):
        """通知の無効化"""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
            return
        
        guild_id = str(ctx.guild.id)
        
        def update_server_config(config):
            if guild_id in config["servers"]:
                config["servers"][guild_id]["enabled"] = False
                return True
            return False
        
        success = [False]
        def wrapper(config):
            success[0] = update_server_config(config)
        
        self.config_manager.update_config(wrapper)
        
        if success[0]:
            await ctx.send("✅ ボイスチャンネル通知を無効にしました。")
        else:
            await ctx.send("❌ このサーバーはまだ設定されていません。")
    
    @commands.command(name='enable')
    async def enable_notifications(self, ctx):
        """通知の有効化"""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
            return
        
        guild_id = str(ctx.guild.id)
        
        def update_server_config(config):
            if guild_id in config["servers"]:
                config["servers"][guild_id]["enabled"] = True
                return True
            return False
        
        success = [False]
        def wrapper(config):
            success[0] = update_server_config(config)
        
        self.config_manager.update_config(wrapper)
        
        if success[0]:
            await ctx.send("✅ ボイスチャンネル通知を有効にしました。")
        else:
            await ctx.send("❌ このサーバーはまず設定する必要があります。`!setup` コマンドを使用してください。")
    
    @commands.command(name='status')
    async def check_status(self, ctx):
        """現在の設定状況を確認"""
        guild_id = str(ctx.guild.id)
        server_config = self.get_server_config(guild_id)
        
        if server_config:
            channel_id = server_config.get("channel_id")
            enabled = server_config.get("enabled", True)
            timezone_offset = server_config.get("timezone_offset", 9)
            
            channel = self.bot.get_channel(int(channel_id)) if channel_id else None
            
            embed = discord.Embed(
                title="📊 現在の設定",
                color=discord.Color.blue()
            )
            embed.add_field(name="通知チャンネル", value=channel.mention if channel else "未設定", inline=False)
            embed.add_field(name="通知状態", value="✅ 有効" if enabled else "❌ 無効", inline=True)
            embed.add_field(name="タイムゾーン", value=f"UTC+{timezone_offset}", inline=True)
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ 未設定",
                description="このサーバーはまだ設定されていません。\n`!setup` コマンドを使用して設定してください。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='reload')
    async def reload_config(self, ctx):
        """設定の手動再読み込み（管理者用）"""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
            return
        
        try:
            # 強制的に設定を再読み込み
            self.config_manager._refresh_if_needed()
            await ctx.send("✅ 設定ファイルを再読み込みしました。")
        except Exception as e:
            logger.error(f"設定再読み込みエラー: {e}")
            await ctx.send("❌ 設定の再読み込みに失敗しました。")
    
    @commands.command(name='timezone')
    async def set_timezone(self, ctx, offset: int):
        """タイムゾーンオフセットの設定"""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
            return
        
        if not -12 <= offset <= 14:
            await ctx.send("❌ タイムゾーンオフセットは -12 から 14 の間で指定してください。")
            return
        
        guild_id = str(ctx.guild.id)
        
        def update_server_config(config):
            if guild_id in config["servers"]:
                config["servers"][guild_id]["timezone_offset"] = offset
                return True
            return False
        
        success = [False]
        def wrapper(config):
            success[0] = update_server_config(config)
        
        self.config_manager.update_config(wrapper)
        
        if success[0]:
            await ctx.send(f"✅ タイムゾーンをUTC{offset:+d}に設定しました。")
        else:
            await ctx.send("❌ このサーバーはまず設定する必要があります。`!setup` コマンドを使用してください。")

# Cogの追加関数（外部からのロード用）
async def setup(bot):
    """Cogをbotに追加する関数"""
    # この関数はbot.pyから呼ばれる際にconfig_managerが渡される
    pass