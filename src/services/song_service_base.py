"""统一的歌曲服务基类 - 封装通用的歌曲操作逻辑"""

from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from ..config import get_app_config
from ..utils.song_service import get_song_manager
from ..utils.logger import setup_logging, get_logger
from ..utils.error_handler import ErrorHandler, with_error_handling, UserFeedback
from ..ui import InteractiveManager, SongSelector

logger = get_logger(__name__)


class SongServiceBase:
    """歌曲服务基类 - 封装通用的歌曲操作逻辑，减少重复代码"""

    def __init__(self, setup_logging_level: bool = True):
        """
        初始化歌曲服务

        Args:
            setup_logging_level: 是否设置日志级别
        """
        # 获取配置
        self.config = get_app_config()

        # 设置日志
        if setup_logging_level:
            setup_logging(self.config.log_level)

        # 获取共享的歌曲管理器
        self.song_manager = get_song_manager(self.config.songs_dir)

        # 创建UI组件（延迟初始化）
        self._ui_manager = None
        self._song_selector = None

        logger.debug("SongServiceBase initialized")

    @property
    def ui_manager(self) -> InteractiveManager:
        """获取UI管理器（延迟初始化）"""
        if self._ui_manager is None:
            self._ui_manager = InteractiveManager()
        return self._ui_manager

    @property
    def song_selector(self) -> SongSelector:
        """获取歌曲选择器（延迟初始化）"""
        if self._song_selector is None:
            self._song_selector = SongSelector(self.song_manager)
        return self._song_selector

    def get_song_by_name_or_interactive(
        self,
        song_name: Optional[str],
        interactive: bool = False,
        prompt_text: str = "选择歌曲",
        for_playing: bool = False,
        auto_select_unique: bool = False,
    ) -> Optional[str]:
        """
        通过名称获取歌曲，或者使用交互式选择

        Args:
            song_name: 歌曲名称（可选）
            interactive: 是否强制使用交互式模式
            prompt_text: 交互选择时的提示文本
            for_playing: 是否用于演奏目的
            auto_select_unique: 是否自动选择唯一匹配的歌曲（不询问确认）

        Returns:
            选择的歌曲名称，如果用户取消则返回None
        """
        # 交互式选择歌曲
        if interactive or song_name is None:
            self.ui_manager.show_welcome()

            # 根据用途设置是否需要确认
            use_for_playing = for_playing and not auto_select_unique

            selected_song_key = self.song_selector.select_song_simple(
                prompt_text,
                for_playing=use_for_playing,
                auto_confirm=auto_select_unique,
            )

            if selected_song_key is None:
                action_text = "演奏" if for_playing else "操作"
                self.ui_manager.show_info(f"{action_text}已取消")
                return None

            return selected_song_key

        return song_name

    def get_song_safely(
        self, song_name: str
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        安全地获取歌曲，统一错误处理

        Args:
            song_name: 歌曲名称

        Returns:
            (成功标志, 歌曲对象, 错误信息)
        """
        try:
            song = self.song_manager.get_song(song_name)
            return True, song, None
        except Exception as e:
            logger.error(f"Failed to get song '{song_name}': {e}")

            # 使用统一的错误处理器
            try:
                available_songs = self.song_manager.list_song_names()
            except Exception:
                available_songs = None

            error_msg = ErrorHandler.handle_song_not_found(
                song_name, available_songs, show_suggestions=True
            )

            return False, None, error_msg

    def print_song_info(self, song: Any, song_name: str) -> None:
        """
        打印歌曲基本信息

        Args:
            song: 歌曲对象
            song_name: 歌曲名称
        """
        print(f"🎵 乐曲: {song.name}")
        logger.debug(f"Song info: name={song.name}, bpm={song.bpm}")

    def get_effective_bpm(self, song: Any, bpm_override: Optional[int] = None) -> int:
        """
        获取有效的BPM值

        Args:
            song: 歌曲对象
            bpm_override: BPM覆盖值

        Returns:
            有效的BPM值
        """
        return bpm_override or song.bpm or self.config.default_bpm

    def get_effective_ready_time(
        self, ready_time_override: Optional[int] = None
    ) -> int:
        """
        获取有效的准备时间

        Args:
            ready_time_override: 准备时间覆盖值

        Returns:
            有效的准备时间
        """
        return (
            ready_time_override
            if ready_time_override is not None
            else self.config.default_ready_time
        )

    def handle_common_error(self, error: Exception, operation: str = "操作") -> bool:
        """
        处理常见错误

        Args:
            error: 异常对象
            operation: 操作描述

        Returns:
            是否已处理（总是返回False表示操作失败）
        """
        error_msg = ErrorHandler.handle_generic_error(error, operation)
        print(error_msg)
        return False

    @with_error_handling("列出歌曲", return_on_error=False)
    def list_all_songs_info(self) -> bool:
        """
        列出所有歌曲信息（非交互式）

        Returns:
            操作是否成功
        """
        UserFeedback.print_operation_start("加载歌曲列表")
        print("📋 可用乐曲:")

        songs_info = self.song_manager.list_songs_with_info()
        for song_info in songs_info:
            name = song_info["name"]
            bpm = song_info["bpm"]
            description = song_info["description"]
            desc_text = f" - {description[:40]}..." if description else ""
            print(f"   {name:<25} (BPM: {bpm}){desc_text}")

        UserFeedback.print_operation_complete("加载歌曲列表", success=True)
        return True

    def handle_interactive_list_songs(self) -> None:
        """
        处理交互式歌曲列表浏览功能
        """
        self.ui_manager.show_welcome("歌曲列表浏览")

        while True:
            options = [
                {"key": "browse", "desc": "🎵 浏览和选择歌曲 (动态搜索)"},
                {"key": "list", "desc": "📋 显示所有歌曲 (静态列表)"},
            ]

            choice = self.ui_manager.show_menu("歌曲浏览模式", options, show_quit=True)

            if choice is None:
                break

            try:
                if choice == "browse":
                    self._handle_dynamic_browse()
                elif choice == "list":
                    self._handle_static_list()

            except KeyboardInterrupt:
                self.ui_manager.show_info("\n操作已取消")
                break
            except Exception as e:
                self.ui_manager.show_error(f"执行操作时发生错误: {e}")
                self.ui_manager.pause()

        self.ui_manager.exit_gracefully()

    def _handle_dynamic_browse(self) -> None:
        """处理动态歌曲浏览"""
        self.ui_manager.show_info("进入动态歌曲浏览模式...")
        self.ui_manager.show_info("💡 提示: 输入关键词可实时搜索，输入数字可直接选择")

        selected_song = self.song_selector.select_song_simple(
            "🎵 浏览歌曲 (支持实时搜索)", for_playing=True
        )

        if selected_song:
            self.ui_manager.show_success(f"您选择了: {selected_song}")
            self._show_song_details_and_play(selected_song)

    def _handle_static_list(self) -> None:
        """处理静态歌曲列表"""
        self.ui_manager.show_info("正在加载歌曲列表...")
        selected_song_from_list = self.song_selector.list_all_songs()

        if selected_song_from_list:
            self.ui_manager.show_info(f"已选择歌曲: {selected_song_from_list}")
            if self.ui_manager.confirm("是否要现在演奏这首歌?"):
                self._play_song_with_defaults(selected_song_from_list)

    def _show_song_details_and_play(self, selected_song: str) -> None:
        """显示歌曲详情并询问是否演奏"""
        try:
            success, song, error_msg = self.get_song_safely(selected_song)
            if not success:
                self.ui_manager.show_warning(f"无法获取歌曲详细信息: {error_msg}")
                self.ui_manager.pause()
                return

            # 显示歌曲详情
            self.ui_manager.show_info(f"🎼 歌曲名称: {song.name}")
            self.ui_manager.show_info(f"🎵 BPM: {song.bpm}")
            if song.description:
                self.ui_manager.show_info(f"📝 描述: {song.description}")
            self.ui_manager.show_info(f"📊 小节数: {len(song.jianpu)}")

            # 演奏选项处理
            self._handle_play_options(selected_song, song)

        except Exception as e:
            self.ui_manager.show_warning(f"无法获取歌曲详细信息: {e}")
            self.ui_manager.pause()

    def _handle_play_options(self, selected_song: str, song: Any) -> None:
        """处理演奏选项"""
        self.ui_manager.show_progress("准备演奏...")

        play_options = [
            {"key": "default", "desc": "🎵 使用默认设置演奏"},
            {"key": "custom", "desc": "⚙️ 自定义演奏参数"},
        ]

        play_choice = self.ui_manager.show_menu(
            "演奏选项", play_options, show_quit=False
        )

        # 准备演奏参数
        strategy_args = ["optimal"]
        bpm = None
        ready_time = None

        if play_choice == "custom":
            strategy_args, bpm, ready_time = self._get_custom_play_params(song)

        # 执行演奏
        self._execute_play(selected_song, strategy_args, bpm, ready_time)

    def _get_custom_play_params(
        self, song: Any
    ) -> Tuple[list, Optional[int], Optional[int]]:
        """获取自定义演奏参数"""
        # 策略选择
        strategy_options = [
            {"key": "optimal", "desc": "🎯 最佳策略 (推荐)"},
            {"key": "high", "desc": "⬆️ 高音优先策略"},
            {"key": "low", "desc": "⬇️ 低音优先策略"},
        ]

        strategy_choice = self.ui_manager.show_menu(
            "选择演奏策略", strategy_options, show_quit=False
        )
        strategy_args = [strategy_choice] if strategy_choice else ["optimal"]

        # BPM设置
        custom_bpm = self.ui_manager.input_number(
            f"自定义BPM (当前: {song.bpm}, 留空使用默认)",
            default=None,
            min_value=30,
            max_value=300,
        )
        bpm = int(custom_bpm) if custom_bpm else None

        # 准备时间
        custom_ready_time = self.ui_manager.input_number(
            "准备时间(秒) (留空使用默认)", default=None, min_value=0, max_value=30
        )
        ready_time = int(custom_ready_time) if custom_ready_time is not None else None

        return strategy_args, bpm, ready_time

    def set_play_callback(self, play_callback):
        """设置演奏回调函数，避免循环导入"""
        self._play_callback = play_callback

    def _execute_play(
        self,
        song_name: str,
        strategy_args: list,
        bpm: Optional[int],
        ready_time: Optional[int],
    ) -> None:
        """执行演奏"""
        if not hasattr(self, "_play_callback") or self._play_callback is None:
            self.ui_manager.show_error("演奏功能未配置")
            return

        self.ui_manager.show_info("🎼 开始演奏...")
        try:
            result = self._play_callback(
                song_name, strategy_args, bpm, ready_time, False
            )
            if result:
                self.ui_manager.show_success("🎉 演奏完成！")
            else:
                self.ui_manager.show_warning("演奏未完成")
            self.ui_manager.pause()
        except Exception as e:
            self.ui_manager.show_error(f"演奏时发生错误: {e}")
            self.ui_manager.pause()

    def _play_song_with_defaults(self, song_name: str) -> None:
        """使用默认设置演奏歌曲"""
        if not hasattr(self, "_play_callback") or self._play_callback is None:
            self.ui_manager.show_error("演奏功能未配置")
            return

        self.ui_manager.show_info("🎼 开始演奏...")
        try:
            result = self._play_callback(song_name, ["optimal"], None, None, False)
            if result:
                self.ui_manager.show_success("🎉 演奏完成！")
            else:
                self.ui_manager.show_warning("演奏未完成")
            self.ui_manager.pause()
        except Exception as e:
            self.ui_manager.show_error(f"演奏时发生错误: {e}")
            self.ui_manager.pause()
