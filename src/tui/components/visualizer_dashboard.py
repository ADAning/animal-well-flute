"""动态音乐可视化仪表盘组件"""

import asyncio
import time
import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from textual.widgets import Static, Button, ProgressBar, Label
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.message import Message
from textual.timer import Timer
from rich.text import Text

from ...services.song_service_base import SongServiceBase
from ...data.songs.song_manager import SongManager


@dataclass
class ParticleData:
    """粒子数据结构"""
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    life: float
    intensity: float
    color: str = "cyan"


@dataclass
class SpectrumBar:
    """频谱条数据"""
    frequency: str
    height: int
    color: str
    intensity: float


class VisualizerDashboard(Container):
    """动态音乐可视化仪表盘"""
    
    # 自定义消息类
    class QuickPlayRequested(Message):
        """快速播放请求"""
        def __init__(self, action: str) -> None:
            self.action = action  # "random", "favorite", "continue"
            super().__init__()
    
    # 响应式属性
    current_song: reactive[Optional[str]] = reactive(None)
    play_status: reactive[str] = reactive("stopped")
    progress: reactive[float] = reactive(0.0)
    elapsed_time: reactive[str] = reactive("00:00")
    remaining_time: reactive[str] = reactive("00:00")
    
    # 可视化状态
    visualization_active: reactive[bool] = reactive(False)
    particle_intensity: reactive[int] = reactive(50)
    theme_mode: reactive[str] = reactive("cave")  # cave, neon, classic
    
    def __init__(self, song_service: SongServiceBase):
        """初始化可视化仪表盘"""
        super().__init__()
        self.song_service = song_service
        self.song_manager = SongManager()
        
        # 粒子系统
        self.particles: List[ParticleData] = []
        self.max_particles = 30  # 减少粒子数量以提高性能
        
        # 频谱数据（模拟）
        self.spectrum_bars: List[SpectrumBar] = []
        self._init_spectrum_bars()
        
        # 统计数据
        self.stats = {
            "total_songs": 0,
            "today_played": 0,
            "total_time": "0h 0m",
            "favorite_genre": "Unknown"
        }
        
        # 动画定时器
        self.particle_timer: Optional[Timer] = None
        self.spectrum_timer: Optional[Timer] = None
        
    def compose(self) -> ComposeResult:
        """构建可视化仪表盘界面"""
        
        # 主标题区域 - Animal Well主题化
        with Container(id="visualizer_header", classes="visualizer_header"):
            yield Static("🕳️ Animal Well Flute - 神秘洞穴音乐可视化中心 🕳️", id="main_title")
            yield Static("∿∿∿ 静谧洞穴，等待音乐的呼唤 ∿∿∿", id="subtitle")
        
        # 主内容区域
        with Container(id="visualizer_main", classes="visualizer_main"):
            
            # 当前播放大卡片 - 洞穴主题
            with Container(id="current_playing_card", classes="current_playing_card") as playing_card:
                playing_card.border_title = "🎼 洞穴乐章"
                yield Static("🌌 暂无乐章回响", id="current_song_display")
                yield Static("在深邃洞穴中，选择一首旋律唤醒沉睡的音符", id="current_song_subtitle")
                yield ProgressBar(total=100, show_percentage=True, id="main_progress")
                
                # 播放信息行 - 神秘符号
                with Horizontal(classes="playing_info_row"):
                    yield Static("🔮 音调未知", id="key_info")
                    yield Static("⚡ — 节拍", id="bpm_info") 
                    yield Static("🕰️ 00:00/00:00", id="time_info")
            
            # 中间区域：频谱 + 统计
            with Horizontal(classes="middle_section"):
                
                # 实时频谱可视化 - 洞穴回音
                with Container(id="spectrum_section", classes="spectrum_section") as spectrum_container:
                    spectrum_container.border_title = "🔊 洞穴回音频谱"
                    yield Container(id="spectrum_bars", classes="spectrum_container")
                
                # 统计信息卡片 - 探险日志
                with Container(id="stats_section", classes="stats_section") as stats_container:
                    stats_container.border_title = "📜 探险日志"
                    with Vertical(classes="stats_cards"):
                        yield Static("🎼 演奏曲目: 0", id="stat_played")
                        yield Static("⌛ 探索时长: 0h 0m", id="stat_duration")
                        yield Static("💎 完成度: 0%", id="stat_completion")
            
            # 底部区域：快速操作 + 系统状态
            with Horizontal(classes="bottom_section"):
                
                # 快速操作区域 - 魔法传送门
                with Container(id="quick_actions", classes="quick_actions") as actions_container:
                    actions_container.border_title = "🌟 魔法传送门"
                    with Horizontal(classes="action_buttons"):
                        yield Button("🎰 随机探索", id="random_btn", classes="quick_btn")
                        yield Button("💎 珍藏音匣", id="favorite_btn", classes="quick_btn")
                        yield Button("🎹 演奏台", id="player_btn", classes="quick_btn primary")
                
                # 系统状态区域 - 洞穴生态
                with Container(id="system_status", classes="system_status") as status_container:
                    status_container.border_title = "🕳️ 洞穴生态"
                    with Vertical(classes="status_items"):
                        yield Static("🗃️ 乐谱典藏: 载入中...", id="songs_status")
                        yield Static("🔮 音频水晶: 正常", id="audio_status")
                        yield Static("⚙️ 魔法引擎: 运行中", id="engine_status")
        
        # 粒子背景容器（使用绝对定位覆盖）
        with Container(id="particle_background", classes="particle_background"):
            yield Container(id="particles_container")
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._load_stats()
        self._init_particles()
        self._start_animations()
        
        # 启动可视化效果
        self.visualization_active = True
        
    def _init_spectrum_bars(self) -> None:
        """初始化频谱显示"""
        frequencies = ["C", "D", "E", "F", "G", "A", "B", "C"]
        colors = ["green", "green", "blue", "blue", "blue", "yellow", "yellow", "yellow"]
        
        for i, (freq, color) in enumerate(zip(frequencies, colors)):
            self.spectrum_bars.append(SpectrumBar(
                frequency=freq,
                height=random.randint(1, 8),
                color=color,
                intensity=random.random()
            ))
    
    def _init_particles(self) -> None:
        """初始化粒子系统"""
        for _ in range(self.max_particles):
            particle = ParticleData(
                x=random.random() * 100,
                y=random.random() * 100,
                velocity_x=(random.random() - 0.5) * 0.5,
                velocity_y=(random.random() - 0.5) * 0.5,
                life=random.random(),
                intensity=random.random(),
                color="cyan" if random.random() > 0.5 else "magenta"
            )
            self.particles.append(particle)
    
    def _start_animations(self) -> None:
        """启动动画定时器"""
        # 粒子更新频率：每100ms更新一次
        self.particle_timer = self.set_interval(0.1, self._update_particles)
        
        # 频谱更新频率：每150ms更新一次
        self.spectrum_timer = self.set_interval(0.15, self._update_spectrum)
    
    def _update_particles(self) -> None:
        """更新粒子位置和状态"""
        # 更新标题区域的动态效果
        try:
            subtitle = self.query_one("#subtitle")
            
            if self.play_status == "playing":
                # 播放时的动态效果 - 洞穴能量流动
                energy_chars = ["✦", "✧", "❋", "⋄", "◊", "💎", "🔮", "⚡"]
                cave_chars = ["∿", "∼", "≋", "⋈"]
                left_energy = random.choices(energy_chars, k=2) + random.choices(cave_chars, k=1)
                right_energy = random.choices(cave_chars, k=1) + random.choices(energy_chars, k=2)
                
                dynamic_subtitle = f"{''.join(left_energy)} 洞穴深处，音乐能量正在共鸣流淌 {''.join(right_energy)}"
                subtitle.update(dynamic_subtitle)
                
                # 更新当前播放卡片的动态标题
                current_playing = self.query_one("#current_playing_card")
                if hasattr(current_playing, 'add_class'):
                    current_playing.add_class("playing")
                    
            elif self.visualization_active:
                # 可视化激活但未播放时的神秘氛围
                mystic_chars = ["∿", "∼", "∽", "⋈", "◊"]
                left_mystic = random.choice(mystic_chars)
                right_mystic = random.choice(mystic_chars)
                
                dynamic_subtitle = f"{left_mystic}∿∼ 神秘洞穴中，音符精灵静候旋律的召唤 ∼∿{right_mystic}"
                subtitle.update(dynamic_subtitle)
                
            else:
                # 静止状态 - 沉睡的洞穴
                subtitle.update("∿∿∿ 静谧洞穴，等待音乐的呼唤 ∿∿∿")
                
                # 移除播放类
                current_playing = self.query_one("#current_playing_card")
                if hasattr(current_playing, 'remove_class'):
                    current_playing.remove_class("playing")
                    
        except Exception:
            pass
            
        # 更新真正的粒子数据（用于未来的高级效果）
        for particle in self.particles:
            # 更新位置
            particle.x += particle.velocity_x
            particle.y += particle.velocity_y
            
            # 边界处理
            if particle.x < 0 or particle.x > 100:
                particle.velocity_x *= -1
            if particle.y < 0 or particle.y > 100:
                particle.velocity_y *= -1
                
            # 生命周期管理
            particle.life -= 0.01
            if particle.life <= 0:
                particle.life = 1.0
                particle.x = random.random() * 100
                particle.y = random.random() * 100
        
        # 如果正在播放，增加粒子活跃度
        if self.play_status == "playing":
            self._pulse_particles()
    
    def _pulse_particles(self) -> None:
        """让粒子随节拍脉动"""
        pulse_strength = 0.1 + (self.particle_intensity / 100) * 0.5
        
        for particle in self.particles:
            # 随机选择一些粒子进行脉动
            if random.random() < 0.3:
                particle.velocity_x += (random.random() - 0.5) * pulse_strength
                particle.velocity_y += (random.random() - 0.5) * pulse_strength
                particle.intensity = min(1.0, particle.intensity + pulse_strength)
    
    def _update_spectrum(self) -> None:
        """更新频谱可视化"""
        try:
            spectrum_container = self.query_one("#spectrum_bars")
            
            # 模拟频谱数据变化
            spectrum_lines = []
            
            # 第一行：频率标签
            freq_line = "   ".join([f"{bar.frequency:>2}" for bar in self.spectrum_bars])
            spectrum_lines.append(freq_line)
            
            # 动态更新频谱条
            for bar in self.spectrum_bars:
                if self.play_status == "playing":
                    # 播放时动态变化
                    bar.height = max(1, bar.height + random.randint(-2, 3))
                    bar.height = min(8, bar.height)
                    bar.intensity = min(1.0, max(0.1, bar.intensity + (random.random() - 0.5) * 0.3))
                else:
                    # 静止时缓慢衰减
                    bar.height = max(1, bar.height - 1)
                    bar.intensity *= 0.95
            
            # 构建频谱显示（从上到下8行）
            for row in range(8, 0, -1):
                row_chars = []
                for bar in self.spectrum_bars:
                    if bar.height >= row:
                        # 根据强度和播放状态选择字符和效果
                        if self.play_status == "playing":
                            # 播放时使用更炫酷的字符
                            if bar.intensity > 0.9:
                                char = "▇" if random.random() > 0.5 else "█"
                            elif bar.intensity > 0.7:
                                char = "▆" if random.random() > 0.3 else "▇"
                            elif bar.intensity > 0.5:
                                char = "▅" if random.random() > 0.3 else "▆"
                            elif bar.intensity > 0.3:
                                char = "▄" if random.random() > 0.3 else "▅"
                            else:
                                char = "▃" if random.random() > 0.5 else "▄"
                        else:
                            # 静止时使用基础字符
                            if bar.intensity > 0.8:
                                char = "█"
                            elif bar.intensity > 0.5:
                                char = "▓"
                            elif bar.intensity > 0.3:
                                char = "▒"
                            else:
                                char = "░"
                    else:
                        char = " "
                    
                    # 根据频率给不同颜色提示（通过字符变化）
                    if bar.frequency in ["C", "G"]:  # 主音
                        row_chars.append(f"{char}▌{char}")
                    elif bar.frequency in ["E", "B"]:  # 三音
                        row_chars.append(f"{char}▐{char}")
                    else:  # 其他音
                        row_chars.append(f"{char} {char}")
                        
                spectrum_lines.append(" ".join(row_chars))
            
            # 更新显示
            spectrum_display = "\n".join(spectrum_lines)
            if hasattr(spectrum_container, 'update'):
                spectrum_container.update(spectrum_display)
                
        except Exception:
            # 如果UI还未完全初始化，忽略错误
            pass
    
    def _load_stats(self) -> None:
        """加载统计数据"""
        try:
            # 获取歌曲库信息
            songs_info = self.song_manager.list_songs_with_info()
            self.stats["total_songs"] = len(songs_info)
            
            # 模拟其他统计数据
            self.stats["today_played"] = random.randint(0, 8)
            self.stats["total_time"] = f"{random.randint(0, 5)}h {random.randint(0, 59)}m"
            self.stats["favorite_genre"] = random.choice(["古典", "民谣", "游戏音乐", "电子"])
            
            # 更新显示
            self._update_stats_display()
            
        except Exception as e:
            # 加载失败时使用默认值
            self.stats["total_songs"] = 0
    
    def _update_stats_display(self) -> None:
        """更新统计显示"""
        try:
            self.query_one("#stat_played").update(f"🎼 演奏曲目: {self.stats['today_played']}")
            self.query_one("#stat_duration").update(f"⌛ 探索时长: {self.stats['total_time']}")
            
            completion_rate = min(100, (self.stats['today_played'] * 20))
            self.query_one("#stat_completion").update(f"💎 完成度: {completion_rate}%")
            
            self.query_one("#songs_status").update(f"🗃️ 乐谱典藏: {self.stats['total_songs']}首")
            
        except Exception:
            # UI未完全加载时忽略错误
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "random_btn":
            self.post_message(self.QuickPlayRequested("random"))
        elif button_id == "favorite_btn":
            self.post_message(self.QuickPlayRequested("favorite"))
        elif button_id == "player_btn":
            self.post_message(self.QuickPlayRequested("player"))
    
    # 响应式属性监听器
    def watch_current_song(self, song_name: Optional[str]) -> None:
        """监听当前歌曲变化"""
        try:
            if song_name:
                self.query_one("#current_song_display").update(f"🌟 {song_name}")
                self.query_one("#current_song_subtitle").update("洞穴中回响着这首神秘的旋律")
                
                # 获取歌曲信息
                success, song, _ = self.song_service.get_song_safely(song_name)
                if success and song:
                    bpm = song.bpm
                    self.query_one("#bpm_info").update(f"⚡ {bpm} 节拍")
                    # 添加音调信息（如果有）
                    self.query_one("#key_info").update("🔮 C大调")  # 默认调性
            else:
                self.query_one("#current_song_display").update("🌌 暂无乐章回响")
                self.query_one("#current_song_subtitle").update("在深邃洞穴中，选择一首旋律唤醒沉睡的音符")
                self.query_one("#bpm_info").update("⚡ — 节拍")
                self.query_one("#key_info").update("🔮 音调未知")
        except Exception:
            pass
    
    def watch_play_status(self, status: str) -> None:
        """监听播放状态变化"""
        self.visualization_active = (status == "playing")
        
        # 根据播放状态调整粒子活跃度
        if status == "playing":
            self.particle_intensity = min(100, self.particle_intensity + 20)
        else:
            self.particle_intensity = max(20, self.particle_intensity - 10)
    
    def watch_progress(self, progress: float) -> None:
        """监听播放进度变化"""
        try:
            progress_bar = self.query_one("#main_progress", ProgressBar)
            progress_bar.progress = min(100, max(0, progress))
        except Exception:
            pass
    
    def watch_elapsed_time(self, time: str) -> None:
        """监听播放时间变化"""
        try:
            time_info = f"⏱️ {time}/{self.remaining_time}"
            self.query_one("#time_info").update(time_info)
        except Exception:
            pass
    
    def watch_remaining_time(self, time: str) -> None:
        """监听剩余时间变化"""
        try:
            time_info = f"⏱️ {self.elapsed_time}/{time}"
            self.query_one("#time_info").update(time_info)
        except Exception:
            pass
    
    # 公共方法
    def update_playing_info(self, song_name: str, progress: float, elapsed: str, remaining: str, status: str) -> None:
        """更新播放信息"""
        self.current_song = song_name
        self.progress = progress
        self.elapsed_time = elapsed
        self.remaining_time = remaining
        self.play_status = status
    
    def set_visualization_intensity(self, intensity: int) -> None:
        """设置可视化强度"""
        self.particle_intensity = max(0, min(100, intensity))
    
    def set_theme_mode(self, theme: str) -> None:
        """设置主题模式"""
        if theme in ["cave", "neon", "classic"]:
            self.theme_mode = theme