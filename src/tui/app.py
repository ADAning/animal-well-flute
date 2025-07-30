"""Animal Well Flute TUI 主应用程序"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, TabbedContent, TabPane
from textual.binding import Binding
from textual.reactive import reactive
from typing import Optional
import asyncio

from ..services.song_service_base import SongServiceBase
from ..utils.logger import setup_logging
from ..config import get_app_config
from .components.song_browser import SongBrowser
from .components.play_control import PlayControl
from .components.analysis_panel import AnalysisPanel
from .components.settings_panel import SettingsPanel


class AnimalWellFluteApp(App):
    """Animal Well Flute TUI 主应用程序"""
    
    CSS_PATH = "app.tcss"
    TITLE = "Animal Well Flute - TUI Mode"
    SUB_TITLE = "简谱笛子自动演奏工具"
    
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("ctrl+c", "quit", "退出", priority=True),
        Binding("f1", "help", "帮助"),
        Binding("f2", "toggle_dark", "切换主题"),
    ]
    
    # 响应式状态
    current_song: reactive[Optional[str]] = reactive(None)
    playing_status: reactive[str] = reactive("stopped")
    
    def __init__(self):
        """初始化应用程序"""
        super().__init__()
        
        # 初始化配置和服务
        self.config = get_app_config()
        setup_logging(self.config.log_level)
        self.song_service = SongServiceBase()
        
        # 设置播放回调
        self.song_service.set_play_callback(self._handle_play_song)

    def compose(self) -> ComposeResult:
        """构建应用程序界面"""
        yield Header(show_clock=True)
        
        with TabbedContent(initial="dashboard"):
            # 主仪表板
            with TabPane("仪表板", id="dashboard"):
                yield Container(
                    Static("🎵 欢迎使用 Animal Well Flute TUI", id="welcome"),
                    Horizontal(
                        Button("🎵 播放歌曲", id="play_btn", variant="primary"),
                        Button("🎼 分析歌曲", id="analyze_btn"),
                        Button("📋 歌曲列表", id="list_btn"),
                        Button("📸 导入简谱", id="import_btn"),
                        classes="button_row"
                    ),
                    Static("当前歌曲: 无", id="current_song_display"),
                    Static("播放状态: 停止", id="play_status_display"),
                    id="dashboard_content"
                )
            
            # 歌曲浏览器
            with TabPane("歌曲浏览", id="browser"):
                yield SongBrowser(self.song_service)
            
            # 播放控制
            with TabPane("播放控制", id="player"):
                yield PlayControl(self.song_service)
            
            # 分析工具
            with TabPane("分析工具", id="analyzer"):
                yield AnalysisPanel(self.song_service)
            
            # 设置
            with TabPane("设置", id="settings"):
                yield SettingsPanel()
        
        yield Footer()

    def on_mount(self) -> None:
        """应用程序启动时的初始化"""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        self.theme = "tokyo-night"
        
        # 设置默认焦点
        self.query_one("#play_btn").focus()
        
        # 初始化状态显示
        self._update_status_displays()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "play_btn":
            self._handle_play_action()
        elif button_id == "analyze_btn":
            self._handle_analyze_action()
        elif button_id == "list_btn":
            self._handle_list_action()
        elif button_id == "import_btn":
            self._handle_import_action()

    def _handle_play_action(self):
        """处理播放动作"""
        if self.current_song:
            # 如果已经选择了歌曲，使用统一的播放方法
            self.start_playback(self.current_song, switch_tab=True)
        else:
            # 如果没有选择歌曲，引导用户到歌曲浏览器选择
            self.query_one(TabbedContent).active = "browser"
            self.notify("请先选择要播放的歌曲")

    def _handle_analyze_action(self):
        """处理分析动作"""
        if self.current_song:
            # 如果已经选择了歌曲，直接切换到分析工具并开始分析
            self.query_one(TabbedContent).active = "analyzer"
            try:
                analysis_panel = self.query_one(AnalysisPanel)
                analysis_panel.set_song_for_analysis(self.current_song)
                self.notify(f"正在分析: {self.current_song}")
            except Exception as e:
                self.notify(f"设置分析歌曲失败: {str(e)}", severity="error")
        else:
            # 如果没有选择歌曲，引导用户到歌曲浏览器选择
            self.query_one(TabbedContent).active = "browser"
            self.notify("请先选择要分析的歌曲")

    def _handle_list_action(self):
        """处理列表动作"""
        # 切换到歌曲浏览器标签页
        self.query_one(TabbedContent).active = "browser"
        self.notify("切换到歌曲浏览器")

    def _handle_import_action(self):
        """处理导入动作"""
        # TODO: 实现图片导入功能
        self.notify("导入功能正在开发中...")
    
    def start_playback(self, song_name: str, switch_tab: bool = True) -> bool:
        """统一的播放启动方法
        
        Args:
            song_name: 要播放的歌曲名称
            switch_tab: 是否自动切换到播放控制标签页
            
        Returns:
            bool: 是否成功启动播放
        """
        try:
            # 更新当前歌曲状态
            self.current_song = song_name
            self.playing_status = "loading"
            self._update_status_displays()
            
            # 切换到播放控制标签页（如果需要）
            if switch_tab:
                self.query_one(TabbedContent).active = "player"
            
            # 获取播放控制组件并开始播放
            play_control = self.query_one(PlayControl)
            play_control.set_current_song(song_name, auto_play=True)
            
            self.notify(f"正在播放: {song_name}")
            return True
            
        except Exception as e:
            self.notify(f"启动播放失败: {str(e)}", severity="error")
            return False

    def _handle_play_song(self, song_name: str, **kwargs):
        """处理歌曲播放回调"""
        # 实际的播放逻辑，这里暂时只更新状态
        self.current_song = song_name
        self.playing_status = "playing"
        self._update_status_displays()
        
        # 同时更新播放控制组件
        try:
            play_control = self.query_one(PlayControl)
            play_control.set_current_song(song_name)
        except Exception:
            pass  # 如果组件不可用，忽略错误

    # 组件消息处理器
    def on_song_browser_song_selected(self, message: SongBrowser.SongSelected) -> None:
        """处理歌曲选择消息"""
        self.current_song = message.song_name
        self._update_status_displays()
        self.notify(f"已选择歌曲: {message.song_name}")

    def on_song_browser_play_requested(self, message: SongBrowser.PlayRequested) -> None:
        """处理播放请求消息"""
        # 使用统一的播放方法
        self.start_playback(message.song_name, switch_tab=True)

    def on_song_browser_analyze_requested(self, message: SongBrowser.AnalyzeRequested) -> None:
        """处理分析请求消息"""
        self.current_song = message.song_name
        self._update_status_displays()
        
        # 切换到分析标签页并设置分析歌曲
        self.query_one(TabbedContent).active = "analyzer"
        
        try:
            analysis_panel = self.query_one(AnalysisPanel)
            analysis_panel.set_song_for_analysis(message.song_name)
        except Exception as e:
            self.notify(f"设置分析歌曲失败: {str(e)}", severity="error")

    def on_play_control_play_started(self, message: PlayControl.PlayStarted) -> None:
        """处理播放开始消息"""
        self.playing_status = "playing"
        self._update_status_displays()
        self.notify(f"开始播放: {message.song_name}")

    def on_play_control_play_stopped(self, message: PlayControl.PlayStopped) -> None:
        """处理播放停止消息"""
        self.playing_status = "stopped"
        self._update_status_displays()
        self.notify(f"停止播放: {message.song_name}")

    def on_play_control_play_paused(self, message: PlayControl.PlayPaused) -> None:
        """处理播放暂停消息"""
        self.playing_status = "paused"
        self._update_status_displays()
        self.notify(f"暂停播放: {message.song_name}")

    def on_analysis_panel_analysis_completed(self, message: AnalysisPanel.AnalysisCompleted) -> None:
        """处理分析完成消息"""
        self.notify(f"分析完成: {message.song_name}")
        # 可以在这里添加更多的处理逻辑，比如更新仪表板显示等

    def _update_status_displays(self):
        """更新状态显示"""
        try:
            current_song_widget = self.query_one("#current_song_display")
            play_status_widget = self.query_one("#play_status_display")
            
            current_song_text = f"当前歌曲: {self.current_song or '无'}"
            play_status_text = f"播放状态: {self._get_status_text()}"
            
            current_song_widget.update(current_song_text)
            play_status_widget.update(play_status_text)
            
            # 更新欢迎文本，提供操作提示
            welcome_widget = self.query_one("#welcome")
            if self.current_song:
                welcome_text = f"🎵 已选择 {self.current_song} - 点击播放按钮开始演奏"
            else:
                welcome_text = "🎵 欢迎使用 Animal Well Flute TUI - 点击歌曲列表选择歌曲"
            welcome_widget.update(welcome_text)
            
        except Exception:
            pass  # 如果更新失败，忽略错误

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            "stopped": "停止",
            "playing": "播放中",
            "paused": "暂停",
            "loading": "加载中"
        }
        return status_map.get(self.playing_status, "未知")

    def watch_current_song(self, new_song: Optional[str]) -> None:
        """监听当前歌曲变化"""
        self._update_status_displays()

    def watch_playing_status(self, new_status: str) -> None:
        """监听播放状态变化"""
        self._update_status_displays()

    def action_help(self) -> None:
        """显示帮助信息"""
        help_text = """
Animal Well Flute TUI 帮助

快捷键:
- q, Ctrl+C: 退出应用程序
- F1: 显示此帮助
- F2: 切换亮/暗主题
- Tab: 在标签页间切换

功能:
- 仪表板: 主要操作入口
- 歌曲浏览: 浏览和搜索歌曲
- 播放控制: 控制歌曲播放
- 分析工具: 分析歌曲音域和映射
- 设置: 配置应用程序选项
        """
        self.notify(help_text, title="帮助", timeout=10)

    def action_toggle_dark(self) -> None:
        """切换深色/浅色主题"""
        self.dark = not self.dark
        theme = "深色" if self.dark else "浅色"
        self.notify(f"已切换到{theme}主题")


def run_tui_app():
    """启动 TUI 应用程序"""
    app = AnimalWellFluteApp()
    app.run()


if __name__ == "__main__":
    run_tui_app()