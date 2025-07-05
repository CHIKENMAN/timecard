import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class UtilityCog(commands.Cog):
    """ユーティリティ関連のコマンドを管理するCog"""
    
    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
    
    @commands.command(name='help')
    async def help_command(self, ctx):
        """ヘルプコマンド"""
        embed = discord.Embed(
            title="🤖 ボイスチャンネル通知ボット",
            description="ボイスチャンネルの参加・退出・移動を通知します。",
            color=discord.Color.blue()
        )
        
        # 設定コマンド
        embed.add_field(
            name="⚙️ 設定コマンド",
            value="`!setup [#チャンネル]` - 通知チャンネルを設定\n"
                  "`!enable` - 通知を有効化\n"
                  "`!disable` - 通知を無効化\n"
                  "`!status` - 現在の設定を確認\n"
                  "`!timezone <オフセット>` - タイムゾーンを設定\n"
                  "`!reload` - 設定を手動再読み込み",
            inline=False
        )
        
        # 情報コマンド
        embed.add_field(
            name="📊 情報コマンド",
            value="`!vcstats` - ボイスチャンネル統計\n"
                  "`!version` - バージョン情報\n"
                  "`!help` - このヘルプを表示",
            inline=False
        )
        
        embed.add_field(
            name="🔐 権限",
            value="設定コマンドには「サーバー管理」権限が必要です。",
            inline=False
        )
        
        embed.set_footer(text="Discord Voice Channel Notification Bot v2.1.0")
        await ctx.send(embed=embed)
    
    @commands.command(name='version')
    async def version(self, ctx):
        """ボットのバージョン情報を表示"""
        embed = discord.Embed(
            title="🔖 バージョン情報",
            description="Discord Voice Channel Notification Bot",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="現在のバージョン",
            value="v2.1.0",
            inline=True
        )
        
        embed.add_field(
            name="リリース日",
            value="2024年12月",
            inline=True
        )
        
        embed.add_field(
            name="主な機能",
            value="• 複数サーバー対応\n• 動的設定再読み込み\n• Cogベースの構成",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # 管理者専用コマンド（BOT_ADMIN_ID環境変数で管理者IDを指定）
    @commands.command(name='admin_info', hidden=True)
    async def admin_info(self, ctx):
        """管理者専用：詳細なボット情報を表示"""
        import os
        import platform
        
        # 管理者IDチェック
        admin_ids = os.getenv('BOT_ADMIN_IDS', '').split(',')
        if str(ctx.author.id) not in admin_ids:
            await ctx.send("❌ この機能を使用する権限がありません。")
            return
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
        except ImportError:
            memory_mb = 0
        
        # サーバー数と設定済みサーバー数
        total_guilds = len(self.bot.guilds)
        config = self.config_manager.get_config()
        configured_guilds = len(config.get("servers", {}))
        
        embed = discord.Embed(
            title="🔧 管理者情報",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📊 統計",
            value=f"参加サーバー数: {total_guilds}\n"
                  f"設定済みサーバー: {configured_guilds}\n"
                  f"応答速度: {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        embed.add_field(
            name="⚡ システム",
            value=f"メモリ使用量: {memory_mb:.1f}MB\n"
                  f"Python: {platform.python_version()}\n"
                  f"プラットフォーム: {platform.system()}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Discord.py",
            value=f"バージョン: {discord.__version__}",
            inline=True
        )
        
        embed.set_footer(text="⚠️ 管理者専用情報")
        await ctx.send(embed=embed)
    
    @commands.command(name='admin_servers', hidden=True)
    async def admin_list_servers(self, ctx):
        """管理者専用：ボットが参加しているサーバー一覧"""
        import os
        
        # 管理者IDチェック
        admin_ids = os.getenv('BOT_ADMIN_IDS', '').split(',')
        if str(ctx.author.id) not in admin_ids:
            await ctx.send("❌ この機能を使用する権限がありません。")
            return
        
        config = self.config_manager.get_config()
        configured_servers = config.get("servers", {})
        
        embed = discord.Embed(
            title="📋 サーバー一覧（管理者専用）",
            color=discord.Color.red()
        )
        
        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            is_configured = guild_id in configured_servers
            status = "✅ 設定済み" if is_configured else "❌ 未設定"
            
            embed.add_field(
                name=guild.name,
                value=f"ID: {guild.id}\n"
                      f"メンバー数: {guild.member_count}\n"
                      f"状態: {status}",
                inline=True
            )
        
        embed.set_footer(text="⚠️ 管理者専用情報")
        await ctx.send(embed=embed)

# Cogの追加関数（外部からのロード用）
async def setup(bot):
    """Cogをbotに追加する関数"""
    # この関数はbot.pyから呼ばれる際にconfig_managerが渡される
    pass