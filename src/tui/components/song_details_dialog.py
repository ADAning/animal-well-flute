"""歌曲详情对话框组件"""

from textual.widgets import Button, Static, ProgressBar, Tabs, Tab
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml

from ...data.songs.sample_songs import Song
from ...services.song_service_base import SongServiceBase
from ...core.parser import RelativeParser
from ...core.converter import AutoConverter
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongDetailsDialog(ModalScreen):
    """歌曲详情对话框"""
    
    # 自定义消息
    class PlayRequested(Message):
        """播放请求消息"""
        def __init__(self, song_name: str) -> None:
            self.song_name = song_name
            super().__init__()
    
    class AnalyzeRequested(Message):
        """分析请求消息"""  
        def __init__(self, song_name: str) -> None:
            self.song_name = song_name
            super().__init__()
    
    # 响应式属性
    song_name: reactive[Optional[str]] = reactive(None)
    song_data: reactive[Optional[Song]] = reactive(None)
    analysis_data: reactive[Optional[Dict]] = reactive(None)
    
    def __init__(self, song_service: SongServiceBase, song_name: str):
        """初始化歌曲详情对话框"""
        super().__init__()
        self.song_service = song_service
        self.song_name = song_name
        self.parser = RelativeParser()
        self.converter = AutoConverter()
    
    def compose(self) -> ComposeResult:
        """构建对话框界面"""
        with Container(id="details_dialog"):
            yield Static("🎵 歌曲详情", id="dialog_title")
            
            # 标签页内容
            with Tabs("基本信息", "简谱内容", "音域分析", id="details_tabs"):
                # 基本信息标签页
                with Tab("基本信息", id="basic_tab"):
                    with Container(id="basic_info_content", classes="tab_content"):
                        with Container(id="song_metadata", classes="info_section") as metadata_container:
                            metadata_container.border_title = "📋 歌曲信息"
                            yield Static("歌曲名称: 加载中...", id="song_name_display")
                            yield Static("BPM: 加载中...", id="bpm_display")  
                            yield Static("小节数: 加载中...", id="bars_display")
                            yield Static("总时长: 加载中...", id="duration_display")
                            yield Static("音高偏移: 加载中...", id="offset_display")
                        
                        with Container(id="song_description", classes="info_section") as desc_container:
                            desc_container.border_title = "📝 歌曲描述"
                            with ScrollableContainer(id="description_scroll"):
                                yield Static("加载中...", id="description_display")
                        
                        with Container(id="file_info", classes="info_section") as file_container:
                            file_container.border_title = "📄 文件信息"
                            yield Static("文件路径: 加载中...", id="file_path_display")
                            yield Static("文件大小: 加载中...", id="file_size_display")
                            yield Static("修改时间: 加载中...", id="modified_time_display")
                
                # 简谱内容标签页
                with Tab("简谱内容", id="jianpu_tab"):
                    with Container(id="jianpu_content", classes="tab_content"):
                        with Container(id="jianpu_display", classes="info_section") as jianpu_container:
                            jianpu_container.border_title = "🎼 简谱记号"
                            with ScrollableContainer(id="jianpu_scroll"):
                                yield Static("加载中...", id="jianpu_text")
                
                # 音域分析标签页  
                with Tab("音域分析", id="analysis_tab"):
                    with Container(id="analysis_content", classes="tab_content"):
                        with Container(id="range_info", classes="info_section") as range_container:
                            range_container.border_title = "🎹 音域信息"
                            yield Static("最低音: 分析中...", id="min_note_display")
                            yield Static("最高音: 分析中...", id="max_note_display")
                            yield Static("音域跨度: 分析中...", id="range_span_display")
                            yield Static("八度跨度: 分析中...", id="octave_span_display")
                        
                        with Container(id="mapping_info", classes="info_section") as mapping_container:
                            mapping_container.border_title = "🎯 映射建议"
                            with ScrollableContainer(id="mapping_scroll"):
                                yield Static("分析中...", id="mapping_suggestions_display")
            
            # 按钮区域
            with Container(id="dialog_buttons"):
                with Horizontal(classes="button_row"):
                    yield Button("▶️ 播放", id="play_btn", variant="primary")
                    yield Button("🔍 分析", id="analyze_btn", variant="default")
                    yield Button("❌ 关闭", id="close_btn", variant="default")
    
    def on_mount(self) -> None:
        """对话框挂载时加载数据"""
        self._load_song_data()
        self._analyze_song()
    
    def _load_song_data(self) -> None:
        """加载歌曲数据"""
        try:
            success, song, error_msg = self.song_service.get_song_safely(self.song_name)
            if not success:
                self._show_error(f"加载歌曲失败: {error_msg}")
                return
            
            self.song_data = song
            self._update_basic_info(song)
            self._update_jianpu_content(song)
            
        except Exception as e:
            logger.error(f"Failed to load song data: {e}")
            self._show_error(f"加载歌曲数据失败: {str(e)}")
    
    def _update_basic_info(self, song: Song) -> None:
        """更新基本信息显示"""
        try:
            # 更新歌曲元数据
            self.query_one("#song_name_display", Static).update(f"歌曲名称: {song.name}")
            self.query_one("#bpm_display", Static).update(f"BPM: {song.bpm}")
            self.query_one("#bars_display", Static).update(f"小节数: {len(song.jianpu)}")
            
            # 计算总时长
            duration_seconds = (len(song.jianpu) * 4) * (60 / song.bpm) if song.bpm > 0 else 0
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_text = f"{minutes:02d}:{seconds:02d}"
            self.query_one("#duration_display", Static).update(f"总时长: {duration_text}")
            
            self.query_one("#offset_display", Static).update(f"音高偏移: {song.offset:+.1f} 半音")
            
            # 更新描述
            description = song.description or "无描述信息"
            self.query_one("#description_display", Static).update(description)
            
            # 更新文件信息 (如果可获取)
            try:
                # 尝试获取文件信息
                song_manager = self.song_service.song_manager
                song_path = None
                
                # 查找对应的YAML文件
                for path in song_manager.songs_dir.glob("*.yaml"):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            if data and data.get('name') == song.name:
                                song_path = path
                                break
                    except:
                        continue
                
                if song_path and song_path.exists():
                    stat = song_path.stat()
                    file_size = stat.st_size
                    size_text = self._format_file_size(file_size)
                    modified_time = stat.st_mtime
                    import time
                    time_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(modified_time))
                    
                    self.query_one("#file_path_display", Static).update(f"文件路径: {song_path.name}")
                    self.query_one("#file_size_display", Static).update(f"文件大小: {size_text}")
                    self.query_one("#modified_time_display", Static).update(f"修改时间: {time_text}")
                else:
                    self.query_one("#file_path_display", Static).update("文件路径: 内置歌曲")
                    self.query_one("#file_size_display", Static).update("文件大小: -")
                    self.query_one("#modified_time_display", Static).update("修改时间: -")
            
            except Exception as e:
                logger.warning(f"Failed to get file info: {e}")
                self.query_one("#file_path_display", Static).update("文件路径: 获取失败")
                self.query_one("#file_size_display", Static).update("文件大小: -")
                self.query_one("#modified_time_display", Static).update("修改时间: -")
                
        except Exception as e:
            logger.error(f"Failed to update basic info: {e}")
    
    def _update_jianpu_content(self, song: Song) -> None:
        """更新简谱内容显示"""
        try:
            # 格式化简谱内容
            jianpu_lines = []
            for i, line in enumerate(song.jianpu, 1):
                jianpu_lines.append(f"第{i:2d}小节: {line}")
            
            jianpu_text = "\n".join(jianpu_lines) if jianpu_lines else "无简谱内容"
            self.query_one("#jianpu_text", Static).update(jianpu_text)
            
        except Exception as e:
            logger.error(f"Failed to update jianpu content: {e}")
            self.query_one("#jianpu_text", Static).update("简谱内容加载失败")
    
    def _analyze_song(self) -> None:
        """分析歌曲音域"""
        try:
            if not self.song_data:
                return
            
            # 解析简谱
            parsed = self.parser.parse(self.song_data.jianpu)
            range_info = self.parser.get_range_info(parsed)
            
            # 获取映射建议
            preview = self.converter.get_conversion_preview(parsed)
            
            self.analysis_data = {
                "range_info": range_info,
                "mapping_suggestions": preview.get("suggestions", {})
            }
            
            self._update_analysis_display()
            
        except Exception as e:
            logger.error(f"Failed to analyze song: {e}")
            self._show_analysis_error(str(e))
    
    def _update_analysis_display(self) -> None:
        """更新分析结果显示"""
        if not self.analysis_data:
            return
        
        try:
            range_info = self.analysis_data.get("range_info", {})
            
            # 更新音域信息
            self.query_one("#min_note_display", Static).update(f"最低音: {range_info.get('min', 0):.1f} 半音")
            self.query_one("#max_note_display", Static).update(f"最高音: {range_info.get('max', 0):.1f} 半音") 
            self.query_one("#range_span_display", Static).update(f"音域跨度: {range_info.get('span', 0):.1f} 半音")
            self.query_one("#octave_span_display", Static).update(f"八度跨度: {range_info.get('octaves', 0):.1f} 八度")
            
            # 更新映射建议
            suggestions = self.analysis_data.get("mapping_suggestions", {})
            mapping_lines = []
            
            for strategy, data in suggestions.items():
                if strategy == "analysis":
                    continue
                
                strategy_names = {
                    "optimal": "最优映射",
                    "high": "偏高音域", 
                    "low": "偏低音域",
                    "manual": "手动偏移"
                }
                
                name = strategy_names.get(strategy, strategy)
                offset = data.get('offset', 0)
                feasible = "✅ 可行" if data.get('feasible', True) else "❌ 不可行"
                
                mapping_lines.append(f"{name}: {offset:+.1f}半音 ({feasible})")
            
            mapping_text = "\n".join(mapping_lines) if mapping_lines else "无映射建议"
            self.query_one("#mapping_suggestions_display", Static).update(mapping_text)
            
        except Exception as e:
            logger.error(f"Failed to update analysis display: {e}")
            self._show_analysis_error(str(e))
    
    def _show_analysis_error(self, error_msg: str) -> None:
        """显示分析错误"""
        self.query_one("#min_note_display", Static).update("最低音: 分析失败")
        self.query_one("#max_note_display", Static).update("最高音: 分析失败")
        self.query_one("#range_span_display", Static).update("音域跨度: 分析失败")
        self.query_one("#octave_span_display", Static).update("八度跨度: 分析失败")
        self.query_one("#mapping_suggestions_display", Static).update(f"分析失败: {error_msg}")
    
    def _show_error(self, error_msg: str) -> None:
        """显示错误信息"""
        # 更新所有显示为错误状态
        self.query_one("#song_name_display", Static).update(f"错误: {error_msg}")
        self.query_one("#jianpu_text", Static).update(f"加载失败: {error_msg}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "play_btn":
            if self.song_name:
                self.post_message(self.PlayRequested(self.song_name))
                self.dismiss()
        elif button_id == "analyze_btn":
            if self.song_name:
                self.post_message(self.AnalyzeRequested(self.song_name)) 
                self.dismiss()
        elif button_id == "close_btn":
            self.dismiss()