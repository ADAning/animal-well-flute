"""播放控制组件"""

from textual.widgets import Button, Static, ProgressBar, Input, Select
from textual.widgets.option_list import Option
from textual.containers import Container, Horizontal
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, List
from enum import Enum
import asyncio

from ...services.song_service_base import SongServiceBase
from ...core.parser import RelativeParser
from ...core.converter import AutoConverter
from ...core.flute import AutoFlute
from ...utils.logger import get_logger

logger = get_logger(__name__)


class PlayStatus(Enum):
    """播放状态枚举"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


class PlayControl(Container):
    """播放控制面板组件"""

    # 自定义消息类
    class PlayStarted(Message):
        """播放开始消息"""
        def __init__(self, song_name: str) -> None:
            self.song_name = song_name
            super().__init__()

    class PlayStopped(Message):
        """播放停止消息"""
        def __init__(self, song_name: str) -> None:
            self.song_name = song_name
            super().__init__()

    class PlayPaused(Message):
        """播放暂停消息"""
        def __init__(self, song_name: str) -> None:
            self.song_name = song_name
            super().__init__()

    # 响应式属性
    current_song: reactive[Optional[str]] = reactive(None)
    play_status: reactive[PlayStatus] = reactive(PlayStatus.STOPPED)
    progress: reactive[float] = reactive(0.0)
    current_bpm: reactive[int] = reactive(120)
    ready_time: reactive[int] = reactive(3)
    
    # 实时播放信息
    current_bar: reactive[int] = reactive(0)
    total_bars: reactive[int] = reactive(0)
    current_note: reactive[str] = reactive("—")
    current_key: reactive[str] = reactive("—")
    elapsed_time: reactive[str] = reactive("00:00")
    remaining_time: reactive[str] = reactive("00:00")

    def __init__(self, song_service: SongServiceBase):
        """初始化播放控制组件"""
        super().__init__()
        self.song_service = song_service
        self.parser = RelativeParser()
        self.converter = AutoConverter()
        self.flute = AutoFlute(progress_callback=self._on_playback_progress, tui_mode=True)
        self.play_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None  # 监控任务引用
        self._user_stopped = False  # 标记是否为用户主动停止

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        # 合并的音乐播放器面板
        with Container(id="music_player", classes="section") as player_container:
            player_container.border_title = "🎵 音乐播放器"
            
            # 主要播放器区域 - 水平三分割布局 (1:3:1)
            with Horizontal(classes="player_main_row"):
                # 左区域 (1份)：歌曲信息区域
                with Container(classes="song_info_section"):
                    yield Static("🎵", id="album_icon", classes="album_icon")
                    yield Static("未选择", id="song_name_display", classes="song_name")
                    yield Static("—", id="song_bpm_display", classes="song_meta")
                
                # 中区域 (3份)：播放控制按钮和进度条
                with Container(classes="player_controls_section"):
                    with Horizontal(classes="control_buttons_row"):
                        yield Button("►", id="play_btn", variant="primary", classes="main_play_btn")
                        yield Button("◼", id="stop_btn", classes="player_btn")
                        yield Button("↻", id="replay_btn", classes="player_btn")
                    # 进度条在按钮正下方，仅在中间区域
                    yield ProgressBar(total=100, show_percentage=False, id="play_progress", classes="player_progress")
                
                # 右区域 (1份)：实时播放信息
                with Container(classes="playback_info_section"):
                    with Horizontal(classes="time_status_row"):
                        yield Static("00:00", id="elapsed_display", classes="time_text")
                        yield Static("停止", id="status_display", classes="status_text")
                    with Horizontal(classes="progress_detail_row"):
                        yield Static("0/0", id="bar_progress", classes="progress_text")
                        yield Static("—", id="current_note_display", classes="note_text")
                    with Horizontal(classes="key_detail_row"):
                        yield Static("—", id="current_key_display", classes="key_text")

        # 播放参数设置
        with Container(id="unified_settings", classes="section") as settings_container:
            settings_container.border_title = "🎵 播放参数"
            with Horizontal(classes="unified_settings_row"):
                # BPM设置
                yield Static("BPM:", classes="setting_label")
                yield Input(
                    value=str(self.current_bpm),
                    placeholder="BPM",
                    id="bpm_input",
                    classes="number_input"
                )
                # 准备时间设置
                yield Static("准备时间:", classes="setting_label")
                yield Input(
                    value=str(self.ready_time),
                    placeholder="3",
                    id="ready_time_input",
                    classes="number_input"
                )
                # 策略设置
                yield Static("策略:", classes="setting_label")
                yield Select(
                    [
                        ("optimal", "最优映射"),
                        ("high", "偏高音域"), 
                        ("low", "偏低音域"),
                        ("auto", "自动选择"),
                        ("manual", "手动偏移"),
                        ("none", "无偏移")
                    ],
                    id="strategy_select",
                    classes="strategy_select"
                )
            # 手动偏移输入单独一行
            with Horizontal(classes="manual_offset_row"):
                yield Input(
                    placeholder="手动偏移值 (半音)",
                    id="manual_offset_input",
                    classes="number_input manual_offset"
                )

        # # 歌曲信息显示
        # with Container(id="song_analysis"):
        #     yield Static("音域信息: 未分析", id="range_info")
        #     yield Static("映射建议: 未分析", id="mapping_info")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        # 延迟初始化，确保所有组件完全加载
        self.call_later(self._initialize_components)

    def _initialize_components(self) -> None:
        """初始化所有组件"""
        # 首先设置默认策略值
        self._set_default_strategy()
        # 然后更新控制按钮状态
        self._update_controls_state()
        # 最后处理手动偏移输入的显示
        self._hide_manual_offset()
        # 初始化状态指示器
        self._update_status_indicator(self.play_status, "停止")

    def _get_safe_strategy_value(self) -> str:
        """安全获取策略值，处理NoSelection情况"""
        try:
            strategy_select = self.query_one("#strategy_select", Select)
            from textual.widgets import Select
            
            if (strategy_select.value is not None and 
                strategy_select.value != Select.BLANK and
                hasattr(strategy_select.value, '__str__') and
                str(strategy_select.value) != "Select.BLANK"):
                return str(strategy_select.value)
            else:
                return "optimal"
        except Exception:
            return "optimal"

    def _set_default_strategy(self) -> None:
        """设置默认策略值"""
        try:
            strategy_select = self.query_one("#strategy_select", Select)
            strategy_select.value = "optimal"
        except Exception:
            pass  # 如果设置失败，忽略错误

    def _update_controls_state(self) -> None:
        """更新控制按钮状态"""
        try:
            play_btn = self.query_one("#play_btn", Button)
            stop_btn = self.query_one("#stop_btn", Button)
            replay_btn = self.query_one("#replay_btn", Button)

            if self.play_status == PlayStatus.STOPPED:
                # 根据是否有歌曲来启用/禁用按钮
                has_song = bool(self.current_song)
                play_btn.disabled = not has_song
                stop_btn.disabled = True
                replay_btn.disabled = not has_song

            elif self.play_status == PlayStatus.PLAYING:
                play_btn.disabled = True
                stop_btn.disabled = False
                replay_btn.disabled = False

            elif self.play_status == PlayStatus.LOADING:
                play_btn.disabled = True
                stop_btn.disabled = True
                replay_btn.disabled = True
                
        except Exception as e:
            logger.error(f"更新按钮状态失败: {e}")
            return

    def _hide_manual_offset(self) -> None:
        """隐藏/显示手动偏移输入"""
        try:
            strategy_select = self.query_one("#strategy_select", Select)
            manual_input = self.query_one("#manual_offset_input", Input)
            
            # 安全获取策略值
            strategy = self._get_safe_strategy_value()
            
            if strategy == "manual":
                manual_input.display = True
            else:
                manual_input.display = False
        except Exception:
            # 如果组件还未初始化完成，默认隐藏手动偏移输入
            try:
                manual_input = self.query_one("#manual_offset_input", Input)
                manual_input.display = False
            except Exception:
                pass

    def _update_song_info(self) -> None:
        """更新歌曲信息显示"""
        try:
            # 更新歌曲名称显示
            song_name_display = self.query_one("#song_name_display", Static)
            song_bpm_display = self.query_one("#song_bpm_display", Static)
            
            if self.current_song:
                # 显示歌曲名称，如果太长则截断
                display_name = self.current_song
                if len(display_name) > 12:
                    display_name = display_name[:10] + "..."
                song_name_display.update(display_name)
                
                # 获取并显示歌曲的BPM和小节信息
                success, song, _ = self.song_service.get_song_safely(self.current_song)
                if success and song:
                    effective_bpm = self.song_service.get_effective_bpm(song, None)
                    # 分析歌曲获取小节数
                    try:
                        parsed = self.parser.parse(song.jianpu)
                        bar_count = len(parsed)
                        song_bpm_display.update(f"{effective_bpm}BPM/{bar_count}小节")
                    except Exception:
                        song_bpm_display.update(f"{effective_bpm}BPM")
                else:
                    song_bpm_display.update("—")
                    
                self._analyze_current_song()
            else:
                song_name_display.update("未选择")
                song_bpm_display.update("—")
                self._clear_analysis()
        except Exception as e:
            # 如果界面更新失败，通过应用通知用户
            if hasattr(self.app, 'notify'):
                self.app.notify(f"界面更新失败: {str(e)}", severity="error")

    def _analyze_current_song(self) -> None:
        """分析当前歌曲"""
        if not self.current_song:
            return

        try:
            # 获取歌曲数据
            success, song, error_msg = self.song_service.get_song_safely(self.current_song)
            if not success:
                self._update_analysis_info("分析失败", error_msg)
                return

            # 解析歌曲
            parsed = self.parser.parse(song.jianpu)
            range_info = self.parser.get_range_info(parsed)

            # 计算总小节数
            self.total_bars = len(parsed)

            # 获取映射建议
            preview = self.converter.get_conversion_preview(parsed)

            # 获取有效BPM
            effective_bpm = self.song_service.get_effective_bpm(song, None)

            # 更新显示，包含BPM信息
            range_text = f"音域: {range_info['min']:.1f}~{range_info['max']:.1f}半音 (跨度{range_info['span']:.1f}) | BPM: {effective_bpm}"
            
            suggestions = preview.get("suggestions", {})
            mapping_text = "映射建议: "
            if "optimal" in suggestions:
                opt = suggestions["optimal"]
                mapping_text += f"最优偏移{opt['offset']:+.1f}半音"

            self._update_analysis_info(range_text, mapping_text)

        except Exception as e:
            self._update_analysis_info("分析失败", str(e))

    def _update_analysis_info(self, range_text: str, mapping_text: str) -> None:
        """更新分析信息显示"""
        # 注意：分析信息显示组件已被移除，此方法暂时为空实现
        # 可以在这里添加日志记录或其他处理逻辑
        pass

    def _clear_analysis(self) -> None:
        """清除分析信息"""
        # 注意：分析信息显示组件已被移除，此方法暂时为空实现
        pass

    async def _start_play(self) -> None:
        """开始播放"""
        if not self.current_song:
            return

        # 如果已有播放任务在运行，先停止它并等待完全结束
        if self.play_task and not self.play_task.done():
            # 标记这是由新播放任务引起的取消，不是用户主动停止
            self._user_stopped = False
            self.play_task.cancel()
            self.flute.stop_requested = True
            
            # 等待旧任务完全结束，避免时序竞争
            try:
                await self.play_task
            except asyncio.CancelledError:
                pass  # 预期的取消异常，忽略
            except Exception:
                pass  # 忽略其他异常
            
            # 确保任务引用已清理
            self.play_task = None

        try:
            self.play_status = PlayStatus.LOADING
            
            # 重置停止请求标志和用户停止标志（开始新播放）
            self.flute.stop_requested = False
            self._user_stopped = False
            
            # 重置实时信息
            self._reset_realtime_info()
            
            # 获取歌曲数据以获取正确的BPM
            success, song, error_msg = self.song_service.get_song_safely(self.current_song)
            if not success:
                if hasattr(self.app, 'notify'):
                    self.app.notify(f"获取歌曲失败: {error_msg}", severity="error")
                return
            
            # 使用与CLI相同的BPM获取逻辑 - 如果用户修改过BPM，则使用用户值，否则使用歌曲BPM
            user_modified_bpm = getattr(self, '_user_modified_bpm', False)
            user_bpm = self.current_bpm if user_modified_bpm else None
            bpm = self.song_service.get_effective_bpm(song, user_bpm)
            
            ready_time = self.ready_time
            
            # 安全获取策略值
            strategy = self._get_safe_strategy_value()
            
            # 构建策略参数
            strategy_args = [strategy]
            if strategy == "manual":
                manual_input = self.query_one("#manual_offset_input", Input)
                if manual_input.value:
                    try:
                        offset = float(manual_input.value)
                        strategy_args.append(str(offset))
                    except ValueError:
                        strategy_args.append("0")

            # 调用播放功能
            self.play_status = PlayStatus.PLAYING
            self.post_message(self.PlayStarted(self.current_song))
            
            # 创建播放任务并保存引用
            self.play_task = asyncio.create_task(self._real_play(bpm, ready_time))
            
            # 等待播放完成
            success = await self.play_task
            
            if success:
                # 播放自然完成 - 只重置进度信息，不强制重置状态
                self.play_status = PlayStatus.STOPPED
                self._reset_realtime_info()
                # 延迟一下再发送停止消息，让用户看到播放完成
                self.call_later(lambda: self.post_message(self.PlayStopped(self.current_song)))
            else:
                self.play_status = PlayStatus.ERROR
                self._reset_realtime_info()

        except asyncio.CancelledError:
            # 任务被取消（暂停/停止）
            self.flute.stop_requested = True
            
            # 只有用户主动停止时才使用强制重置
            if self._user_stopped:
                self._unified_atomic_reset()
                if self.current_song:
                    self.post_message(self.PlayStopped(self.current_song))
            else:
                # 非用户停止的取消（如新播放任务覆盖），只做轻量重置
                self.play_status = PlayStatus.STOPPED
                self._reset_realtime_info()
        except Exception as e:
            self.play_status = PlayStatus.ERROR
            self._reset_realtime_info()
            if hasattr(self.app, 'notify'):
                self.app.notify(f"播放失败: {str(e)}", severity="error")
        finally:
            self.play_task = None

    async def _real_play(self, bpm: int, ready_time: int) -> bool:
        """真实的播放过程"""
        if not self.current_song:
            return False

        try:
            # 获取歌曲数据
            success, song, error_msg = self.song_service.get_song_safely(self.current_song)
            if not success:
                if hasattr(self.app, 'notify'):
                    self.app.notify(f"获取歌曲失败: {error_msg}", severity="error")
                return False

            # 获取播放设置
            settings = self.get_play_settings()
            
            # 解析歌曲
            parsed = self.parser.parse(song.jianpu)
            
            # 转换音符
            strategy = settings.get("strategy", "optimal")
            if strategy == "manual":
                manual_offset = settings.get("manual_offset", 0.0)
                converted = self.converter.convert_jianpu(
                    parsed, strategy="manual", manual_offset=manual_offset
                )
            elif strategy == "auto":
                auto_preference = settings.get("auto_preference", "optimal")
                converted = self.converter.convert_jianpu(
                    parsed, strategy="auto", auto_preference=auto_preference
                )
            else:
                converted = self.converter.convert_jianpu(parsed, strategy=strategy)

            # 检查无效音符
            invalid_count = sum(
                1 for bar in converted for note in bar
                if note.physical_height is not None and not note.key_combination
            )
            
            if invalid_count > 0:
                if hasattr(self.app, 'notify'):
                    self.app.notify(f"警告: 发现 {invalid_count} 个无法演奏的音符", severity="warning")

            # 准备阶段
            for i in range(ready_time, 0, -1):
                if self.play_status != PlayStatus.PLAYING:
                    return False
                
                try:
                    status_display = self.query_one("#status_display", Static)
                    status_display.update(f"准备中... {i}")
                except Exception:
                    pass
                await asyncio.sleep(1)

            # 开始真实播放
            try:
                status_display = self.query_one("#status_display", Static)
                status_display.update("播放中...")
            except Exception:
                pass
            
            # 计算节拍间隔
            beat_interval = 60.0 / bpm
            
            # 使用与CLI版本完全相同的播放架构
            # 在异步环境中调用同步的 play_song 方法
            loop = asyncio.get_event_loop()
            
            # 直接使用 flute.play_song() 方法，与CLI版本保持完全一致
            def play_with_cli_method():
                """使用与CLI相同的播放方法"""
                try:
                    # 直接调用 flute.play_song()，这与CLI版本完全一致
                    self.flute.play_song(converted, beat_interval)
                    return not self.flute.stop_requested
                except Exception as e:
                    # TUI模式下不打印到控制台，静默处理错误
                    return False
            
            # 如果需要进度更新，可以创建一个监控任务
            async def monitor_progress():
                """监控播放进度和实时信息"""
                total_notes = sum(len(bar) for bar in converted)
                if total_notes == 0:
                    return
                
                # 估算总播放时间
                total_time = 0
                for bar in converted:
                    for note in bar:
                        total_time += note.time_factor * beat_interval
                
                start_time = asyncio.get_event_loop().time()
                current_bar_index = 0
                current_note_index = 0
                
                while not success_future.done():
                    await asyncio.sleep(0.1)
                    
                    # 增强的停止状态检查 - 立即中断监控循环
                    if self.play_status == PlayStatus.STOPPED or self.flute.stop_requested:
                        break
                        
                    elapsed = asyncio.get_event_loop().time() - start_time
                    progress = min(100, (elapsed / total_time) * 100) if total_time > 0 else 0
                    
                    # 估算当前小节和音符
                    estimated_bar = min(int((elapsed / total_time) * len(converted)), len(converted) - 1) if total_time > 0 else 0
                    
                    # 获取当前音符信息
                    current_note_text = "—"
                    current_key_text = "—"
                    if estimated_bar < len(converted) and len(converted[estimated_bar]) > 0:
                        # 简单估算当前音符
                        bar_notes = converted[estimated_bar]
                        note_in_bar = min(len(bar_notes) - 1, int((elapsed % (total_time / len(converted))) / beat_interval)) if beat_interval > 0 else 0
                        if 0 <= note_in_bar < len(bar_notes):
                            note = bar_notes[note_in_bar]
                            if hasattr(note, 'note_text'):
                                current_note_text = getattr(note, 'note_text', '—')
                            if hasattr(note, 'key_combination') and note.key_combination:
                                current_key_text = self._format_key_combination(note.key_combination)
                    
                    # 格式化时间
                    elapsed_str = self._format_time(elapsed)
                    remaining_str = self._format_time(max(0, total_time - elapsed))
                    
                    # 更新进度和实时信息
                    loop.call_soon_threadsafe(self._update_progress, progress)
                    loop.call_soon_threadsafe(
                        self._update_realtime_info, 
                        estimated_bar + 1, 
                        current_note_text, 
                        current_key_text, 
                        elapsed_str, 
                        remaining_str
                    )
            
            # 创建一个Future来跟踪播放完成状态
            success_future = loop.run_in_executor(None, play_with_cli_method)
            
            # 同时启动进度监控
            self._monitor_task = asyncio.create_task(monitor_progress())
            
            # 等待播放完成
            success = await success_future
            
            # 强制取消进度监控任务
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            self._monitor_task = None
            
            return success

        except Exception as e:
            if hasattr(self.app, 'notify'):
                self.app.notify(f"播放失败: {str(e)}", severity="error")
            return False

    # 事件处理器
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "play_btn":
            # 播放按钮：检查是否有歌曲
            if not self.current_song:
                # 没有歌曲时提示用户
                if hasattr(self.app, 'notify'):
                    self.app.notify("请先从歌曲浏览器选择一首歌曲", severity="warning")
                return
            
            # 播放按钮：总是开始新的播放
            self._user_stopped = False  # 重置用户停止标志
            asyncio.create_task(self._start_play())
        
        elif button_id == "stop_btn":
            # 停止按钮：停止播放
            # 标记为用户主动停止
            self._user_stopped = True
            
            # 立即停止笛子播放
            self.flute.stop_requested = True
            
            # 强制取消监控任务
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                self._monitor_task = None
            
            # 强制取消播放任务
            if self.play_task and not self.play_task.done():
                self.play_task.cancel()
                self.play_task = None
            
            # 使用统一的原子性重置方法
            self._unified_atomic_reset()
            
            if self.current_song:
                self.post_message(self.PlayStopped(self.current_song))
        
        elif button_id == "replay_btn":
            # 重播按钮：重新开始播放
            self._user_stopped = False  # 重置用户停止标志
            self.progress = 0
            asyncio.create_task(self._start_play())

    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入变化"""
        if event.input.id == "bpm_input":
            try:
                # 检查是否是程序性更新，如果是则不设置用户修改标志
                is_programmatic = getattr(self, '_programmatic_bpm_update', False)
                
                if event.value:  # 用户输入了值
                    bpm = int(event.value)
                    self.current_bpm = max(30, min(300, bpm))  # 限制范围
                    
                    if not is_programmatic:
                        self._user_modified_bpm = True  # 标记用户已修改BPM
                else:
                    # 如果没有输入值，恢复到歌曲默认BPM
                    if hasattr(self, '_user_modified_bpm'):
                        delattr(self, '_user_modified_bpm')
                    if self.current_song:
                        success, song, _ = self.song_service.get_song_safely(self.current_song)
                        if success and song:
                            self.current_bpm = self.song_service.get_effective_bpm(song, None)
                    else:
                        self.current_bpm = 120
            except ValueError:
                pass
        
        elif event.input.id == "ready_time_input":
            try:
                ready_time = int(event.value) if event.value else 3
                self.ready_time = max(0, min(10, ready_time))  # 限制范围
            except ValueError:
                pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """处理选择器变化"""
        if event.select.id == "strategy_select":
            self._hide_manual_offset()

    # 响应式属性监听器
    def watch_current_song(self, song_name: Optional[str]) -> None:
        """监听当前歌曲变化"""
        self._update_song_info()
        self._update_controls_state()

    def watch_play_status(self, status: PlayStatus) -> None:
        """监听播放状态变化"""
        try:
            status_display = self.query_one("#status_display", Static)
            status_map = {
                PlayStatus.STOPPED: "停止",
                PlayStatus.PLAYING: "播放中",
                PlayStatus.LOADING: "加载中",
                PlayStatus.ERROR: "错误"
            }
            status_display.update(status_map.get(status, '未知'))
        except Exception:
            pass
            
        self._update_controls_state()
        
        # 更新音乐播放器样式的状态指示器
        self._update_status_indicator(status, status_map.get(status, '未知'))

    def _update_status_indicator(self, status: PlayStatus, status_text: str) -> None:
        """更新音乐播放器样式的状态指示器"""
        try:
            # 获取音乐播放器容器
            player_container = self.query_one("#music_player", Container)
            
            # 移除旧的状态类
            player_container.remove_class("status-stopped", "status-playing", "status-loading", "status-error")
            
            # 根据状态添加对应的CSS类
            if status == PlayStatus.PLAYING:
                player_container.add_class("status-playing")
            elif status == PlayStatus.LOADING:
                player_container.add_class("status-loading")
            elif status == PlayStatus.ERROR:
                player_container.add_class("status-error")
            else:  # STOPPED
                player_container.add_class("status-stopped")
            
            # 保持border_title为固定的音乐播放器标题
            player_container.border_title = "🎵 音乐播放器"
                
        except Exception:
            # 如果更新失败，忽略错误
            pass

    def watch_progress(self, progress: float) -> None:
        """监听播放进度变化"""
        progress_bar = self.query_one("#play_progress", ProgressBar)
        progress_bar.progress = min(100, max(0, progress))
        
    def watch_current_bar(self, bar: int) -> None:
        """监听当前小节变化"""
        try:
            bar_progress = self.query_one("#bar_progress", Static)
            bar_progress.update(f"{bar}/{self.total_bars}")
        except Exception:
            pass
            
    def watch_current_note(self, note: str) -> None:
        """监听当前音符变化"""
        try:
            note_display = self.query_one("#current_note_display", Static)
            note_display.update(note)
        except Exception:
            pass
            
    def watch_current_key(self, key: str) -> None:
        """监听当前按键变化"""
        try:
            key_display = self.query_one("#current_key_display", Static)
            key_display.update(key)
        except Exception:
            pass
            
    def watch_elapsed_time(self, time: str) -> None:
        """监听已播放时间变化"""
        try:
            # 更新单独的已播放时间显示
            elapsed_display = self.query_one("#elapsed_display", Static)
            elapsed_display.update(time)
        except Exception:
            pass
            
    def watch_remaining_time(self, time: str) -> None:
        """监听剩余时间变化"""
        # 剩余时间不再显示，改为在状态中显示总时长
        pass

    # 公共方法
    def set_current_song(self, song_name: str, auto_play: bool = False) -> None:
        """设置当前歌曲
        
        Args:
            song_name: 歌曲名称
            auto_play: 是否自动开始播放
        """
        
        self.current_song = song_name
        
        # 立即更新界面状态
        self._update_song_info()
        self._update_controls_state()
        
        # 延迟再次更新，确保界面正确刷新
        self.call_later(self._update_song_info)
        self.call_later(self._update_controls_state)
        
        # 自动读取歌曲的BPM并更新当前BPM设置
        # 注意：当设置新歌曲时，我们应该重置用户修改标志，使用歌曲的默认BPM
        if song_name:
            # 重置用户修改标志，让新歌曲使用自己的BPM
            if hasattr(self, '_user_modified_bpm'):
                delattr(self, '_user_modified_bpm')
            success, song, error_msg = self.song_service.get_song_safely(song_name)
            if success and song:
                # 使用与CLI相同的BPM获取逻辑
                effective_bpm = self.song_service.get_effective_bpm(song, None)
                self.current_bpm = effective_bpm
                
                # 更新BPM输入框显示（需要防止触发on_input_changed）
                try:
                    bpm_input = self.query_one("#bpm_input", Input)
                    # 设置一个临时标志，防止程序性更新触发用户修改标志
                    self._programmatic_bpm_update = True
                    bpm_input.value = str(effective_bpm)
                except Exception as e:
                    pass  # 忽略BPM输入框更新失败的错误
                finally:
                    # 清除临时标志
                    if hasattr(self, '_programmatic_bpm_update'):
                        delattr(self, '_programmatic_bpm_update')
            else:
                pass  # 歌曲获取失败，无需处理
        else:
            pass  # 没有歌曲名称，无需处理
        
        if auto_play and song_name:
            # 直接调用播放方法进行测试
            self.call_later(self._trigger_auto_play)
    
    def _update_progress(self, progress: float) -> None:
        """更新播放进度（线程安全）"""
        try:
            self.progress = progress
            progress_bar = self.query_one("#play_progress", ProgressBar)
            progress_bar.progress = min(100, max(0, progress))
        except Exception:
            pass  # 如果UI更新失败，忽略错误
            
    def _update_realtime_info(self, bar_num: int, note_text: str, key_text: str, elapsed: str, remaining: str) -> None:
        """更新实时播放信息（线程安全）"""
        try:
            self.current_bar = bar_num
            self.current_note = note_text
            self.current_key = key_text
            self.elapsed_time = elapsed
            self.remaining_time = remaining
        except Exception:
            pass  # 如果更新失败，忽略错误
            
    def _reset_realtime_info(self) -> None:
        """重置实时信息"""
        self.current_bar = 0
        self.total_bars = 0  # 也重置总小节数
        self.current_note = "—"
        self.current_key = "—"
        self.elapsed_time = "00:00"
        self.remaining_time = "00:00"
    
    def _force_ui_reset(self) -> None:
        """强制重置所有UI元素"""
        try:
            # 强制重置进度条
            progress_bar = self.query_one("#play_progress", ProgressBar)
            progress_bar.progress = 0
            
            # 强制重置所有显示元素
            elapsed_display = self.query_one("#elapsed_display", Static)
            elapsed_display.update("00:00")
            
            bar_progress = self.query_one("#bar_progress", Static)
            bar_progress.update("0/0")
            
            current_note_display = self.query_one("#current_note_display", Static)
            current_note_display.update("—")
            
            current_key_display = self.query_one("#current_key_display", Static)
            current_key_display.update("—")
            
        except Exception:
            # 如果某些元素不存在，忽略错误
            pass
    
    def _atomic_reset(self) -> None:
        """原子性重置所有播放状态和UI（用于用户主动停止）"""
        # 只取消监控任务，不强制取消播放任务（避免干扰正常播放）
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            self._monitor_task = None
        
        # 只有在用户明确停止时才取消播放任务
        if hasattr(self, '_user_stopped') and self._user_stopped:
            if self.play_task and not self.play_task.done():
                self.play_task.cancel()
            
        # 重置所有状态
        self.play_status = PlayStatus.STOPPED
        self.progress = 0.0
        self.current_bar = 0
        self.total_bars = 0
        self.current_note = "—"
        self.current_key = "—"
        self.elapsed_time = "00:00"
        self.remaining_time = "00:00"
        
        # 强制UI更新
        self._force_ui_reset()
    
    def _unified_atomic_reset(self) -> None:
        """统一的原子性重置方法 - 只在用户主动停止时使用"""
        # 立即执行重置
        self._atomic_reset()
        
        # 只延迟一次UI重置，避免过度重置
        self.call_later(self._force_ui_reset)
        
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _format_key_combination(self, key_combination: list) -> str:
        """格式化按键组合显示"""
        if not key_combination:
            return "—"
        
        # 按键映射表，将字符串按键转换为更直观的符号
        key_symbols = {
            "up": "↑",
            "down": "↓", 
            "left": "←",
            "right": "→",
            "1": "1", "2": "2", "3": "3", "4": "4", "5": "5",
            "6": "6", "7": "7", "8": "8", "9": "9", "0": "0"
        }
        
        # 转换按键组合
        symbols = []
        for key in key_combination:
            symbols.append(key_symbols.get(key.lower(), key))
        
        return "+".join(symbols)

    def _trigger_auto_play(self) -> None:
        """触发自动播放"""
        if self.current_song:
            # 直接创建播放任务
            self.play_status = PlayStatus.STOPPED  # 确保状态正确
            asyncio.create_task(self._start_play())
    
    async def _delayed_auto_play(self) -> None:
        """延迟自动播放方法（备用）"""
        # 等待一小段时间确保UI完全更新
        await asyncio.sleep(0.1)
        
        if self.current_song:
            # 强制重置播放状态，确保可以开始播放
            self.play_status = PlayStatus.STOPPED
            await self._start_play()

    def stop_playback(self) -> None:
        """停止播放"""
        if self.play_task:
            self.play_task.cancel()
        self.play_status = PlayStatus.STOPPED
        self.progress = 0
        self._reset_realtime_info()

    def _on_playback_progress(self, current_bar: int, total_bars: int, message: str) -> None:
        """播放进度回调，从后台线程调用"""
        try:
            # 使用 Textual 的 call_from_thread 方法，这是线程安全的
            self.call_from_thread(self._update_playback_progress, current_bar, total_bars, message)
        except Exception:
            # 静默忽略错误，避免干扰TUI
            pass

    def _update_playback_progress(self, current_bar: int, total_bars: int, message: str) -> None:
        """在主线程中更新播放进度（线程安全）"""
        try:
            # 更新小节进度
            self.current_bar = current_bar
            self.total_bars = total_bars
            
            # 计算整体进度
            progress = (current_bar / total_bars * 100) if total_bars > 0 else 0
            self.progress = progress
            
            # 更新状态显示
            try:
                status_display = self.query_one("#status_display", Static)
                status_display.update(f"播放中 ({current_bar}/{total_bars})")
            except Exception:
                pass
            
        except Exception:
            # 静默忽略UI更新错误
            pass

    def get_play_settings(self) -> dict:
        """获取当前播放设置"""
        # 安全获取策略值
        strategy = self._get_safe_strategy_value()
            
        # 安全获取手动偏移输入
        try:
            manual_input = self.query_one("#manual_offset_input", Input)
        except Exception:
            manual_input = None
        
        settings = {
            "bpm": self.current_bpm,
            "ready_time": self.ready_time,
            "strategy": strategy
        }
        
        if strategy == "manual" and manual_input and manual_input.value:
            try:
                settings["manual_offset"] = float(manual_input.value)
            except ValueError:
                settings["manual_offset"] = 0.0
        
        return settings