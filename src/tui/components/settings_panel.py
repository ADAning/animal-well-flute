"""设置面板组件"""

from textual.widgets import Button, Static, Input, Switch, Select
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, Dict
import os

from ...config import get_app_config, save_app_config
from ...utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class SettingsPanel(Container):
    """设置面板组件"""

    # 自定义消息类
    class SettingsChanged(Message):
        """设置变更消息"""
        def __init__(self, setting_name: str, new_value) -> None:
            self.setting_name = setting_name
            self.new_value = new_value
            super().__init__()
    
    class ImportRequested(Message):
        """导入请求消息"""
        def __init__(self, import_type: str) -> None:
            self.import_type = import_type  # "image", "directory"
            super().__init__()

    # 响应式属性
    dark_mode: reactive[bool] = reactive(True)
    log_level: reactive[str] = reactive("INFO")
    default_bpm: reactive[int] = reactive(120)
    default_ready_time: reactive[int] = reactive(3)

    def __init__(self):
        """初始化设置面板组件"""
        super().__init__()
        self.config = get_app_config()
        self._load_current_settings()

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        with Vertical():
            # 标题
            yield Static("应用程序设置", classes="section_title")
            
            # 外观设置
            with Container(id="appearance_settings"):
                yield Static("外观设置", classes="subsection_title")
                with Horizontal(classes="setting_row"):
                    yield Static("深色模式:", classes="setting_label")
                    yield Switch(value=self.dark_mode, id="dark_mode_switch")
                
                with Horizontal(classes="setting_row"):
                    yield Static("日志级别:", classes="setting_label")
                    yield Select(
                        [
                            ("DEBUG", "调试"),
                            ("INFO", "信息"),
                            ("WARNING", "警告"),
                            ("ERROR", "错误")
                        ],
                        id="log_level_select"
                    )

            # 播放设置
            with Container(id="playback_settings"):
                yield Static("播放设置", classes="subsection_title")
                with Horizontal(classes="setting_row"):
                    yield Static("默认BPM:", classes="setting_label")
                    yield Input(
                        value=str(self.default_bpm),
                        placeholder="120",
                        id="default_bpm_input",
                        classes="number_input"
                    )
                
                with Horizontal(classes="setting_row"):
                    yield Static("默认准备时间:", classes="setting_label")
                    yield Input(
                        value=str(self.default_ready_time),
                        placeholder="3",
                        id="default_ready_time_input",
                        classes="number_input"
                    )

            # 高级设置
            with Container(id="advanced_settings"):
                yield Static("高级设置", classes="subsection_title")
                with Horizontal(classes="setting_row"):
                    yield Static("歌曲目录:", classes="setting_label")
                    yield Input(
                        value=str(self.config.songs_dir),
                        placeholder="songs",
                        id="songs_dir_input",
                        classes="path_input"
                    )
                
                # 导入功能
                yield Static("简谱导入", classes="subsection_title")
                with Horizontal(classes="setting_row"):
                    yield Button("📸 导入简谱图片", id="import_image_btn", variant="success")
                    yield Button("📁 批量导入目录", id="import_dir_btn", variant="default")
                with Horizontal(classes="setting_row"):
                    yield Static("AI服务状态:", classes="setting_label")
                    yield Static("检查中...", id="ai_status_display", classes="status_text")

            # 操作按钮
            with Container(id="settings_actions"):
                with Horizontal(classes="action_row"):
                    yield Button("💾 保存设置", id="save_btn", variant="primary")
                    yield Button("🔄 重置为默认", id="reset_btn", variant="default")
                    yield Button("📁 打开配置文件", id="open_config_btn", variant="default")

            # 信息显示
            with Container(id="settings_info"):
                yield Static("", id="settings_status")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._update_ui_from_settings()
        self._check_ai_status()

    def _load_current_settings(self) -> None:
        """加载当前设置"""
        # 从应用程序获取当前设置
        if hasattr(self.app, 'dark'):
            self.dark_mode = self.app.dark
        
        self.log_level = self.config.log_level
        # 其他设置可以从config中读取或使用默认值

    def _update_ui_from_settings(self) -> None:
        """根据设置更新UI"""
        try:
            # 更新开关状态
            dark_mode_switch = self.query_one("#dark_mode_switch", Switch)
            dark_mode_switch.value = self.dark_mode

            # 更新日志级别选择
            log_level_select = self.query_one("#log_level_select", Select)
            log_level_select.value = self.log_level

        except Exception:
            pass  # 如果组件还未完全初始化，忽略错误

    def _save_settings(self) -> None:
        """保存设置"""
        try:
            status = self.query_one("#settings_status", Static)
            status.update("💾 正在保存...")
            
            # 获取所有输入值
            songs_dir_input = self.query_one("#songs_dir_input", Input)
            songs_dir = songs_dir_input.value.strip() or "songs"
            
            # 更新配置对象
            self.config.log_level = self.log_level
            self.config.songs_dir = songs_dir
            
            # 保存配置到文件
            config_data = {
                "log_level": self.log_level,
                "songs_dir": songs_dir,
                "default_bpm": self.default_bpm,
                "default_ready_time": self.default_ready_time,
                "ui": {
                    "dark_mode": self.dark_mode
                }
            }
            
            save_app_config(config_data)
            
            # 应用深色模式设置
            if hasattr(self.app, 'dark'):
                self.app.dark = self.dark_mode
                
            # 应用日志级别设置
            setup_logging(self.log_level, tui_mode=True)

            status.update("✅ 设置已保存并应用")
            
            # 发送设置变更消息
            self.post_message(self.SettingsChanged("all", config_data))
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            status = self.query_one("#settings_status", Static)
            status.update(f"❌ 保存失败: {str(e)}")

    def _reset_settings(self) -> None:
        """重置为默认设置"""
        self.dark_mode = True
        self.log_level = "INFO"
        self.default_bpm = 120
        self.default_ready_time = 3
        
        self._update_ui_from_settings()
        
        status = self.query_one("#settings_status", Static)
        status.update("🔄 已重置为默认设置")

    def _open_config_file(self) -> None:
        """打开配置文件"""
        import os
        import subprocess
        import sys
        
        try:
            config_path = self.config.config_file
            
            # 如果配置文件不存在，先创建一个
            if not config_path.exists():
                self.config.save_config()
            
            if sys.platform == "win32":
                os.startfile(str(config_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(config_path)])
            else:
                subprocess.run(["xdg-open", str(config_path)])
            
            status = self.query_one("#settings_status", Static)
            status.update(f"📁 已打开配置文件: {config_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to open config file: {e}")
            status = self.query_one("#settings_status", Static)
            status.update(f"❌ 打开失败: {str(e)}")

    # 事件处理器
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "save_btn":
            self._save_settings()
        elif button_id == "reset_btn":
            self._reset_settings()
        elif button_id == "open_config_btn":
            self._open_config_file()
        elif button_id == "import_image_btn":
            self.post_message(self.ImportRequested("image"))
        elif button_id == "import_dir_btn":
            self.post_message(self.ImportRequested("directory"))

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """处理开关变化"""
        if event.switch.id == "dark_mode_switch":
            self.dark_mode = event.value

    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入变化"""
        if event.input.id == "default_bpm_input":
            try:
                bpm = int(event.value) if event.value else 120
                self.default_bpm = max(30, min(300, bpm))
            except ValueError:
                pass
        elif event.input.id == "default_ready_time_input":
            try:
                ready_time = int(event.value) if event.value else 3
                self.default_ready_time = max(0, min(10, ready_time))
            except ValueError:
                pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """处理选择器变化"""
        if event.select.id == "log_level_select":
            self.log_level = event.value

    def _check_ai_status(self) -> None:
        """检查AI服务状态"""
        try:
            ai_status_display = self.query_one("#ai_status_display", Static)
            
            # 检查环境变量中的API密钥
            google_key = os.getenv("GOOGLE_API_KEY")
            ark_key = os.getenv("ARK_API_KEY")
            
            if google_key:
                ai_status_display.update("✅ Gemini可用")
            elif ark_key:
                ai_status_display.update("✅ Doubao可用")
            else:
                ai_status_display.update("❌ 未配置API密钥")
                
        except Exception:
            pass

    # 响应式属性监听器
    def watch_dark_mode(self, dark_mode: bool) -> None:
        """监听深色模式变化"""
        pass  # 可以在这里添加额外的处理逻辑

    # 公共方法
    def get_current_settings(self) -> Dict:
        """获取当前设置"""
        return {
            "dark_mode": self.dark_mode,
            "log_level": self.log_level,
            "default_bpm": self.default_bpm,
            "default_ready_time": self.default_ready_time
        }