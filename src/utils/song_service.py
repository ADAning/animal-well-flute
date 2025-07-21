"""共享的歌曲管理服务 - 单例模式"""

from typing import Optional
from pathlib import Path
from ..data.songs.song_manager import SongManager
from .logger import get_logger

logger = get_logger(__name__)


class SongService:
    """歌曲管理服务单例"""

    _instance: Optional["SongService"] = None
    _song_manager: Optional[SongManager] = None

    def __new__(cls) -> "SongService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        logger.debug("SongService singleton initialized")

    def get_song_manager(self, songs_dir: Optional[Path] = None) -> SongManager:
        """获取SongManager实例

        Args:
            songs_dir: 歌曲目录路径，仅在首次调用时生效

        Returns:
            SongManager实例
        """
        if self._song_manager is None:
            self._song_manager = SongManager(songs_dir or Path("songs"))
            logger.info(
                f"Created SongManager with directory: {songs_dir or Path('songs')}"
            )
        return self._song_manager

    def reload_songs(self, songs_dir: Optional[Path] = None) -> SongManager:
        """重新加载歌曲数据

        Args:
            songs_dir: 歌曲目录路径

        Returns:
            新的SongManager实例
        """
        self._song_manager = SongManager(songs_dir or Path("songs"))
        logger.info("Songs reloaded")
        return self._song_manager

    def is_initialized(self) -> bool:
        """检查是否已初始化SongManager"""
        return self._song_manager is not None


# 全局服务实例
song_service = SongService()


def get_song_manager(songs_dir: Optional[Path] = None) -> SongManager:
    """便捷函数：获取全局SongManager实例"""
    return song_service.get_song_manager(songs_dir)
