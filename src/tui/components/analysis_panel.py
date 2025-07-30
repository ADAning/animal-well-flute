"""分析面板组件"""

from textual.widgets import Button, Static, Input, DataTable, Select
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, Dict, List

from ...services.song_service_base import SongServiceBase
from ...core.parser import RelativeParser
from ...core.converter import AutoConverter


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

    def __init__(self, song_service: SongServiceBase):
        """初始化分析面板组件"""
        super().__init__()
        self.song_service = song_service
        self.parser = RelativeParser()
        self.converter = AutoConverter()

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        with Vertical():
            # 歌曲选择和分析控制
            with Container(id="analysis_header"):
                with Horizontal(classes="song_select_row"):
                    yield Static("歌曲:", classes="label")
                    yield Input(placeholder="输入歌曲名称", id="song_input")
                    yield Button("🔍 分析", id="analyze_btn", variant="primary")

            # 基本信息显示
            with Container(id="basic_info"):
                yield Static("基本信息", classes="section_title")
                with Horizontal(classes="info_row"):
                    yield Static("歌曲名称: 未选择", id="song_name_info")
                    yield Static("BPM: -", id="bpm_info")
                    yield Static("小节数: -", id="bars_info")

            # 音域分析
            with Container(id="range_analysis"):
                yield Static("音域分析", classes="section_title")
                with Horizontal(classes="range_row"):
                    yield Static("最低音: -", id="min_note")
                    yield Static("最高音: -", id="max_note")
                    yield Static("音域跨度: -", id="range_span")
                    yield Static("八度跨度: -", id="octave_span")

            # 映射策略建议
            with Container(id="mapping_suggestions"):
                yield Static("映射策略建议", classes="section_title")
                yield DataTable(id="strategy_table", cursor_type="none")

            # 详细分析结果
            with Container(id="detailed_analysis"):
                yield Static("详细分析", classes="section_title")
                yield Static("选择歌曲并点击分析按钮开始分析", id="analysis_details")

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

    def _update_analysis_display(self, song_name: str, analysis: Dict) -> None:
        """更新分析显示"""
        # 更新基本信息
        song_info = analysis.get("song_info", {})
        self.query_one("#song_name_info", Static).update(f"歌曲名称: {song_name}")
        self.query_one("#bpm_info", Static).update(f"BPM: {song_info.get('bpm', '-')}")
        self.query_one("#bars_info", Static).update(f"小节数: {song_info.get('bars', '-')}")

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
            # 获取歌曲数据
            success, song, error_msg = self.song_service.get_song_safely(song_name)
            if not success:
                self._show_error(error_msg)
                return

            # 解析歌曲
            parsed = self.parser.parse(song.jianpu)
            range_info = self.parser.get_range_info(parsed)

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
            self._update_analysis_display(song_name, analysis_data)
            self.post_message(self.AnalysisCompleted(song_name, analysis_data))

        except Exception as e:
            self._show_error(f"分析失败: {str(e)}")

    def _show_error(self, message: str) -> None:
        """显示错误信息"""
        self.query_one("#analysis_details", Static).update(f"❌ {message}")
        if hasattr(self.app, 'notify'):
            self.app.notify(message, severity="error")

    # 事件处理器
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "analyze_btn":
            song_input = self.query_one("#song_input", Input)
            song_name = song_input.value.strip()
            
            if not song_name:
                self._show_error("请输入歌曲名称")
                return
            
            self.current_song = song_name
            self.query_one("#analysis_details", Static).update("正在分析...")
            self._analyze_song(song_name)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入提交（按回车）"""
        if event.input.id == "song_input":
            # 触发分析按钮
            analyze_btn = self.query_one("#analyze_btn", Button)
            self.post_message(Button.Pressed(analyze_btn))

    # 响应式属性监听器
    def watch_current_song(self, song_name: Optional[str]) -> None:
        """监听当前歌曲变化"""
        if song_name:
            song_input = self.query_one("#song_input", Input)
            song_input.value = song_name

    # 公共方法
    def set_song_for_analysis(self, song_name: str) -> None:
        """设置要分析的歌曲"""
        self.current_song = song_name
        self._analyze_song(song_name)

    def get_analysis_results(self) -> Optional[Dict]:
        """获取分析结果"""
        return self.analysis_data