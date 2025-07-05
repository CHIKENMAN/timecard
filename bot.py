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

# DiscordBotクラス
class DiscordVoiceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.voice_states = True
        intents.guilds = True
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # 設定管理を初期化
        self.config_manager = ConfigManager()
        
        # デフォルトのhelpコマンドを削除（カスタムヘルプを使用）
        self.remove_command('help')
    
    async def setup_hook(self):
        """ボット起動時の初期設定"""
        logger.info("ボットの初期設定を開始します...")
        
        # Cogをロード
        await self.load_cogs()
        
        # 設定監視タスクを開始
        self.loop.create_task(self.config_monitor_task())
        
        logger.info("ボットの初期設定が完了しました")
    
    async def load_cogs(self):
        """Cogをロード"""
        cogs_to_load = [
            'cogs.config_cog',
            'cogs.voice_cog',
            'cogs.utility_cog'
        ]
        
        for cog in cogs_to_load:
            try:
                # Cogをロード
                if cog == 'cogs.config_cog':
                    from cogs.config_cog import ConfigCog
                    await self.add_cog(ConfigCog(self, self.config_manager))
                elif cog == 'cogs.voice_cog':
                    from cogs.voice_cog import VoiceCog
                    await self.add_cog(VoiceCog(self, self.config_manager))
                elif cog == 'cogs.utility_cog':
                    from cogs.utility_cog import UtilityCog
                    await self.add_cog(UtilityCog(self, self.config_manager))
                
                logger.info(f"Cog '{cog}' をロードしました")
            except Exception as e:
                logger.error(f"Cog '{cog}' のロードに失敗: {e}")
    
    async def config_monitor_task(self):
        """設定ファイル監視タスク"""
        while True:
            await asyncio.sleep(30)  # 30秒ごとにチェック
            try:
                # 設定の再読み込みをトリガー
                self.config_manager.get_config()
            except Exception as e:
                logger.error(f"設定監視エラー: {e}")
    
    async def on_ready(self):
        """ボット起動完了時の処理"""
        logger.info(f'{self.user} としてログインしました')
        logger.info(f'ボットは {len(self.guilds)} サーバーに参加しています')
        for guild in self.guilds:
            logger.info(f'- {guild.name} (ID: {guild.id})')
        
        # アクティビティを設定
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="ボイスチャンネル | !help"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """コマンドエラーの処理"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ このコマンドを実行する権限がありません。")
        elif isinstance(error, commands.CommandNotFound):
            pass  # 存在しないコマンドは無視
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 必要な引数が不足しています。`!help` でコマンドの使い方を確認してください。")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ 引数の形式が正しくありません。`!help` でコマンドの使い方を確認してください。")
        else:
            logger.error(f"予期しないコマンドエラー: {error}")
            await ctx.send("❌ 予期しないエラーが発生しました。")
    
    async def on_disconnect(self):
        """ボット切断時の処理"""
        logger.warning("ボットがDiscordから切断されました")
    
    async def on_resumed(self):
        """ボット再接続時の処理"""
        logger.info("ボットがDiscordに再接続しました")

# メイン関数
async def main():
    """ボットのメイン関数"""
    bot = DiscordVoiceBot()
    
    # ボットトークンの取得
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN環境変数が設定されていません。")
        return
    
    # ボットを起動
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("ボットの停止が要求されました")
    except Exception as e:
        logger.error(f"ボットの実行中にエラーが発生しました: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("プログラムが中断されました")
    except Exception as e:
        logger.error(f"プログラムの実行中にエラーが発生しました: {e}")