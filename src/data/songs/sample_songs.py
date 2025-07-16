"""示例乐曲数据"""

from typing import Dict
from dataclasses import dataclass
from typing import Any

@dataclass
class Song:
    """乐曲数据类"""
    name: str
    bpm: int
    jianpu: Any
    description: str = ""
    offset: float = 0.0


def get_sample_songs() -> Dict[str, Song]:
    """获取示例乐曲数据"""
    
    songs = {
        
        "miss_you_every_day": Song(
            name="Miss You Every Day",
            bpm=72,
            description="想你的365天",
            jianpu=[
                ["h1", "-", (7, (7, "h1")), (7, (6, 5))],
                [(6, 3), 3, "-", "-"],
                ["h1", "-", (7, (7, "h1")), (7, (6, 5))],
                [(6, 5), 5, "-", "-"],
                ["h1", "-", (7, (7, "h1")), (7, (6, 5))],
                [(6, 5), (5, (3, 2)), (2, 1), 1],
                [1, (1, (2, 3)), (6, 5), (3, (2, 1))],
                [1, "-", "-", "-"],
            ]
        ),
        
        "a_dream": Song(
            name="A Dream",
            bpm=100,
            offset=0.5,
            description="梦一场",
            jianpu=[
                [0, 0, (0, 3), (3, 4)],
                [5, (3,), "5d", (0, 5)],
                [5, (3, 2), 2, (1, 1)],
                [("h1", 7), (6, 7), (6, 5), (5, 3)],
                [(6, 5), (3, 5), 0, (0, 5)],
                [(5, 4), (3, 4), 4, (0, 4)],
                [(3, 2), (2, 1), 1, ("l6", 1)],
                [(2, 2), (2, 3), (2, 3), (2, "l6"), 2, 0],
            ]
        ),
        
        "simple_scale": Song(
            name="Simple Scale",
            bpm=120,
            description="简单音阶练习",
            jianpu=[
                [1, 2, 3, 4],
                [5, 6, 7, "h1"],
                ["h1", 7, 6, 5],
                [4, 3, 2, 1],
            ]
        ),
    }
    
    return songs