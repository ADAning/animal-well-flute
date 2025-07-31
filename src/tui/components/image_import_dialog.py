"""图片导入对话框组件"""

from textual.widgets import Button, Static, Input, Select, ProgressBar
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

from ...tools.sheet_importer import JianpuSheetImporter
from ...tools.config import ToolsConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ImageImportDialog(ModalScreen):
    """图片导入对话框"""
    
    # 自定义消息
    class ImportCompleted(Message):
        """导入完成消息"""
        def __init__(self, results: Dict[str, Any]) -> None:
            self.results = results
            super().__init__()
    
    class ImportCancelled(Message):
        """导入取消消息"""
        pass
    
    # 响应式属性
    selected_files: reactive[List[Path]] = reactive([])
    import_status: reactive[str] = reactive("ready")  # ready, importing, completed, error
    progress_value: reactive[int] = reactive(0)
    status_message: reactive[str] = reactive("选择要导入的图片文件")
    
    def __init__(self):
        """初始化图片导入对话框"""
        super().__init__()
        self.importer = JianpuSheetImporter()
        self.import_results = None
    
    def compose(self) -> ComposeResult:
        """构建对话框界面"""
        with Container(id="import_dialog"):
            yield Static("📸 导入简谱图片", id="dialog_title")
            
            # 文件选择区域
            with Container(id="file_selection", classes="section") as file_container:
                file_container.border_title = "📁 文件选择"
                with Horizontal(classes="file_row"):
                    yield Static("文件路径:", classes="option_label")
                    yield Input(placeholder="选择图片文件或文件夹路径", id="file_path_input")
                    yield Button("📁 浏览", id="browse_btn", variant="default")
                
                with Horizontal(classes="file_row"):
                    yield Static("导入模式:", classes="option_label")
                    yield Select([
                        ("single", "单个文件"),
                        ("multiple", "多个文件合并"),
                        ("folder", "整个文件夹")
                    ], id="import_mode", value="single")
                    yield Button("✅ 添加", id="add_file_btn", variant="default")
            
            # 导入选项
            with Container(id="import_options", classes="section") as options_container:
                options_container.border_title = "⚙️ 导入选项"
                with Horizontal(classes="option_row"):
                    yield Static("AI服务:", classes="option_label")
                    yield Select([
                        ("auto", "自动选择"),
                        ("google", "Google Gemini"),
                        ("doubao", "豆包")
                    ], id="provider_select", value="auto")
                
                with Horizontal(classes="option_row"):
                    yield Static("输出名称:", classes="option_label")
                    yield Input(placeholder="可选，默认使用文件名", id="output_name_input")
            
            # 导入进度
            with Container(id="import_progress", classes="section") as progress_container:
                progress_container.border_title = "📈 导入进度"
                yield ProgressBar(total=100, show_percentage=True, id="progress_bar")
                yield Static("选择要导入的图片文件", id="status_display")
                yield Static("", id="result_display")
            
            # 按钮区域
            with Container(id="dialog_buttons"):
                with Horizontal(classes="button_row"):
                    yield Button("🚀 开始导入", id="start_import_btn", variant="primary")
                    yield Button("❌ 取消", id="cancel_btn", variant="default")
    
    def on_mount(self) -> None:
        """对话框挂载时初始化"""
        # 检查AI服务状态
        self._check_ai_services()
    
    def _check_ai_services(self) -> None:
        """检查AI服务状态"""
        try:
            status = self.importer.get_provider_status()
            available_providers = [("auto", "自动选择")]
            
            for provider, info in status.items():
                if info.get("available", False):
                    name = {"google": "Google Gemini", "doubao": "豆包"}.get(provider, provider)
                    available_providers.append((provider, f"{name} ✅"))
                else:
                    name = {"google": "Google Gemini", "doubao": "豆包"}.get(provider, provider) 
                    available_providers.append((provider, f"{name} ❌"))
            
            # 更新服务选择器
            provider_select = self.query_one("#provider_select", Select)
            provider_select.set_options(available_providers)
            
        except Exception as e:
            logger.warning(f"Failed to check AI services: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "browse_btn":
            self._browse_files()
        elif button_id == "add_file_btn":
            self._add_files()
        elif button_id == "start_import_btn":
            asyncio.create_task(self._start_import())
        elif button_id == "cancel_btn":
            self._cancel_import()
    
    def _browse_files(self) -> None:
        """浏览文件"""
        # 这里应该打开文件浏览器，简化实现
        file_path_input = self.query_one("#file_path_input", Input)
        if not file_path_input.value:
            file_path_input.value = "请输入文件路径"
    
    def _add_files(self) -> None:
        """添加文件到列表"""
        file_path_input = self.query_one("#file_path_input", Input)
        import_mode = self.query_one("#import_mode", Select)
        
        path_str = file_path_input.value.strip()
        if not path_str or path_str == "请输入文件路径":
            self.status_message = "请输入有效的文件路径"
            return
        
        try:
            path = Path(path_str)
            
            if import_mode.value == "folder":
                # 文件夹模式
                if not path.exists() or not path.is_dir():
                    self.status_message = "指定路径不是有效的文件夹"
                    return
                
                # 查找图片文件
                image_files = []
                for ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff']:
                    image_files.extend(path.glob(f"*.{ext}"))
                    image_files.extend(path.glob(f"*.{ext.upper()}"))
                
                if not image_files:
                    self.status_message = f"文件夹中未找到图片文件: {path}"
                    return
                
                self.selected_files = sorted(image_files, key=lambda x: x.name)
                self.status_message = f"已选择文件夹: {len(self.selected_files)} 个图片文件"
            
            else:
                # 单个或多个文件模式
                if not path.exists() or not path.is_file():
                    self.status_message = "指定路径不是有效的文件"
                    return
                
                # 验证是否为图片文件
                valid_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}
                if path.suffix.lower() not in valid_extensions:
                    self.status_message = f"不支持的文件格式: {path.suffix}"
                    return
                
                # 添加到文件列表
                if path not in self.selected_files:
                    new_files = list(self.selected_files)
                    new_files.append(path)
                    self.selected_files = new_files
                    self.status_message = f"已添加文件: {len(self.selected_files)} 个"
                else:
                    self.status_message = "文件已在列表中"
        
        except Exception as e:
            self.status_message = f"添加文件失败: {str(e)}"
    
    async def _start_import(self) -> None:
        """开始导入过程"""
        if not self.selected_files:
            self.status_message = "请先选择要导入的文件"
            return
        
        if self.import_status == "importing":
            return  # 正在导入中，忽略重复点击
        
        try:
            self.import_status = "importing"
            self.progress_value = 0
            self.status_message = "正在准备导入..."
            
            # 获取导入选项
            provider_select = self.query_one("#provider_select", Select)
            output_name_input = self.query_one("#output_name_input", Input)
            import_mode = self.query_one("#import_mode", Select)
            
            provider = str(provider_select.value) if provider_select.value != "auto" else None
            output_name = output_name_input.value.strip() or None
            mode = str(import_mode.value)
            
            # 执行导入
            if mode == "folder":
                # 文件夹模式：所有文件合并为一首歌
                self.status_message = "正在处理文件夹中的图片..."
                self.progress_value = 25
                
                folder_path = self.selected_files[0].parent
                result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.importer.import_folder_as_single_song,
                    folder_path, provider, output_name
                )
                
            elif mode == "multiple":
                # 多文件模式：合并为一首歌
                self.status_message = "正在处理多个图片文件..."
                self.progress_value = 25
                
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.importer.import_multiple_images,
                    self.selected_files, provider, output_name
                )
                
            else:
                # 单文件模式
                if len(self.selected_files) == 1:
                    self.status_message = "正在处理图片文件..."
                    self.progress_value = 25
                    
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.importer.import_single_image,
                        self.selected_files[0], provider, output_name
                    )
                else:
                    # 批量导入
                    self.status_message = "正在批量处理图片文件..."
                    self.progress_value = 25
                    
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.importer.import_batch,
                        self.selected_files, provider
                    )
            
            self.progress_value = 100
            self.import_results = result
            
            if result.get("success", False):
                self.import_status = "completed"
                if "output_file" in result:
                    self.status_message = f"导入成功！生成文件: {Path(result['output_file']).name}"
                else:
                    success_count = result.get("successful_imports", 0)
                    total_count = result.get("total_images", 0)
                    self.status_message = f"批量导入完成：{success_count}/{total_count} 个文件成功"
                
                # 显示结果详情
                self._display_results(result)
                
                # 延迟后自动关闭对话框
                asyncio.create_task(self._auto_close())
            else:
                self.import_status = "error"
                error_msg = result.get("error", "未知错误")
                self.status_message = f"导入失败: {error_msg}"
        
        except Exception as e:
            self.import_status = "error"
            self.status_message = f"导入过程出错: {str(e)}"
            logger.error(f"Import failed: {e}")
    
    def _display_results(self, result: Dict[str, Any]) -> None:
        """显示导入结果"""
        result_display = self.query_one("#result_display", Static)
        
        if result.get("success", False):
            if "output_file" in result:
                # 单个文件结果
                song_name = result.get("song_name", "未知")
                measures = result.get("measures_count", 0)
                provider = result.get("provider_used", "unknown")
                
                result_text = f"✅ {song_name} | {measures}小节 | 使用{provider}"
                
                if result.get("has_warnings", False):
                    result_text += " ⚠️ 有警告"
            else:
                # 批量导入结果
                success = result.get("successful_imports", 0)
                total = result.get("total_images", 0)
                result_text = f"✅ 成功: {success}/{total}"
            
            result_display.update(result_text)
        else:
            error_msg = result.get("error", "未知错误")
            result_display.update(f"❌ {error_msg}")
    
    async def _auto_close(self) -> None:
        """成功后自动关闭对话框"""
        await asyncio.sleep(3)  # 等待3秒
        if self.import_status == "completed":
            self.post_message(self.ImportCompleted(self.import_results))
            self.dismiss()
    
    def _cancel_import(self) -> None:
        """取消导入"""
        self.post_message(self.ImportCancelled())
        self.dismiss()
    
    # 响应式属性监听器
    def watch_import_status(self, status: str) -> None:
        """监听导入状态变化"""
        start_btn = self.query_one("#start_import_btn", Button)
        
        if status == "importing":
            start_btn.disabled = True
            start_btn.label = "⏳ 导入中..."
        elif status == "completed":
            start_btn.disabled = True
            start_btn.label = "✅ 导入完成"
        elif status == "error":
            start_btn.disabled = False
            start_btn.label = "🔄 重试导入"
        else:
            start_btn.disabled = False
            start_btn.label = "🚀 开始导入"
    
    def watch_progress_value(self, value: int) -> None:
        """监听进度变化"""
        progress_bar = self.query_one("#progress_bar", ProgressBar)
        progress_bar.progress = value
    
    def watch_status_message(self, message: str) -> None:
        """监听状态消息变化"""
        status_display = self.query_one("#status_display", Static)
        status_display.update(message)