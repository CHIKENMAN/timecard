import discord
from discord.ext import commands
from discord.utils import escape_markdown
from datetime import datetime, timedelta, timezone
import json
import os
import asyncio
import logging
import threading
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定ファイルパス
CONFIG_PATH = 'config.json'

# 設定ファイルの読み込み
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return get_default_config()
    else:
        logger.warning(f"設定ファイル {CONFIG_PATH} が見つかりません。デフォルト設定を使用します。")
        return get_default_config()

def get_default_config():
    """デフォルト設定を取得"""
    return {
        "servers": {},
        "default_settings": {
            "enabled": True,
            "timezone_offset": 9
        }
    }

# 設定の保存
def save_config(config):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.debug("設定ファイルを保存しました")
    except IOError as e:
        logger.error(f"設定ファイル保存エラー: {e}")

# 設定管理クラス
class ConfigManager:
    def __init__(self):
        self._config = load_config()
        self._lock = threading.Lock()
        self._last_modified = self._get_file_modified_time()
        
    def _get_file_modified_time(self):
        """設定ファイルの最終更新時刻を取得"""
        try:
            return os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
        except OSError:
            return 0
    
    def _refresh_if_needed(self):
        """必要に応じて設定を再読み込み"""
        current_modified = self._get_file_modified_time()
        if current_modified > self._last_modified:
            logger.info("設定ファイルが更新されました。再読み込みします。")
            self._config = load_config()
            self._last_modified = current_modified
    
    def get_config(self):
        """現在の設定を取得（自動再読み込み）"""
        with self._lock:
            self._refresh_if_needed()
            return self._config.copy()
    
    def update_config(self, updater_func):
        """設定を安全に更新"""
        with self._lock:
            self._refresh_if_needed()
            updater_func(self._config)
            save_config(self._config)
            self._last_modified = self._get_file_modified_time()

# グローバル設定管理インスタンス
config_manager = ConfigManager()

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(intents=intents, command_prefix='!')

def get_server_config(guild_id):
    """サーバー固有の設定を取得"""
    config = config_manager.get_config()
    guild_id_str = str(guild_id)
    if guild_id_str in config["servers"]:
        return config["servers"][guild_id_str]
    return None

def get_destination_channel(guild_id):
    """サーバー用の通知チャンネルを取得"""
    server_config = get_server_config(guild_id)
    if server_config and server_config.get("enabled", True):
        channel_id = server_config.get("channel_id")
        if channel_id:
            try:
                return bot.get_channel(int(channel_id))
            except (ValueError, TypeError):
                logger.error(f"無効なチャンネルID: {channel_id}")
    return None

def get_timezone_offset(guild_id):
    """サーバー固有のタイムゾーンオフセットを取得"""
    config = config_manager.get_config()
    server_config = get_server_config(guild_id)
    if server_config:
        return server_config.get("timezone_offset", config["default_settings"]["timezone_offset"])
    return config["default_settings"]["timezone_offset"]

@bot.event
async def on_ready():
    logger.info(f'{bot.user} としてログインしました')
    logger.info(f'ボットは {len(bot.guilds)} サーバーに参加しています')
    for guild in bot.guilds:
        logger.info(f'- {guild.name} (ID: {guild.id})')
    
    # 設定監視タスクを開始
    asyncio.create_task(config_monitor_task())

async def config_monitor_task():
    """設定ファイル監視タスク"""
    while True:
        await asyncio.sleep(30)  # 30秒ごとにチェック
        try:
            # 設定の再読み込みをトリガー
            config_manager.get_config()
        except Exception as e:
            logger.error(f"設定監視エラー: {e}")

@bot.event
async def on_guild_join(guild):
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

@bot.command(name='setup')
async def setup_channel(ctx, channel: discord.TextChannel = None):
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
    
    config_manager.update_config(update_server_config)
    
    embed = discord.Embed(
        title="✅ 設定完了",
        description=f"ボイスチャンネル通知を {channel.mention} に設定しました。",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='disable')
async def disable_notifications(ctx):
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
    
    config_manager.update_config(wrapper)
    
    if success[0]:
        await ctx.send("✅ ボイスチャンネル通知を無効にしました。")
    else:
        await ctx.send("❌ このサーバーはまだ設定されていません。")

@bot.command(name='enable')
async def enable_notifications(ctx):
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
    
    config_manager.update_config(wrapper)
    
    if success[0]:
        await ctx.send("✅ ボイスチャンネル通知を有効にしました。")
    else:
        await ctx.send("❌ このサーバーはまず設定する必要があります。`!setup` コマンドを使用してください。")

@bot.command(name='status')
async def check_status(ctx):
    """現在の設定状況を確認"""
    guild_id = str(ctx.guild.id)
    server_config = get_server_config(guild_id)
    
    if server_config:
        channel_id = server_config.get("channel_id")
        enabled = server_config.get("enabled", True)
        timezone_offset = server_config.get("timezone_offset", 9)
        
        channel = bot.get_channel(int(channel_id)) if channel_id else None
        
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

@bot.command(name='reload')
async def reload_config(ctx):
    """設定の手動再読み込み（管理者用）"""
    if not ctx.author.guild_permissions.manage_guild:
        await ctx.send("❌ この機能を使用するには「サーバー管理」権限が必要です。")
        return
    
    try:
        # 強制的に設定を再読み込み
        config_manager._refresh_if_needed()
        await ctx.send("✅ 設定ファイルを再読み込みしました。")
    except Exception as e:
        logger.error(f"設定再読み込みエラー: {e}")
        await ctx.send("❌ 設定の再読み込みに失敗しました。")

@bot.event
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルの状態変更を検知"""
    if member.bot:  # ボットは除外
        return
    
    if before.channel == after.channel:  # チャンネルに変更がない場合
        return
    
    guild_id = member.guild.id
    destination = get_destination_channel(guild_id)
    
    if destination is None:
        return  # 設定されていない、または無効化されている
    
    # タイムゾーンオフセットを取得
    tz_offset = get_timezone_offset(guild_id)
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

@bot.command(name='help')
async def help_command(ctx):
    """ヘルプコマンド"""
    embed = discord.Embed(
        title="🤖 ボイスチャンネル通知ボット",
        description="ボイスチャンネルの参加・退出・移動を通知します。",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📋 コマンド一覧",
        value="`!setup [#チャンネル]` - 通知チャンネルを設定\n"
              "`!enable` - 通知を有効化\n"
              "`!disable` - 通知を無効化\n"
              "`!status` - 現在の設定を確認\n"
              "`!reload` - 設定を手動再読み込み\n"
              "`!help` - このヘルプを表示",
        inline=False
    )
    embed.add_field(
        name="⚙️ 権限",
        value="設定コマンドには「サーバー管理」権限が必要です。",
        inline=False
    )
    await ctx.send(embed=embed)

# エラーハンドリング
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ このコマンドを実行する権限がありません。")
    elif isinstance(error, commands.CommandNotFound):
        pass  # 存在しないコマンドは無視
    else:
        logger.error(f"コマンドエラー: {error}")
        await ctx.send("❌ エラーが発生しました。")

if __name__ == "__main__":
    token = os.getenv('BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        logger.error("BOT_TOKEN環境変数が設定されていません。")