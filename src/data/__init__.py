"""数据模块 - 包含乐曲数据和配置管理"""

from .music_theory import *
from .songs import *

__all__ = ["MusicNotation", "FlutePhysical", "RelativeNote", "PhysicalNote", "SongManager"]