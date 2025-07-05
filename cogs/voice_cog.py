import discord
from discord.ext import commands
from discord.utils import escape_markdown
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    """ボイスチャンネル関連のイベント処理を管理するCog"""
    
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
    
    def get_destination_channel(self, guild_id):
        """サーバー用の通知チャンネルを取得"""
        server_config = self.get_server_config(guild_id)
        if server_config and server_config.get("enabled", True):
            channel_id = server_config.get("channel_id")
            if channel_id:
                try:
                    return self.bot.get_channel(int(channel_id))
                except (ValueError, TypeError):
                    logger.error(f"無効なチャンネルID: {channel_id}")
        return None
    
    def get_timezone_offset(self, guild_id):
        """サーバー固有のタイムゾーンオフセットを取得"""
        config = self.config_manager.get_config()
        server_config = self.get_server_config(guild_id)
        if server_config:
            return server_config.get("timezone_offset", config["default_settings"]["timezone_offset"])
        return config["default_settings"]["timezone_offset"]
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネルの状態変更を検知"""
        if member.bot:  # ボットは除外
            return
        
        if before.channel == after.channel:  # チャンネルに変更がない場合
            return
        
        guild_id = member.guild.id
        destination = self.get_destination_channel(guild_id)
        
        if destination is None:
            return  # 設定されていない、または無効化されている
        
        # タイムゾーンオフセットを取得
        tz_offset = self.get_timezone_offset(guild_id)
        now = datetime.now(timezone(timedelta(hours=tz_offset)))
        date_str = now.strftime("%Y/%m/%d %H:%M:%S")
        
        try:
            if before.channel is None:  # 参加
                message = f'{date_str} {member.display_name} が {after.channel.name} に参加しました'
                await destination.send(escape_markdown(message))
            elif after.channel is None:  # 退出
                message = f'{date_str} {member.display_name} が {before.channel.name} から退出しました'
                await destination.send(escape_markdown(message))
            else:  # 移動
                message = f'{date_str} {member.display_name} が {before.channel.name} から {after.channel.name} に移動しました'
                await destination.send(escape_markdown(message))
        except discord.errors.Forbidden:
            logger.error(f"チャンネル {destination.name} への送信権限がありません")
        except Exception as e:
            logger.error(f"メッセージ送信中にエラーが発生: {e}")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """新しいサーバーに参加した時の処理"""
        logger.info(f'新しいサーバーに参加しました: {guild.name} (ID: {guild.id})')
        
        # 管理者権限を持つチャンネルを探して設定方法を通知
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="ボイスチャンネル通知ボットへようこそ！",
                    description="このボットを使用するには設定が必要です。",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="設定方法",
                    value=f"`!setup #{channel.name}` - このチャンネルを通知先に設定\n`!help` - その他のコマンドを表示",
                    inline=False
                )
                await channel.send(embed=embed)
                break
    
    @commands.command(name='vcstats')
    async def voice_channel_stats(self, ctx):
        """ボイスチャンネルの統計情報を表示"""
        guild = ctx.guild
        voice_channels = guild.voice_channels
        
        if not voice_channels:
            await ctx.send("このサーバーにはボイスチャンネルがありません。")
            return
        
        embed = discord.Embed(
            title="🎤 ボイスチャンネル統計",
            description=f"サーバー: {guild.name}",
            color=discord.Color.blue()
        )
        
        total_members = 0
        active_channels = 0
        
        for channel in voice_channels:
            member_count = len(channel.members)
            total_members += member_count
            
            if member_count > 0:
                active_channels += 1
                members_list = [member.display_name for member in channel.members]
                embed.add_field(
                    name=f"🔊 {channel.name}",
                    value=f"**{member_count}人**: {', '.join(members_list)}" if member_count <= 10 else f"**{member_count}人**: {', '.join(members_list[:10])}...",
                    inline=False
                )
        
        embed.add_field(
            name="📊 概要",
            value=f"アクティブなチャンネル: {active_channels}/{len(voice_channels)}\n"
                  f"総接続者数: {total_members}人",
            inline=False
        )
        
        await ctx.send(embed=embed)

# Cogの追加関数（外部からのロード用）
async def setup(bot):
    """Cogをbotに追加する関数"""
    # この関数はbot.pyから呼ばれる際にconfig_managerが渡される
    pass