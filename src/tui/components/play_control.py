"""播放控制组件"""

from textual.widgets import Button, Static, ProgressBar, Input, Select
from textual.widgets.option_list import Option
from textual.containers import Container, Horizontal, Vertical
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

    def __init__(self, song_service: SongServiceBase):
        """初始化播放控制组件"""
        super().__init__()
        self.song_service = song_service
        self.parser = RelativeParser()
        self.converter = AutoConverter()
        self.flute = AutoFlute()
        self.play_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """构建组件界面"""
        with Vertical():
            # 当前歌曲信息
            with Container(id="current_song_info"):
                yield Static("当前歌曲: 无", id="song_title")
                yield ProgressBar(total=100, show_percentage=True, id="play_progress")
                yield Static("状态: 停止", id="play_status_text")

            # 播放控制按钮
            with Container(id="play_controls"):
                with Horizontal(classes="control_row"):
                    yield Button("▶️ 播放", id="play_btn", variant="primary")
                    yield Button("⏸️ 暂停", id="pause_btn", variant="default")
                    yield Button("⏹️ 停止", id="stop_btn", variant="default")
                    yield Button("🔄 重播", id="replay_btn", variant="default")

            # 播放设置
            with Container(id="play_settings"):
                with Horizontal(classes="settings_row"):
                    yield Static("BPM:", classes="setting_label")
                    yield Input(
                        value=str(self.current_bpm),
                        placeholder="BPM",
                        id="bpm_input",
                        classes="number_input"
                    )
                    yield Static("准备时间:", classes="setting_label")
                    yield Input(
                        value=str(self.ready_time),
                        placeholder="3",
                        id="ready_time_input",
                        classes="number_input"
                    )

            # 策略选择
            with Container(id="strategy_settings"):
                yield Static("映射策略:", classes="setting_label")
                yield Select(
                    [
                        ("optimal", "最优映射"),
                        ("high", "偏高音域"), 
                        ("low", "偏低音域"),
                        ("auto", "自动选择"),
                        ("manual", "手动偏移"),
                        ("none", "无偏移")
                    ],
                    id="strategy_select"
                )
                yield Input(
                    placeholder="手动偏移值 (半音)",
                    id="manual_offset_input",
                    classes="number_input"
                )

            # 歌曲信息显示
            with Container(id="song_analysis"):
                yield Static("音域信息: 未分析", id="range_info")
                yield Static("映射建议: 未分析", id="mapping_info")

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
        play_btn = self.query_one("#play_btn", Button)
        pause_btn = self.query_one("#pause_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)
        replay_btn = self.query_one("#replay_btn", Button)

        if self.play_status == PlayStatus.STOPPED:
            play_btn.disabled = not self.current_song
            pause_btn.disabled = True
            stop_btn.disabled = True
            replay_btn.disabled = not self.current_song

        elif self.play_status == PlayStatus.PLAYING:
            play_btn.disabled = True
            pause_btn.disabled = False
            stop_btn.disabled = False
            replay_btn.disabled = False

        elif self.play_status == PlayStatus.PAUSED:
            play_btn.disabled = False
            pause_btn.disabled = True
            stop_btn.disabled = False
            replay_btn.disabled = False

        elif self.play_status == PlayStatus.LOADING:
            play_btn.disabled = True
            pause_btn.disabled = True
            stop_btn.disabled = True
            replay_btn.disabled = True

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
        song_title = self.query_one("#song_title", Static)
        if self.current_song:
            song_title.update(f"当前歌曲: {self.current_song}")
            self._analyze_current_song()
        else:
            song_title.update("当前歌曲: 无")
            self._clear_analysis()

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
        range_info = self.query_one("#range_info", Static)
        mapping_info = self.query_one("#mapping_info", Static)
        range_info.update(range_text)
        mapping_info.update(mapping_text)

    def _clear_analysis(self) -> None:
        """清除分析信息"""
        self._update_analysis_info("音域信息: 未分析", "映射建议: 未分析")

    async def _start_play(self) -> None:
        """开始播放"""
        if not self.current_song:
            return

        try:
            self.play_status = PlayStatus.LOADING
            
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
            
            # 调用真实的播放逻辑
            success = await self._real_play(bpm, ready_time)
            
            if success:
                self.play_status = PlayStatus.STOPPED
                self.progress = 0
                self.post_message(self.PlayStopped(self.current_song))
            else:
                self.play_status = PlayStatus.ERROR

        except Exception as e:
            self.play_status = PlayStatus.ERROR
            if hasattr(self.app, 'notify'):
                self.app.notify(f"播放失败: {str(e)}", severity="error")

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
                
                status_text = self.query_one("#play_status_text", Static)
                status_text.update(f"状态: 准备中... {i}")
                await asyncio.sleep(1)

            # 开始真实播放
            status_text = self.query_one("#play_status_text", Static)
            status_text.update("状态: 播放中...")
            
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
                    print(f"播放过程中发生错误: {e}")
                    return False
            
            # 如果需要进度更新，可以创建一个监控任务
            async def monitor_progress():
                """监控播放进度（简单估算）"""
                total_notes = sum(len(bar) for bar in converted)
                if total_notes == 0:
                    return
                
                # 估算总播放时间
                total_time = 0
                for bar in converted:
                    for note in bar:
                        total_time += note.time_factor * beat_interval
                
                start_time = asyncio.get_event_loop().time()
                while not success_future.done():
                    await asyncio.sleep(0.1)
                    elapsed = asyncio.get_event_loop().time() - start_time
                    progress = min(100, (elapsed / total_time) * 100) if total_time > 0 else 0
                    loop.call_soon_threadsafe(self._update_progress, progress)
            
            # 创建一个Future来跟踪播放完成状态
            success_future = loop.run_in_executor(None, play_with_cli_method)
            
            # 同时启动进度监控
            monitor_task = asyncio.create_task(monitor_progress())
            
            # 等待播放完成
            success = await success_future
            monitor_task.cancel()  # 取消进度监控任务
            
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
            if self.play_status == PlayStatus.PAUSED:
                self.play_status = PlayStatus.PLAYING
            else:
                asyncio.create_task(self._start_play())
        
        elif button_id == "pause_btn":
            if self.play_status == PlayStatus.PLAYING:
                self.play_status = PlayStatus.PAUSED
                self.post_message(self.PlayPaused(self.current_song or ""))
        
        elif button_id == "stop_btn":
            if self.play_task:
                self.play_task.cancel()
            self.play_status = PlayStatus.STOPPED
            self.progress = 0
            progress_bar = self.query_one("#play_progress", ProgressBar)
            progress_bar.progress = 0
            if self.current_song:
                self.post_message(self.PlayStopped(self.current_song))
        
        elif button_id == "replay_btn":
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
        status_text = self.query_one("#play_status_text", Static)
        status_map = {
            PlayStatus.STOPPED: "停止",
            PlayStatus.PLAYING: "播放中",
            PlayStatus.PAUSED: "暂停",
            PlayStatus.LOADING: "加载中",
            PlayStatus.ERROR: "错误"
        }
        status_text.update(f"状态: {status_map[status]}")
        self._update_controls_state()

    def watch_progress(self, progress: float) -> None:
        """监听播放进度变化"""
        progress_bar = self.query_one("#play_progress", ProgressBar)
        progress_bar.progress = min(100, max(0, progress))

    # 公共方法
    def set_current_song(self, song_name: str, auto_play: bool = False) -> None:
        """设置当前歌曲
        
        Args:
            song_name: 歌曲名称
            auto_play: 是否自动开始播放
        """
            
        self.current_song = song_name
        
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