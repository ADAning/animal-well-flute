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
        "simple_scale": Song(
            name="Simple Scale",
            bpm=120,
            description="简单音阶练习",
            jianpu=[
                [1, 2, 3, 4],
                [5, 6, 7, "h1"],
                ["h1", 7, 6, 5],
                [4, 3, 2, 1],
            ],
        ),
    }

    return songs
