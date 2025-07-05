import discord
from discord.ext import commands
import logging
import platform
import psutil
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class UtilityCog(commands.Cog):
    """ユーティリティ関連のコマンドを管理するCog"""
    
    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        self.start_time = datetime.now(timezone.utc)
    
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
                  "`!botinfo` - ボット情報\n"
                  "`!ping` - 応答速度確認\n"
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
    
    @commands.command(name='ping')
    async def ping(self, ctx):
        """ボットの応答速度を確認"""
        latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"応答速度: {latency}ms",
            color=discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 300 else discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='botinfo')
    async def bot_info(self, ctx):
        """ボットの詳細情報を表示"""
        # 稼働時間を計算
        uptime = datetime.now(timezone.utc) - self.start_time
        uptime_str = str(uptime).split('.')[0]  # マイクロ秒を除去
        
        # メモリ使用量
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
        except:
            memory_mb = 0
        
        # サーバー数と設定済みサーバー数
        total_guilds = len(self.bot.guilds)
        config = self.config_manager.get_config()
        configured_guilds = len(config.get("servers", {}))
        
        embed = discord.Embed(
            title="🤖 ボット情報",
            color=discord.Color.blue()
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
            value=f"稼働時間: {uptime_str}\n"
                  f"メモリ使用量: {memory_mb:.1f}MB\n"
                  f"Python: {platform.python_version()}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 バージョン",
            value=f"ボット: v2.1.0\n"
                  f"Discord.py: {discord.__version__}\n"
                  f"プラットフォーム: {platform.system()}",
            inline=True
        )
        
        embed.set_footer(text=f"ボットID: {self.bot.user.id}")
        await ctx.send(embed=embed)
    
    @commands.command(name='servers')
    async def list_servers(self, ctx):
        """ボットが参加しているサーバー一覧（ボット管理者専用）"""
        # 簡単なボット管理者チェック（実際の運用では適切な権限チェックを実装）
        if ctx.author.id not in [123456789012345678]:  # ここに管理者のIDを設定
            await ctx.send("❌ この機能を使用する権限がありません。")
            return
        
        config = self.config_manager.get_config()
        configured_servers = config.get("servers", {})
        
        embed = discord.Embed(
            title="📋 サーバー一覧",
            color=discord.Color.blue()
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

# Cogの追加関数（外部からのロード用）
async def setup(bot):
    """Cogをbotに追加する関数"""
    # この関数はbot.pyから呼ばれる際にconfig_managerが渡される
    pass