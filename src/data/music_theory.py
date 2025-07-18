"""音乐理论模块 - 处理相对音高和物理音高的映射"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MappingStrategy(Enum):
    """音高映射策略"""

    OPTIMAL = "optimal"  # 优化居中
    HIGH = "high"  # 尽可能高
    LOW = "low"  # 尽可能低
    MANUAL = "manual"  # 手动指定


@dataclass
class RelativeNote:
    """相对音高音符 - 简谱中的音符标记"""

    notation: str  # 音符标记，如 "1", "h3", "l5"
    relative_height: float  # 相对高度值
    time_factor: float  # 时值因子

    def __post_init__(self):
        if self.time_factor <= 0:
            raise ValueError("time_factor must be positive")


@dataclass
class PhysicalNote:
    """物理音高音符 - 笛子实际可演奏的音符"""

    notation: str  # 原始音符标记
    physical_height: float  # 物理高度值
    time_factor: float  # 时值因子
    key_combination: List[str]  # 按键组合

    def __post_init__(self):
        if self.time_factor <= 0:
            raise ValueError("time_factor must be positive")


@dataclass
class RangeInfo:
    """音域信息"""

    min_height: float
    max_height: float
    span: float
    note_count: int

    @property
    def octaves(self) -> float:
        """音域跨度（八度）"""
        return self.span / 12.0


class MusicNotation:
    """音乐记谱法 - 相对音高定义"""

    # 相对音高映射 - 这些是简谱中的相对标记
    RELATIVE_HEIGHTS: Dict[str, float] = {
        # 休止符
        "0": None,
        # 低音区 (相对标记，相对于中音区-6.0半音)
        "l1": -6.0,
        "l2": -5.0,
        "l3": -4.0,
        "l4": -3.5,
        "l5": -2.5,
        "l6": -1.5,
        "l7": -0.5,
        # 中音区 (相对标记，以1为基准0)
        "1": 0,
        "2": 1,
        "3": 2,
        "4": 2.5,
        "5": 3.5,
        "6": 4.5,
        "7": 5.5,
        # 高音区 (相对标记)
        "h1": 6,
        "h2": 7,
        "h3": 8,
        "h4": 8.5,
        "h5": 9.5,
        "h6": 10.5,
        "h7": 11.5,
        # 超高音区 (可扩展)
        "h8": 12,
        "h9": 13,
        "h10": 14,
        "h11": 14.5,
        "h12": 15.5,
        "h13": 16.5,
        "h14": 17.5,
        "h15": 18,
        "h16": 19,
        "h17": 20,
    }

    @classmethod
    def initialize_half_tones(cls):
        """初始化半音音符"""
        # 为所有基础音符生成半音版本
        base_notes = {}
        for note, height in cls.RELATIVE_HEIGHTS.items():
            if height is not None and note != "0":
                base_notes[note] = height

        # 生成半音
        for note, height in base_notes.items():
            if not note.endswith(".5"):
                half_note = note + ".5"
                if half_note not in cls.RELATIVE_HEIGHTS:
                    cls.RELATIVE_HEIGHTS[half_note] = height + 0.5

    @classmethod
    def get_relative_height(cls, notation: str) -> Optional[float]:
        """获取音符的相对高度"""
        return cls.RELATIVE_HEIGHTS.get(notation)

    @classmethod
    def extend_range(cls, target_range: float):
        """根据需要扩展音域定义"""
        current_max = max(h for h in cls.RELATIVE_HEIGHTS.values() if h is not None)
        if target_range > current_max:
            # 自动扩展高音区
            needed = int(target_range - current_max) + 5
            for i in range(needed):
                new_height = current_max + i + 1
                new_note = f"h{int(new_height) + 6}"  # 简化命名
                cls.RELATIVE_HEIGHTS[new_note] = new_height


class FlutePhysical:
    """笛子物理特性 - 实际可演奏的音高和按键"""

    # 笛子物理音域 (实际可演奏的范围)
    MIN_PHYSICAL_HEIGHT = -6.0  # 1降八度 (1 + 按1键)
    MAX_PHYSICAL_HEIGHT = 6.5  # 1+高半音 (1+ + 按3键)
    PHYSICAL_RANGE = MAX_PHYSICAL_HEIGHT - MIN_PHYSICAL_HEIGHT

    # 基础按键映射 - 对应8个方向键
    BASE_KEY_MAPPING = {
        0: ["right"],  # 1音
        1: ["right", "down"],  # 2音
        2: ["down"],  # 3音
        2.5: ["left", "down"],  # 4音
        3.5: ["left"],  # 5音
        4.5: ["left", "up"],  # 6音
        5.5: ["up"],  # 7音
        6: ["right", "up"],  # h1音
    }

    @classmethod
    def get_key_combination(cls, physical_height: float) -> List[str]:
        """获取物理音高对应的按键组合"""
        # 生成完整的按键映射
        key_mapping = cls._generate_full_key_mapping()
        return key_mapping.get(physical_height, [])

    @classmethod
    def _generate_full_key_mapping(cls) -> Dict[float, List[str]]:
        """生成完整的按键映射表"""
        mapping = {}

        # 基础按键
        for height, keys in cls.BASE_KEY_MAPPING.items():
            mapping[height] = keys.copy()

        # 低音区 (添加"1"键) - 按1键降八度
        basic_notes = [0, 1, 2, 2.5, 3.5, 4.5, 5.5, 6]
        for note in basic_notes:  # 包括h1(1+)，因为1+降八度=1
            mapping[note - 6] = cls.BASE_KEY_MAPPING[note] + ["1"]

        # 半音 (添加"3"键)
        current_keys = list(mapping.keys())
        for note in current_keys:
            if note is not None and (note + 0.5) not in mapping:
                mapping[note + 0.5] = mapping[note] + ["3"]

        # 添加休止符
        mapping[None] = []

        return mapping

    @classmethod
    def is_playable(cls, physical_height: Optional[float]) -> bool:
        """检查物理音高是否可演奏"""
        if physical_height is None:
            return True  # 休止符总是可演奏
        return cls.MIN_PHYSICAL_HEIGHT <= physical_height <= cls.MAX_PHYSICAL_HEIGHT

    @classmethod
    def validate_range(cls, min_height: float, max_height: float) -> bool:
        """验证音域是否在笛子可演奏范围内"""
        return (
            cls.is_playable(min_height)
            and cls.is_playable(max_height)
            and (max_height - min_height) <= cls.PHYSICAL_RANGE
        )


# 初始化半音
MusicNotation.initialize_half_tones()


class RangeAnalyzer:
    """音域分析器"""

    @staticmethod
    def analyze_relative_notes(notes: List[RelativeNote]) -> RangeInfo:
        """分析相对音符的音域信息"""
        valid_heights = [
            note.relative_height for note in notes if note.relative_height is not None
        ]

        if not valid_heights:
            return RangeInfo(0, 0, 0, 0)

        min_height = min(valid_heights)
        max_height = max(valid_heights)
        span = max_height - min_height

        return RangeInfo(min_height, max_height, span, len(valid_heights))

    @staticmethod
    def analyze_physical_notes(notes: List[PhysicalNote]) -> RangeInfo:
        """分析物理音符的音域信息"""
        valid_heights = [
            note.physical_height for note in notes if note.physical_height is not None
        ]

        if not valid_heights:
            return RangeInfo(0, 0, 0, 0)

        min_height = min(valid_heights)
        max_height = max(valid_heights)
        span = max_height - min_height

        return RangeInfo(min_height, max_height, span, len(valid_heights))
