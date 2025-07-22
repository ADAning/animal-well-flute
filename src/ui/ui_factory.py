"""UI组件工厂 - 统一管理界面组件创建"""

from typing import Optional, Dict, Any
from .interactive import InteractiveManager
from .song_selector import SongSelector
from ..data.songs.song_manager import SongManager


class UIManagerFactory:
    """UI管理器工厂类 - 减少重复的UI组件初始化代码"""

    def __init__(self):
        # 缓存组件实例，避免重复创建
        self._interactive_managers: Dict[str, InteractiveManager] = {}
        self._song_selectors: Dict[str, SongSelector] = {}

    def get_interactive_manager(
        self, context_key: str = "default"
    ) -> InteractiveManager:
        """
        获取交互式管理器实例

        Args:
            context_key: 上下文键，用于区分不同场景的管理器

        Returns:
            InteractiveManager实例
        """
        if context_key not in self._interactive_managers:
            self._interactive_managers[context_key] = InteractiveManager()

        return self._interactive_managers[context_key]

    def get_song_selector(
        self, song_manager: SongManager, context_key: str = "default"
    ) -> SongSelector:
        """
        获取歌曲选择器实例

        Args:
            song_manager: 歌曲管理器实例
            context_key: 上下文键，用于区分不同场景的选择器

        Returns:
            SongSelector实例
        """
        # 为每个song_manager创建独立的选择器
        cache_key = f"{context_key}_{id(song_manager)}"

        if cache_key not in self._song_selectors:
            self._song_selectors[cache_key] = SongSelector(song_manager)

        return self._song_selectors[cache_key]

    def create_ui_context(
        self, song_manager: SongManager, context_name: str = "default"
    ) -> Dict[str, Any]:
        """
        创建完整的UI上下文

        Args:
            song_manager: 歌曲管理器实例
            context_name: 上下文名称

        Returns:
            包含ui_manager和song_selector的字典
        """
        return {
            "ui_manager": self.get_interactive_manager(context_name),
            "song_selector": self.get_song_selector(song_manager, context_name),
        }

    def clear_cache(self, context_key: Optional[str] = None) -> None:
        """
        清理缓存的组件实例

        Args:
            context_key: 要清理的上下文键，None表示清理所有
        """
        if context_key is None:
            self._interactive_managers.clear()
            self._song_selectors.clear()
        else:
            self._interactive_managers.pop(context_key, None)
            # 清理对应的song_selector（可能有多个）
            keys_to_remove = [
                key
                for key in self._song_selectors.keys()
                if key.startswith(f"{context_key}_")
            ]
            for key in keys_to_remove:
                self._song_selectors.pop(key, None)


# 全局UI工厂实例
ui_factory = UIManagerFactory()


def get_ui_context(
    song_manager: SongManager, context_name: str = "default"
) -> Dict[str, Any]:
    """
    便捷函数：获取UI上下文

    Args:
        song_manager: 歌曲管理器实例
        context_name: 上下文名称

    Returns:
        UI上下文字典
    """
    return ui_factory.create_ui_context(song_manager, context_name)
