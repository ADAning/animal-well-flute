"""歌曲浏览器组件"""

from textual.widgets import DataTable, Input, Button, Static, Label, Rule
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from typing import Optional, List, Tuple
from dataclasses import dataclass
from rich.text import Text

from ...services.song_service_base import SongServiceBase
from ...data.songs.song_manager import SongManager
from .search_highlighter import highlight_search_matches, create_highlighted_song_display
from .song_details_dialog import SongDetailsDialog
from ..widgets import CenterMiddle


@dataclass
class SongInfo:
    """歌曲信息数据类"""
    key: str
    name: str
    bpm: int
    bars: int
    description: str


class SongBrowser(Container):
    """歌曲浏览器组件"""

    # 组件级别的键盘绑定
    BINDINGS = [
        Binding("enter", "play_selected", "播放", priority=True),
        Binding("space", "analyze_selected", "分析", priority=True),
        Binding("i", "show_details", "详情", priority=True),
    ]

    # 自定义消息类
    class SongSelected(Message):
        """歌曲选择消息"""
        def __init__(self, song_name: str, song_key: str) -> None:
            self.song_name = song_name
            self.song_key = song_key
            super().__init__()

    class PlayRequested(Message):
        """播放请求消息"""
        def __init__(self, song_name: str, song_key: str) -> None:
            self.song_name = song_name
            self.song_key = song_key
            super().__init__()

    class AnalyzeRequested(Message):
        """分析请求消息"""
        def __init__(self, song_name: str, song_key: str) -> None:
            self.song_name = song_name
            self.song_key = song_key
            super().__init__()

    # 响应式属性
    search_query: reactive[str] = reactive("")
    selected_song: reactive[Optional[str]] = reactive(None)
    songs_loaded: reactive[bool] = reactive(False)

    def __init__(self, song_service: SongServiceBase):
        """初始化歌曲浏览器"""
        super().__init__()
        self.song_service = song_service
        self.song_manager = SongManager()
        self.all_songs: List[SongInfo] = []
        self.filtered_songs: List[SongInfo] = []

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        with Vertical():
            # 合并的浏览器区域 - 包含搜索和表格，用分割线分开
            with Container(id="unified_browser_area"):
                # 搜索区域
                with Container(id="browser_header"):
                    with Horizontal(classes="search_row"):
                        yield Static("🔍 搜索:", classes="search_label")
                        yield Input(placeholder="输入歌曲名称或关键词...", id="search_input")
                        yield Button("🔄 刷新", id="refresh_btn", variant="default")
                
                # 分割线 - 类似Postman界面的效果
                yield Rule(id="browser_separator")
                
                # 歌曲表格容器
                with Container(id="songs_container"):
                    # 空状态消息
                    yield CenterMiddle(Label("🎵 暂无歌曲\n\n请检查 songs/ 目录或点击刷新按钮重新加载"), id="empty-message")
                    # 歌曲表格
                    yield DataTable(id="songs_table", cursor_type="row")
            
            # 状态栏
            yield Static("加载中...", id="status_bar")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._setup_table()
        self._load_songs()

    def _setup_table(self) -> None:
        """设置数据表格"""
        table = self.query_one("#songs_table", DataTable)
        try:
            # 确保表格是空的
            table.clear()
            # 添加列
            table.add_columns("歌曲名称", "BPM", "小节数", "描述")
            table.cursor_type = "row"
            table.zebra_stripes = True
        except Exception as e:
            # 如果设置失败，记录但不崩溃
            if hasattr(self.app, 'notify'):
                self.app.notify(f"表格设置失败: {str(e)}", severity="warning")

    def _load_songs(self) -> None:
        """加载歌曲数据"""
        try:
            self.all_songs = []
            
            # 使用歌曲管理器获取歌曲信息
            songs_info = self.song_manager.list_songs_with_info()
            
            # 用于检测重复的key
            seen_keys = set()
            duplicate_keys = []
            
            for song_info in songs_info:
                try:
                    song = SongInfo(
                        key=song_info["key"],
                        name=song_info["name"],
                        bpm=int(song_info["bpm"]),
                        bars=int(song_info["bars"]),
                        description=song_info["description"] or ""
                    )
                    
                    # 检测重复key
                    if song.key in seen_keys:
                        duplicate_keys.append(song.key)
                    seen_keys.add(song.key)
                    
                    self.all_songs.append(song)
                except (ValueError, KeyError) as e:
                    # 跳过无效的歌曲信息
                    if hasattr(self.app, 'notify'):
                        self.app.notify(f"跳过无效歌曲: {song_info.get('name', 'unknown')} - {str(e)}", severity="warning")
                    continue
            
            # 如果有重复key，在状态中警告
            if duplicate_keys:
                if hasattr(self.app, 'notify'):
                    self.app.notify(f"检测到重复歌曲key: {', '.join(set(duplicate_keys))}", severity="warning")
            
            self.filtered_songs = self.all_songs.copy()
            self._update_table()
            self._update_empty_state()
            self.songs_loaded = True
            
            if len(self.all_songs) > 0:
                status_msg = f"✅ 已加载 {len(self.all_songs)} 首歌曲"
                if duplicate_keys:
                    status_msg += f" (包含 {len(set(duplicate_keys))} 个重复key)"
                status_msg += " - 选择歌曲后按Enter播放或点击按钮操作"
                self._update_status(status_msg)
            else:
                self._update_status("🔍 未找到歌曲文件 - 请检查 songs/ 目录")
            
        except Exception as e:
            error_msg = f"加载歌曲失败: {str(e)}"
            self._update_status(error_msg)
            if hasattr(self.app, 'notify'):
                self.app.notify(error_msg, severity="error")
            self._update_empty_state()

    def _update_table(self) -> None:
        """更新表格数据"""
        table = self.query_one("#songs_table", DataTable)
        
        # 更彻底的清理表格
        try:
            table.clear(columns=False)  # 只清理行，保留列
        except Exception:
            # 如果清理失败，尝试完全重建表格
            try:
                table.clear()
                table.add_columns("歌曲名称", "BPM", "小节数", "描述")
            except Exception:
                pass
        
        # 获取当前搜索查询
        current_query = self.search_query.strip() if self.search_query else ""
        
        # 用于跟踪已使用的key，避免重复
        used_keys = set()
        
        for i, song in enumerate(self.filtered_songs):
            # 限制描述长度
            description = song.description[:50] + "..." if len(song.description) > 50 else song.description
            description = description or "无描述"
            
            # 确保row key唯一，如果原key重复则添加索引
            row_key = song.key
            if row_key in used_keys:
                row_key = f"{song.key}_{i}"
            used_keys.add(row_key)
            
            try:
                # 创建带高亮的文本
                if current_query:
                    highlighted_name = highlight_search_matches(song.name, current_query)
                    highlighted_desc = highlight_search_matches(description, current_query)
                    highlighted_bpm = highlight_search_matches(str(song.bpm), current_query)
                    
                    table.add_row(
                        highlighted_name,
                        highlighted_bpm,
                        str(song.bars),
                        highlighted_desc,
                        key=row_key
                    )
                else:
                    # 没有搜索查询时使用普通文本
                    table.add_row(
                        song.name,
                        str(song.bpm),
                        str(song.bars),
                        description,
                        key=row_key
                    )
            except Exception as e:
                # 如果添加行失败，记录错误但继续处理其他歌曲
                error_msg = f"添加行失败 [{song.name}]: {str(e)}"
                self._update_status(error_msg)
                # 可选：使用简单的索引作为key再试一次
                try:
                    fallback_key = f"song_{i}"
                    if current_query:
                        table.add_row(
                            highlighted_name,
                            highlighted_bpm,
                            str(song.bars),
                            highlighted_desc,
                            key=fallback_key
                        )
                    else:
                        table.add_row(
                            song.name,
                            str(song.bpm),
                            str(song.bars),
                            description,
                            key=fallback_key
                        )
                except Exception as e2:
                    # 如果依然失败，跳过这个歌曲
                    continue

    def _update_status(self, message: str) -> None:
        """更新状态栏"""
        status_bar = self.query_one("#status_bar", Static)
        status_bar.update(message)

    def _update_empty_state(self) -> None:
        """更新空状态显示"""
        container = self.query_one("#songs_container", Container)
        has_songs = len(self.filtered_songs) > 0
        
        # 设置empty类来控制显示/隐藏
        container.set_class(not has_songs, "empty")
        
        # 如果是搜索结果为空，更新消息文本
        if not has_songs and self.search_query.strip():
            empty_message = self.query_one("#empty-message Label", Label)
            empty_message.update(f"🔍 未找到匹配的歌曲\n\n搜索: '{self.search_query}'\n请尝试其他关键词或点击刷新按钮")
        elif not has_songs:
            empty_message = self.query_one("#empty-message Label", Label)
            empty_message.update("🎵 暂无歌曲\n\n请检查 songs/ 目录或点击刷新按钮重新加载")

    def _filter_songs(self, query: str) -> None:
        """根据搜索查询过滤歌曲"""
        # 更新搜索查询状态
        self.search_query = query
        
        if not query.strip():
            self.filtered_songs = self.all_songs.copy()
        else:
            query_lower = query.lower()
            self.filtered_songs = [
                song for song in self.all_songs
                if (query_lower in song.name.lower() or 
                    query_lower in song.description.lower() or
                    query_lower in song.key.lower() or
                    query_lower == str(song.bpm))
            ]
        
        self._update_table()
        self._update_empty_state()
        count_text = f"找到 {len(self.filtered_songs)} 首歌曲"
        if query.strip():
            count_text += f" (搜索: '{query}')"
        self._update_status(count_text)

    def _get_selected_song(self) -> Optional[Tuple[str, str]]:
        """获取当前选中的歌曲"""
        table = self.query_one("#songs_table", DataTable)
        if table.cursor_row >= 0 and table.cursor_row < len(self.filtered_songs):
            song = self.filtered_songs[table.cursor_row]
            return song.name, song.key
        return None

    # 事件处理器
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理搜索输入变化"""
        if event.input.id == "search_input":
            self.search_query = event.value
            self._filter_songs(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "refresh_btn":
            self._update_status("正在刷新...")
            self._load_songs()

    # 快捷键动作方法
    def action_play_selected(self) -> None:
        """播放选中的歌曲 (Enter键)"""
        selected = self._get_selected_song()
        if selected:
            song_name, song_key = selected
            self.post_message(self.PlayRequested(song_name, song_key))
            self._update_status(f"正在播放: {song_name}")
        else:
            self._update_status("⚠️  请先在列表中选择一首歌曲")

    def action_analyze_selected(self) -> None:
        """分析选中的歌曲 (空格键)"""
        selected = self._get_selected_song()
        if selected:
            song_name, song_key = selected
            self.post_message(self.AnalyzeRequested(song_name, song_key))
            self._update_status(f"正在分析: {song_name}")
        else:
            self._update_status("⚠️  请先在列表中选择一首歌曲")

    def action_show_details(self) -> None:
        """显示选中歌曲的详情 (I键)"""
        selected = self._get_selected_song()
        if selected:
            song_name, song_key = selected
            self._show_song_details(song_name, song_key)
            self._update_status(f"查看详情: {song_name}")
        else:
            self._update_status("⚠️  请先在列表中选择一首歌曲")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择"""
        if event.row_key and len(self.filtered_songs) > event.cursor_row >= 0:
            song = self.filtered_songs[event.cursor_row]
            self.selected_song = song.name
            self.post_message(self.SongSelected(song.name, song.key))
            self._update_status(f"已选择: {song.name} - 按Enter播放，空格分析，或点击操作按钮")
    

    def _show_song_details(self, song_name: str, song_key: str) -> None:
        """显示歌曲详情"""
        try:
            # 打开歌曲详情对话框
            details_dialog = SongDetailsDialog(self.song_service, song_name)
            self.app.push_screen(details_dialog)
                
        except Exception as e:
            self._update_status(f"打开详情失败: {str(e)}")

    # 响应式属性监听器
    def watch_search_query(self, query: str) -> None:
        """监听搜索查询变化"""
        self._filter_songs(query)

    def watch_selected_song(self, song_name: Optional[str]) -> None:
        """监听选中歌曲变化"""
        if song_name:
            self._update_status(f"当前选择: {song_name}")

    # 公共方法
    def refresh_songs(self) -> None:
        """刷新歌曲列表"""
        self._load_songs()

    def select_song_by_name(self, song_name: str) -> bool:
        """根据名称选择歌曲"""
        for i, song in enumerate(self.filtered_songs):
            if song.name == song_name:
                table = self.query_one("#songs_table", DataTable)
                table.cursor_row = i
                self.selected_song = song_name
                return True
        return False

    def get_selected_song_info(self) -> Optional[SongInfo]:
        """获取当前选中歌曲的完整信息"""
        if self.selected_song:
            for song in self.filtered_songs:
                if song.name == self.selected_song:
                    return song
        return None