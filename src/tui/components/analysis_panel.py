"""分析面板组件"""

from textual.widgets import Button, Static, Input, DataTable, Select, ProgressBar
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, Dict, List
from enum import Enum

from ...services.song_service_base import SongServiceBase
from ...core.parser import RelativeParser
from ...core.converter import AutoConverter
from ...data.songs.song_manager import SongManager


class AnalysisStatus(Enum):
    """分析状态枚举"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"


class AnalysisPanel(Container):
    """分析面板组件"""

    # 自定义消息类
    class AnalysisCompleted(Message):
        """分析完成消息"""
        def __init__(self, song_name: str, analysis_data: Dict) -> None:
            self.song_name = song_name
            self.analysis_data = analysis_data
            super().__init__()

    # 响应式属性
    current_song: reactive[Optional[str]] = reactive(None)
    analysis_data: reactive[Optional[Dict]] = reactive(None)
    analysis_status: reactive[AnalysisStatus] = reactive(AnalysisStatus.IDLE)

    def __init__(self, song_service: SongServiceBase):
        """初始化分析面板组件"""
        super().__init__()
        self.song_service = song_service
        self.parser = RelativeParser()
        self.converter = AutoConverter()
        self.song_manager = SongManager()

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        # 歌曲选择控制面板 - 类似Postman的请求构建区域
        with Container(id="analysis_control", classes="section") as control_container:
            control_container.border_title = "🎵 歌曲分析"
            with Horizontal(classes="song_select_row"):
                yield Static("歌曲:", classes="setting_label")
                yield Input(placeholder="输入歌曲名称或从浏览器选择", id="song_input")
                yield Button("🔍 分析", id="analyze_btn", variant="primary")
            
            # 分析状态和进度显示
            with Horizontal(classes="status_row"):
                yield Static("状态: 等待分析", id="analysis_status_display")
                yield ProgressBar(total=100, show_percentage=False, id="analysis_progress")

        # 基本信息面板 - 使用border_title替代内部标题
        with Container(id="basic_info", classes="section") as basic_container:
            basic_container.border_title = "📊 基本信息"
            with Vertical():
                with Horizontal(classes="info_row"):
                    yield Static("歌曲名称: 未选择", id="song_name_info")
                    yield Static("BPM: -", id="bpm_info")
                with Horizontal(classes="info_row"):
                    yield Static("小节数: -", id="bars_info")
                    yield Static("总时长: -", id="duration_info")

        # 音域分析面板
        with Container(id="range_analysis", classes="section") as range_container:
            range_container.border_title = "🎼 音域分析"
            with Vertical():
                with Horizontal(classes="range_row"):
                    yield Static("最低音: -", id="min_note")
                    yield Static("最高音: -", id="max_note")
                with Horizontal(classes="range_row"):
                    yield Static("音域跨度: -", id="range_span")
                    yield Static("八度跨度: -", id="octave_span")

        # 映射策略建议面板
        with Container(id="mapping_suggestions", classes="section") as mapping_container:
            mapping_container.border_title = "🎯 映射策略建议"
            yield DataTable(id="strategy_table", cursor_type="none")

        # 详细分析结果面板
        with Container(id="detailed_analysis", classes="section") as detail_container:
            detail_container.border_title = "📋 详细分析"
            yield Static("选择歌曲并点击分析按钮开始分析", id="analysis_details", classes="analysis_text")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._setup_strategy_table()

    def _setup_strategy_table(self) -> None:
        """设置策略表格"""
        table = self.query_one("#strategy_table", DataTable)
        table.add_columns("策略", "偏移(半音)", "可行性", "说明")

    def _clear_analysis(self) -> None:
        """清除分析结果"""
        # 清除基本信息
        self.query_one("#song_name_info", Static).update("歌曲名称: 未选择")
        self.query_one("#bpm_info", Static).update("BPM: -")
        self.query_one("#bars_info", Static).update("小节数: -")
        self.query_one("#duration_info", Static).update("总时长: -")

        # 清除音域信息
        self.query_one("#min_note", Static).update("最低音: -")
        self.query_one("#max_note", Static).update("最高音: -")
        self.query_one("#range_span", Static).update("音域跨度: -")
        self.query_one("#octave_span", Static).update("八度跨度: -")

        # 清除策略表格
        table = self.query_one("#strategy_table", DataTable)
        table.clear()

        # 清除详细分析
        self.query_one("#analysis_details", Static).update("选择歌曲并点击分析按钮开始分析")
        
        # 清除状态显示
        self.query_one("#analysis_status_display", Static).update("状态: 等待分析")
        self.query_one("#analysis_progress", ProgressBar).progress = 0

    def _update_analysis_display(self, song_name: str, analysis: Dict) -> None:
        """更新分析显示"""
        # 更新基本信息
        song_info = analysis.get("song_info", {})
        self.query_one("#song_name_info", Static).update(f"歌曲名称: {song_name}")
        self.query_one("#bpm_info", Static).update(f"BPM: {song_info.get('bpm', '-')}")
        self.query_one("#bars_info", Static).update(f"小节数: {song_info.get('bars', '-')}")
        
        # 计算总时长
        bpm = song_info.get('bpm', 120)
        bars = song_info.get('bars', 0)
        if bpm and bars:
            # 假设每小节四拍，计算时长
            duration_seconds = (bars * 4) * (60 / bpm)
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_text = f"{minutes:02d}:{seconds:02d}"
        else:
            duration_text = "-"
        self.query_one("#duration_info", Static).update(f"总时长: {duration_text}")

        # 更新音域信息
        range_info = analysis.get("range_info", {})
        self.query_one("#min_note", Static).update(f"最低音: {range_info.get('min', '-'):.1f}")
        self.query_one("#max_note", Static).update(f"最高音: {range_info.get('max', '-'):.1f}")
        self.query_one("#range_span", Static).update(f"音域跨度: {range_info.get('span', '-'):.1f}半音")
        self.query_one("#octave_span", Static).update(f"八度跨度: {range_info.get('octaves', '-'):.1f}八度")

        # 更新策略表格
        self._update_strategy_table(analysis.get("mapping_suggestions", {}))

        # 更新详细分析
        self._update_detailed_analysis(analysis)
        
        # 更新状态显示
        self.query_one("#analysis_status_display", Static).update("状态: 分析完成")
        self.query_one("#analysis_progress", ProgressBar).progress = 100

    def _update_strategy_table(self, suggestions: Dict) -> None:
        """更新策略表格"""
        table = self.query_one("#strategy_table", DataTable)
        table.clear()

        strategy_names = {
            "optimal": "最优映射",
            "high": "偏高音域",
            "low": "偏低音域",
            "manual": "手动偏移"
        }

        for strategy, data in suggestions.items():
            if strategy == "analysis":
                continue
            
            name = strategy_names.get(strategy, strategy)
            offset = f"{data.get('offset', 0):+.1f}"
            feasible = "✅ 可行" if data.get('feasible', True) else "❌ 不可行"
            
            # 生成说明
            description = ""
            if strategy == "optimal":
                description = "推荐的最佳映射策略"
            elif strategy == "high":
                description = "偏向高音域的映射"
            elif strategy == "low":
                description = "偏向低音域的映射"
            elif "error" in data:
                description = data["error"]
            
            table.add_row(name, offset, feasible, description)

    def _update_detailed_analysis(self, analysis: Dict) -> None:
        """更新详细分析"""
        details = []
        
        # 音域统计
        range_info = analysis.get("range_info", {})
        if range_info:
            details.append(f"音符范围: {range_info.get('min', 0):.1f} ~ {range_info.get('max', 0):.1f} 半音")
            details.append(f"覆盖 {range_info.get('octaves', 0):.1f} 个完整八度")
        
        # 映射可行性
        suggestions = analysis.get("mapping_suggestions", {})
        feasible_strategies = [name for name, data in suggestions.items() 
                             if data.get('feasible', True) and name != "analysis"]
        if feasible_strategies:
            details.append(f"可行策略: {', '.join(feasible_strategies)}")
        
        # 特殊说明
        if analysis.get("has_impossible_notes"):
            details.append("⚠️ 包含无法在游戏中演奏的音符")
        
        if analysis.get("requires_transposition"):
            details.append("建议使用音高偏移以获得最佳效果")

        detail_text = "\n".join(details) if details else "分析完成，详细信息如上所示"
        self.query_one("#analysis_details", Static).update(detail_text)

    def _analyze_song(self, song_name: str) -> None:
        """分析指定歌曲"""
        try:
            # 更新分析状态
            self.analysis_status = AnalysisStatus.ANALYZING
            self.query_one("#analysis_status_display", Static).update("状态: 正在分析...")
            self.query_one("#analysis_progress", ProgressBar).progress = 25
            
            # 获取歌曲数据
            success, song, error_msg = self.song_service.get_song_safely(song_name)
            if not success:
                self._show_error(error_msg)
                return
            
            self.query_one("#analysis_progress", ProgressBar).progress = 50

            # 解析歌曲
            parsed = self.parser.parse(song.jianpu)
            range_info = self.parser.get_range_info(parsed)
            
            self.query_one("#analysis_progress", ProgressBar).progress = 75

            # 获取映射建议
            preview = self.converter.get_conversion_preview(parsed)

            # 构建分析数据
            analysis_data = {
                "song_info": {
                    "name": song.name,
                    "bpm": song.bpm,
                    "bars": len(song.jianpu),
                    "description": song.description
                },
                "range_info": range_info,
                "mapping_suggestions": preview.get("suggestions", {}),
                "has_impossible_notes": any(
                    note.physical_height is not None and not note.key_combination
                    for bar in parsed for note in bar
                ),
                "requires_transposition": range_info.get("span", 0) > 12
            }

            self.analysis_data = analysis_data
            self.analysis_status = AnalysisStatus.COMPLETED
            self._update_analysis_display(song_name, analysis_data)
            self.post_message(self.AnalysisCompleted(song_name, analysis_data))

        except Exception as e:
            self.analysis_status = AnalysisStatus.ERROR
            self._show_error(f"分析失败: {str(e)}")

    def _show_error(self, message: str) -> None:
        """显示错误信息"""
        self.query_one("#analysis_details", Static).update(f"❌ {message}")
        self.query_one("#analysis_status_display", Static).update(f"状态: 分析失败")
        self.query_one("#analysis_progress", ProgressBar).progress = 0
        if hasattr(self.app, 'notify'):
            self.app.notify(message, severity="error")

    # 事件处理器
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "analyze_btn":
            self.analyze_current_song()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入提交（按回车）"""
        if event.input.id == "song_input":
            # 直接分析当前歌曲
            self.analyze_current_song()

    # 响应式属性监听器
    def watch_current_song(self, song_name: Optional[str]) -> None:
        """监听当前歌曲变化"""
        if song_name:
            song_input = self.query_one("#song_input", Input)
            song_input.value = song_name
    
    def watch_analysis_status(self, status: AnalysisStatus) -> None:
        """监听分析状态变化"""
        try:
            # 更新状态显示和进度条
            status_display = self.query_one("#analysis_status_display", Static)
            progress_bar = self.query_one("#analysis_progress", ProgressBar)
            
            if status == AnalysisStatus.IDLE:
                status_display.update("状态: 等待分析")
                progress_bar.progress = 0
            elif status == AnalysisStatus.ANALYZING:
                status_display.update("状态: 正在分析...")
                # 进度条在_analyze_song方法中更新
            elif status == AnalysisStatus.COMPLETED:
                status_display.update("状态: 分析完成")
                progress_bar.progress = 100
            elif status == AnalysisStatus.ERROR:
                status_display.update("状态: 分析失败")
                progress_bar.progress = 0
        except Exception:
            # 如果更新失败，忽略错误
            pass

    # 公共方法
    def set_song_for_analysis(self, song_name: str, auto_analyze: bool = True) -> None:
        """设置要分析的歌曲
        
        Args:
            song_name: 歌曲名称
            auto_analyze: 是否自动开始分析
        """
        self.current_song = song_name
        
        # 更新输入框显示
        song_input = self.query_one("#song_input", Input)
        song_input.value = song_name
        
        if auto_analyze:
            self._analyze_song(song_name)
    
    def analyze_current_song(self) -> None:
        """分析当前输入框中的歌曲"""
        song_input = self.query_one("#song_input", Input)
        song_name = song_input.value.strip()
        
        if not song_name:
            self._show_error("请输入歌曲名称")
            return
        
        self.current_song = song_name
        self._analyze_song(song_name)

    def get_analysis_results(self) -> Optional[Dict]:
        """获取分析结果"""
        return self.analysis_data
    
    def get_current_song(self) -> Optional[str]:
        """获取当前选中的歌曲名称"""
        return self.current_song