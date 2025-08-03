"""新的笛子控制器 - 使用物理音符系统"""

import time
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
        progress_callback: Optional[callable] = None,
        tui_mode: bool = False,
    ):
        self.keyboard = keyboard or Controller()
        self.blow_key = blow_key
        self.stop_requested = False
        self.listener = None
        self.progress_callback = progress_callback
        self.tui_mode = tui_mode
        
        # TUI模式下减少日志输出
        if not tui_mode:
            logger.info(f"AutoFlute initialized with blow_key={blow_key}")

    def _convert_key(self, key_str: str):
        """将字符串按键转换为pynput可用的按键对象"""
        return self.KEY_MAPPING.get(key_str, key_str)

    def _on_press(self, key):
        """处理按键事件"""
        if key == Key.esc:
            if not self.tui_mode:
                logger.info("ESC key detected, stopping playback...")
            self.stop_requested = True
            return False  # 停止监听

    def _start_stop_listener(self):
        """启动ESC键监听"""
        self.stop_requested = False
        self.listener = Listener(on_press=self._on_press)
        self.listener.start()
        if not self.tui_mode:
            logger.info("ESC key listener started - press ESC to stop playback")

    def _stop_listener(self):
        """停止ESC键监听"""
        if self.listener:
            self.listener.stop()
            self.listener = None

    def play_physical_note(self, note: PhysicalNote, beat_interval: float) -> bool:
        """演奏物理音符，返回是否应该继续演奏"""
        if self.stop_requested:
            return False

        blow_time = note.time_factor * beat_interval

        if not note.key_combination:
            # 休止符，只需要等待
            logger.debug(f"Rest note, waiting for {blow_time:.2f}s")
            # 分段等待，以便能响应停止请求
            steps = max(1, int(blow_time * 10))  # 每100ms检查一次
            for _ in range(steps):
                if self.stop_requested:
                    return False
                time.sleep(blow_time / steps)
            return True

        # 显示当前演奏的音符信息
        key_display = (
            " + ".join(note.key_combination) if note.key_combination else "无按键"
        )
        logger.debug(
            f"Playing note: {note.notation} (height: {note.physical_height:.1f}) - keys: {key_display} - duration: {blow_time:.2f}s"
        )

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
        logger.debug(f"Started blowing for {blow_time:.2f}s")

        # 持续时间 - 分段等待以便响应停止请求
        steps = max(1, int(blow_time * 10))  # 每100ms检查一次
        for _ in range(steps):
            if self.stop_requested:
                # 立即释放所有按键
                self.keyboard.release(blow_key)
                for key_str in note.key_combination:
                    key = self._convert_key(key_str)
                    self.keyboard.release(key)
                return False
            time.sleep(blow_time / steps)

        # 释放吹气键
        self.keyboard.release(blow_key)

        # 释放所有按键
        for key_str in note.key_combination:
            key = self._convert_key(key_str)
            self.keyboard.release(key)
            logger.debug(f"Released key: {key_str} -> {key}")

        return True

    def play_bar(self, bar: List[PhysicalNote], beat_interval: float) -> bool:
        """演奏一个小节，返回是否应该继续演奏"""
        if self.stop_requested:
            return False

        if not self.tui_mode:
            logger.info(f"Playing bar with {len(bar)} notes")

        for note in bar:
            if not self.play_physical_note(note, beat_interval):
                return False
            logger.debug(
                f"Played note: {note.notation} "
                f"(physical_height={note.physical_height}, "
                f"time={note.time_factor * beat_interval:.2f}s, "
                f"keys={note.key_combination})"
            )

        return True

    def play_song(self, bars: List[List[PhysicalNote]], beat_interval: float) -> None:
        """演奏整首乐曲"""
        if not self.tui_mode:
            logger.info(f"Starting to play song with {len(bars)} bars")

        # 启动ESC键监听
        self._start_stop_listener()

        try:
            for i, bar in enumerate(bars, 1):
                if self.stop_requested:
                    break

                if not self.tui_mode:
                    logger.info(f"Playing bar {i}/{len(bars)}")
                
                # 通知进度回调
                if self.progress_callback:
                    try:
                        self.progress_callback(i, len(bars), f"Playing bar {i}/{len(bars)}")
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")

                if not self.play_bar(bar, beat_interval):
                    break

            if not self.tui_mode:
                if self.stop_requested:
                    logger.info("Song stopped by user")
                else:
                    logger.info("Song finished")
        finally:
            # 停止ESC键监听
            self._stop_listener()
