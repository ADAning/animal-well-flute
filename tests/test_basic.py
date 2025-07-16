"""基本功能测试"""

import pytest
from src.core.parser import RelativeParser
from src.core.converter import AutoConverter
from src.data.music_theory import RelativeNote, PhysicalNote
from src.data.songs.sample_songs import get_sample_songs


def test_relative_note_creation():
    """测试相对音符创建"""
    note = RelativeNote(notation="1", time_factor=1.0, relative_height=0.0)
    assert note.notation == "1"
    assert note.time_factor == 1.0
    assert note.relative_height == 0.0


def test_physical_note_creation():
    """测试物理音符创建"""
    note = PhysicalNote(notation="1", time_factor=1.0, physical_height=60.0, key_combination=["z"])
    assert note.notation == "1"
    assert note.time_factor == 1.0
    assert note.physical_height == 60.0
    assert note.key_combination == ["z"]


def test_parser_simple():
    """测试解析器基本功能"""
    parser = RelativeParser()
    jianpu = [[1, 2, 3, 4], [5, 6, 7, "h1"]]
    
    result = parser.parse(jianpu)
    assert len(result) == 2
    assert len(result[0]) == 4
    assert len(result[1]) == 4
    
    # 检查第一个音符
    assert result[0][0].notation == "1"
    assert result[0][0].time_factor == 1.0


def test_converter_basic():
    """测试转换器基本功能"""
    converter = AutoConverter()
    
    # 创建测试音符
    notes = [
        [RelativeNote(notation="1", time_factor=1.0, relative_height=0.0)],
        [RelativeNote(notation="2", time_factor=1.0, relative_height=2.0)],
        [RelativeNote(notation="0", time_factor=1.0, relative_height=None)],
    ]
    
    result = converter.convert_jianpu(notes, strategy="manual", manual_offset=1.0)
    
    assert len(result) == 3
    assert len(result[0]) == 1
    assert result[0][0].physical_height == 1.0  # 0.0 + 1.0
    assert result[1][0].physical_height == 3.0  # 2.0 + 1.0
    assert result[2][0].physical_height is None  # 休止符不变


def test_sample_songs():
    """测试示例乐曲"""
    songs = get_sample_songs()
    assert len(songs) > 0
    
    # 测试每首乐曲的基本属性
    for song_key, song in songs.items():
        assert isinstance(song.name, str)
        assert song.bpm > 0
        assert len(song.jianpu) > 0


def test_parser_with_rest():
    """测试解析器处理休止符"""
    parser = Parser()
    jianpu = [[1, 0, 2, "-"]]
    
    result = parser.parse(jianpu)
    assert len(result) == 1
    assert len(result[0]) == 3  # 延长音会合并到前一个音符
    
    assert result[0][0].note == "1"
    assert result[0][1].note == "0"
    assert result[0][2].note == "2"
    assert result[0][2].time_factor == 4.0  # 2.0 + 2.0 (延长音)


def test_parser_with_dotted_notes():
    """测试解析器处理附点音符"""
    parser = Parser()
    jianpu = [["1d", "2d"]]
    
    result = parser.parse(jianpu)
    assert len(result) == 1
    assert len(result[0]) == 2
    
    # 附点音符时值应该是1.5倍
    assert result[0][0].time_factor == 3.0  # 2.0 * 1.5
    assert result[0][1].time_factor == 3.0  # 2.0 * 1.5


if __name__ == "__main__":
    pytest.main([__file__])