"""歌曲浏览器组件"""

from textual.widgets import DataTable, Input, Button, Static
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, List, Tuple
from dataclasses import dataclass

from ...services.song_service_base import SongServiceBase
from ...data.songs.song_manager import SongManager


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
            # 搜索和控制区域
            with Container(id="browser_header"):
                with Horizontal(classes="search_row"):
                    yield Static("🔍 搜索:", classes="search_label")
                    yield Input(placeholder="输入歌曲名称或关键词...", id="search_input")
                    yield Button("🔄 刷新", id="refresh_btn", variant="default")
                
                with Horizontal(classes="action_row"):
                    yield Button("🎵 播放", id="play_selected_btn", variant="primary")
                    yield Button("🎼 分析", id="analyze_selected_btn", variant="default")
                    yield Button("📋 详情", id="details_btn", variant="default")

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
        table.add_columns("歌曲名称", "BPM", "小节数", "描述")
        table.cursor_type = "row"
        table.zebra_stripes = True

    def _load_songs(self) -> None:
        """加载歌曲数据"""
        try:
            self.all_songs = []
            
            # 使用歌曲管理器获取歌曲信息
            songs_info = self.song_manager.list_songs_with_info()
            
            for song_info in songs_info:
                song = SongInfo(
                    key=song_info["key"],
                    name=song_info["name"],
                    bpm=int(song_info["bpm"]),
                    bars=int(song_info["bars"]),
                    description=song_info["description"] or ""
                )
                self.all_songs.append(song)
            
            self.filtered_songs = self.all_songs.copy()
            self._update_table()
            self.songs_loaded = True
            self._update_status(f"✅ 已加载 {len(self.all_songs)} 首歌曲 - 选择歌曲后按Enter播放或点击按钮操作")
            
        except Exception as e:
            self._update_status(f"加载歌曲失败: {str(e)}")

    def _update_table(self) -> None:
        """更新表格数据"""
        table = self.query_one("#songs_table", DataTable)
        table.clear()
        
        for song in self.filtered_songs:
            # 限制描述长度
            description = song.description[:30] + "..." if len(song.description) > 30 else song.description
            table.add_row(
                song.name,
                str(song.bpm),
                str(song.bars),
                description or "无描述",
                key=song.key
            )

    def _update_status(self, message: str) -> None:
        """更新状态栏"""
        status_bar = self.query_one("#status_bar", Static)
        status_bar.update(message)

    def _filter_songs(self, query: str) -> None:
        """根据搜索查询过滤歌曲"""
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
        
        elif button_id == "play_selected_btn":
            selected = self._get_selected_song()
            if selected:
                song_name, song_key = selected
                self.post_message(self.PlayRequested(song_name, song_key))
                self._update_status(f"正在播放: {song_name}")
            else:
                self._update_status("⚠️  请先在列表中选择一首歌曲")
        
        elif button_id == "analyze_selected_btn":
            selected = self._get_selected_song()
            if selected:
                song_name, song_key = selected
                self.post_message(self.AnalyzeRequested(song_name, song_key))
                self._update_status(f"正在分析: {song_name}")
            else:
                self._update_status("⚠️  请先在列表中选择一首歌曲")
        
        elif button_id == "details_btn":
            selected = self._get_selected_song()
            if selected:
                song_name, song_key = selected
                self._show_song_details(song_name, song_key)
                self._update_status(f"查看详情: {song_name}")
            else:
                self._update_status("⚠️  请先在列表中选择一首歌曲")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择"""
        if event.row_key and len(self.filtered_songs) > event.cursor_row:
            song = self.filtered_songs[event.cursor_row]
            self.selected_song = song.name
            self.post_message(self.SongSelected(song.name, song.key))
            self._update_status(f"已选择: {song.name} - 按Enter播放，空格分析，或点击操作按钮")
    
    def on_key(self, event) -> None:
        """处理键盘事件"""
        if event.key == "enter":
            # 按Enter键播放选中的歌曲
            selected = self._get_selected_song()
            if selected:
                song_name, song_key = selected
                self.post_message(self.PlayRequested(song_name, song_key))
                self._update_status(f"正在播放: {song_name}")
            else:
                self._update_status("请先选择一首歌曲")
        elif event.key == "space":
            # 按空格键分析选中的歌曲
            selected = self._get_selected_song()
            if selected:
                song_name, song_key = selected
                self.post_message(self.AnalyzeRequested(song_name, song_key))
                self._update_status(f"正在分析: {song_name}")
            else:
                self._update_status("请先选择一首歌曲")

    def _show_song_details(self, song_name: str, song_key: str) -> None:
        """显示歌曲详情"""
        try:
            song = self.song_manager.get_song(song_key)
            details = f"""
歌曲详情:
名称: {song.name}
BPM: {song.bpm}
小节数: {len(song.jianpu)}
描述: {song.description or '无'}
偏移: {song.offset:+.1f} 半音
            """.strip()
            
            # 使用应用程序的通知系统显示详情
            app = self.app
            if hasattr(app, 'notify'):
                app.notify(details, title=f"歌曲详情 - {song_name}", timeout=8)
            else:
                self._update_status(f"详情: {song_name}")
                
        except Exception as e:
            self._update_status(f"获取详情失败: {str(e)}")

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