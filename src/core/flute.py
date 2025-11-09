"""新的笛子控制器 - 使用物理音符系统

改进点：
- 采用基于绝对时间轴的调度，避免顺序 sleep 导致节拍累计漂移。
- 保留 ESC 及时停止能力，同时减少无意义的分段等待。
- 提供可选的安静模式以减少逐音打印对时序的干扰（默认关闭以保持现有输出）。
"""

import time
from time import perf_counter
from typing import List, Optional
from pynput.keyboard import Controller, Key, Listener
import threading

from ..data.music_theory import PhysicalNote
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AutoFlute:
    """自动笛子控制器 - 使用物理音符系统"""

    # 按键字符串到Key对象的映射
    KEY_MAPPING = {
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7",
        "8": "8",
        "9": "9",
        "0": "0",
        "x": "x",
        "z": "z",
        "c": "c",
        "v": "v",
        "b": "b",
        "n": "n",
        "m": "m",
    }

    def __init__(
        self,
        blow_key: str = "x",
        keyboard: Optional[Controller] = None,
        quiet: bool = False,
    ):
        self.keyboard = keyboard or Controller()
        self.blow_key = blow_key
        self.stop_requested = False
        self.listener = None
        self.quiet = quiet
        # 等待策略参数（可根据需要微调）
        self._long_sleep_slice = 0.05  # >50ms 使用较长 sleep 片段
        self._guard_time = 0.002  # 2ms 保护，避免 oversleep
        logger.info(
            f"AutoFlute initialized with blow_key={blow_key}, quiet={quiet}"
        )

    def _convert_key(self, key_str: str):
        """将字符串按键转换为pynput可用的按键对象"""
        return self.KEY_MAPPING.get(key_str, key_str)

    def _on_press(self, key):
        """处理按键事件"""
        if key == Key.esc:
            print(f"\n⏹️  检测到ESC键，停止演奏...")
            self.stop_requested = True
            return False  # 停止监听

    def _start_stop_listener(self):
        """启动ESC键监听"""
        self.stop_requested = False
        self.listener = Listener(on_press=self._on_press)
        self.listener.start()
        print(f"🎹 按ESC键可随时停止演奏")

    def _stop_listener(self):
        """停止ESC键监听"""
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _wait_until(self, target_time: float) -> bool:
        """等待直到目标绝对时间点，期间可响应停止。

        返回 False 表示已请求停止，应中断后续演奏。
        """
        while True:
            if self.stop_requested:
                return False
            now = perf_counter()
            remaining = target_time - now
            if remaining <= 0:
                return True

            # 长等待：最多按 50ms 片段 sleep，避免过多切片误差
            if remaining > self._long_sleep_slice + self._guard_time:
                time.sleep(self._long_sleep_slice)
                continue

            # 短等待：留出 guard，降低 oversleep 风险
            if remaining > self._guard_time:
                time.sleep(remaining - self._guard_time)
                continue

            # 最后 2ms 忙等对齐，确保精确到目标时间
            while perf_counter() < target_time:
                if self.stop_requested:
                    return False
            return True

    def _play_note_scheduled(
        self, note: PhysicalNote, beat_interval: float, start_at: float
    ) -> bool:
        """在指定绝对时间 start_at 开始演奏该音符（或休止），采用绝对时长控制。"""
        if self.stop_requested:
            return False

        blow_time = note.time_factor * beat_interval
        end_at = start_at + blow_time

        # 休止符：等待至结束时间
        if not note.key_combination:
            if not self.quiet:
                print(f"🎵 休止符 - 等待 {blow_time:.2f}s")
            logger.debug(f"Rest note, waiting until {end_at:.6f}")
            return self._wait_until(end_at)

        # 打印信息（可静音）
        if not self.quiet:
            key_display = " + ".join(note.key_combination)
            print(
                f"🎵 演奏音符: {note.notation} (高度: {note.physical_height:.1f}) - 按键: {key_display} - 时长: {blow_time:.2f}s"
            )

        # 等待到起始时间（如已落后则立即开始）
        if not self._wait_until(start_at):
            return False

        # 按下所有按键
        for key_str in note.key_combination:
            if self.stop_requested:
                return False
            key = self._convert_key(key_str)
            self.keyboard.press(key)
            logger.debug(f"Pressed key: {key_str} -> {key}")

        # 按下吹气键
        blow_key = self._convert_key(self.blow_key)
        self.keyboard.press(blow_key)
        logger.debug(f"Started blowing; target end at {end_at:.6f}")

        # 保持直到结束时间
        if not self._wait_until(end_at):
            # 停止请求：立即释放
            try:
                self.keyboard.release(blow_key)
            finally:
                for key_str in note.key_combination:
                    key = self._convert_key(key_str)
                    self.keyboard.release(key)
            return False

        # 正常结束：释放按键
        self.keyboard.release(blow_key)
        for key_str in note.key_combination:
            key = self._convert_key(key_str)
            self.keyboard.release(key)
            logger.debug(f"Released key: {key_str} -> {key}")

        return True

    def play_song(self, bars: List[List[PhysicalNote]], beat_interval: float) -> None:
        """演奏整首乐曲（绝对时间调度，防止节拍漂移）"""
        print(f"🎶 开始演奏乐曲 (共 {len(bars)} 小节)")
        logger.info(f"Starting to play song with {len(bars)} bars")

        # 启动ESC键监听
        self._start_stop_listener()

        try:
            # 全局时间轴：从当前时刻开始
            next_start = perf_counter()

            for i, bar in enumerate(bars, 1):
                if self.stop_requested:
                    break

                print(f"\n📊 第 {i}/{len(bars)} 小节:")
                logger.info(f"Playing bar {i}/{len(bars)}")

                # 小节标题打印完成后，不等待，直接按照 next_start 调度
                for note in bar:
                    if self.stop_requested:
                        break
                    # 采用绝对时间播放单音
                    if not self._play_note_scheduled(note, beat_interval, next_start):
                        # 被请求停止
                        break
                    # 滚动到下一个音的起点（基于乐曲节拍，而非实际耗时）
                    next_start += note.time_factor * beat_interval

            if self.stop_requested:
                print(f"\n⏹️  演奏已停止")
                logger.info("Song stopped by user")
            else:
                print(f"\n🎉 乐曲演奏完成！")
                logger.info("Song finished")
        finally:
            # 停止ESC键监听
            self._stop_listener()
