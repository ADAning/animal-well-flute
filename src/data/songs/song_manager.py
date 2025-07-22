"""乐曲管理器"""

from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import json
import yaml
import re

from .sample_songs import Song
from .sample_songs import get_sample_songs
from ..parsers import JianpuParser, TokenValidator
from ...utils.exceptions import SongNotFoundError
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongManager:
    """乐曲管理器 - 负责加载和管理乐曲数据"""

    def __init__(self, songs_dir: Optional[Path] = None):
        self.songs_dir = songs_dir or Path("songs")
        self.songs: Dict[str, Song] = {}  # key -> Song
        self.name_to_key: Dict[str, str] = {}  # name -> key 映射

        # 初始化解析器
        self.jianpu_parser = JianpuParser()

        self._load_songs()

    def _load_songs(self) -> None:
        """加载所有乐曲数据"""
        # 加载内置示例乐曲
        sample_songs = get_sample_songs()
        self.songs.update(sample_songs)
        # 为示例歌曲添加name到key的映射
        for key, song in sample_songs.items():
            self.name_to_key[song.name] = key
        logger.info(f"Loaded {len(sample_songs)} sample songs")

        # 加载外部乐曲文件
        if self.songs_dir.exists():
            self._load_external_songs()

    def _load_external_songs(self) -> None:
        """加载外部乐曲文件"""
        external_count = 0

        for file_path in self.songs_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    # 对于legacy格式，使用unsafe_load来处理Python类型
                    data = yaml.unsafe_load(f)

                # 验证数据完整性
                validation_errors = self.validate_song_data(data)
                if validation_errors:
                    logger.error(f"Validation errors in {file_path}:")
                    for error in validation_errors:
                        logger.error(f"  - {error}")
                    continue

                # 使用新的解析器处理不同的YAML格式
                format_type = self.jianpu_parser.detect_jianpu_format(data)

                if format_type == "string_based":
                    # 统一处理所有基于字符串的格式
                    logger.debug(f"Detected string-based format in {file_path}")
                    data["jianpu"] = self.jianpu_parser.parse_unified_jianpu(
                        data["jianpu"]
                    )
                elif format_type == "legacy":
                    # legacy格式直接使用，yaml.unsafe_load已经处理了Python类型
                    logger.debug(f"Detected legacy format in {file_path}")
                else:
                    logger.warning(
                        f"Unknown YAML format in {file_path}, attempting legacy parsing"
                    )

                song = Song(**data)
                key = song.name.lower().replace(" ", "_")
                self.songs[key] = song
                self.name_to_key[song.name] = key  # 添加name到key的映射
                external_count += 1
                logger.debug(f"Loaded external song: {song.name}")

            except Exception as e:
                logger.error(f"Error loading song from {file_path}: {e}")

        for file_path in self.songs_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    song = Song(**data)
                    key = song.name.lower().replace(" ", "_")
                    self.songs[key] = song
                    self.name_to_key[song.name] = key  # 添加name到key的映射
                    external_count += 1
                    logger.debug(f"Loaded external song: {song.name}")
            except Exception as e:
                logger.error(f"Error loading song from {file_path}: {e}")

        if external_count > 0:
            logger.info(f"Loaded {external_count} external songs")

    def get_song(self, name: str) -> Song:
        """获取指定名称的乐曲

        Args:
            name: 乐曲名称或key

        Returns:
            Song: 乐曲对象

        Raises:
            SongNotFoundError: 乐曲未找到
        """
        # 首先尝试通过exact name匹配
        if name in self.name_to_key:
            key = self.name_to_key[name]
            return self.songs[key]

        # 如果没有找到，尝试通过key匹配（向后兼容）
        key = name.lower().replace(" ", "_")
        if key in self.songs:
            return self.songs[key]

        raise SongNotFoundError(f"Song '{name}' not found")

    def get_song_by_name(self, name: str) -> Song:
        """通过歌曲名称获取乐曲（精确匹配Name字段）

        Args:
            name: 歌曲的Name字段

        Returns:
            Song: 乐曲对象

        Raises:
            SongNotFoundError: 乐曲未找到
        """
        if name not in self.name_to_key:
            raise SongNotFoundError(f"Song with name '{name}' not found")

        key = self.name_to_key[name]
        return self.songs[key]

    def get_song_by_key(self, key: str) -> Song:
        """通过key获取乐曲

        Args:
            key: 乐曲key

        Returns:
            Song: 乐曲对象

        Raises:
            SongNotFoundError: 乐曲未找到
        """
        if key not in self.songs:
            raise SongNotFoundError(f"Song with key '{key}' not found")
        return self.songs[key]

    def list_songs(self) -> List[str]:
        """列出所有可用的乐曲key（向后兼容）"""
        return list(self.songs.keys())

    def list_song_names(self) -> List[str]:
        """列出所有歌曲的Name字段"""
        return list(self.name_to_key.keys())

    def list_songs_with_info(self) -> List[Dict[str, str]]:
        """列出所有歌曲的详细信息

        Returns:
            包含name, key, bpm, bars等信息的字典列表
        """
        songs_info = []
        for name, key in self.name_to_key.items():
            song = self.songs[key]
            bars_count = len(song.jianpu) if song.jianpu else 0
            songs_info.append(
                {
                    "name": song.name,
                    "key": key,
                    "bpm": str(song.bpm),
                    "description": song.description or "",
                    "bars": str(bars_count),
                }
            )
        return sorted(songs_info, key=lambda x: x["name"])

    def get_song_info(self, name: str) -> Dict:
        """获取乐曲信息

        Args:
            name: 乐曲名称

        Returns:
            Dict: 乐曲信息
        """
        song = self.get_song(name)
        return {
            "name": song.name,
            "bpm": song.bpm,
            "relative": song.offset,
            "description": song.description,
            "bars": len(song.jianpu),
        }

    def add_song(self, song: Song) -> None:
        """添加新乐曲

        Args:
            song: 乐曲对象
        """
        key = song.name.lower().replace(" ", "_")
        self.songs[key] = song
        self.name_to_key[song.name] = key  # 添加name到key的映射
        logger.info(f"Added song: {song.name}")

    def save_song(self, song: Song, file_path: Path) -> None:
        """保存乐曲到文件

        Args:
            song: 乐曲对象
            file_path: 文件路径
        """
        data = {
            "name": song.name,
            "bpm": song.bpm,
            "jianpu": song.jianpu,
            "relative": song.offset,
            "description": song.description,
        }

        if file_path.suffix.lower() == ".yaml":
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved song '{song.name}' to {file_path}")

    def save_song_simplified(self, song: Song, file_path: Path) -> None:
        """保存乐曲为字符串化格式的YAML文件

        Args:
            song: 乐曲对象
            file_path: 文件路径
        """
        # 使用新的解析器转换为字符串化格式
        stringified_jianpu = self.jianpu_parser.convert_to_string_format(song.jianpu)

        data = {
            "name": song.name,
            "bpm": song.bpm,
            "jianpu": stringified_jianpu,
            "relative": song.offset,
            "description": song.description,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

        logger.info(f"Saved song '{song.name}' in stringified format to {file_path}")

    def convert_song_to_simplified(
        self, song_name: str, output_path: Optional[Path] = None
    ) -> bool:
        """将指定歌曲转换为简化格式并保存

        Args:
            song_name: 歌曲名称
            output_path: 输出路径，如果为None则覆盖原文件

        Returns:
            转换是否成功
        """
        try:
            song = self.get_song(song_name)

            if output_path is None:
                # 查找原始文件路径
                key = song_name.lower().replace(" ", "_")
                original_file = None

                for file_path in self.songs_dir.glob("*.yaml"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            # 对于legacy格式，使用unsafe_load来处理Python类型
                            data = yaml.unsafe_load(f)
                            if data.get("name", "").lower().replace(" ", "_") == key:
                                original_file = file_path
                                break
                    except:
                        continue

                if original_file:
                    output_path = original_file
                else:
                    output_path = self.songs_dir / f"{key}_simplified.yaml"

            self.save_song_simplified(song, output_path)
            logger.info(f"Successfully converted '{song_name}' to simplified format")
            return True

        except Exception as e:
            logger.error(f"Failed to convert song '{song_name}': {e}")
            return False

    def convert_all_to_simplified(
        self, backup_dir: Optional[Path] = None
    ) -> Dict[str, bool]:
        """将所有歌曲转换为简化格式

        Args:
            backup_dir: 备份目录，如果提供则先备份原文件

        Returns:
            转换结果字典 {歌曲名: 是否成功}
        """
        results = {}

        if backup_dir and backup_dir.exists():
            logger.info(f"Backing up original files to {backup_dir}")
            for file_path in self.songs_dir.glob("*.yaml"):
                backup_path = backup_dir / file_path.name
                try:
                    import shutil

                    shutil.copy2(file_path, backup_path)
                except Exception as e:
                    logger.warning(f"Failed to backup {file_path}: {e}")

        for song_name in self.list_songs():
            results[song_name] = self.convert_song_to_simplified(song_name)

        success_count = sum(1 for success in results.values() if success)
        logger.info(
            f"Converted {success_count}/{len(results)} songs to simplified format"
        )

        return results

    def get_format_info(self) -> Dict[str, Any]:
        """获取当前加载歌曲的格式信息

        Returns:
            格式信息字典
        """
        format_info = {
            "total_songs": len(self.songs),
            "sample_songs": 0,
            "external_songs": 0,
            "format_types": {
                "stringified": 0,
                "simplified": 0,
                "legacy": 0,
                "unknown": 0,
            },
        }

        # 统计示例歌曲
        sample_songs = get_sample_songs()
        format_info["sample_songs"] = len(sample_songs)

        # 统计外部歌曲格式
        for file_path in self.songs_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    # 对于legacy格式，使用unsafe_load来处理Python类型
                    data = yaml.unsafe_load(f)
                    format_type = self.jianpu_parser.detect_jianpu_format(data)
                    format_info["format_types"][format_type] += 1
                    format_info["external_songs"] += 1
            except:
                format_info["format_types"]["unknown"] += 1

        return format_info

    def validate_song_data(self, data: Dict) -> List[str]:
        """验证歌曲数据的完整性和正确性

        Args:
            data: 歌曲数据字典

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 检查必需字段
        required_fields = ["name", "bpm", "jianpu"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # 验证name字段
        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                errors.append("Field 'name' must be a non-empty string")

        # 验证bpm字段
        if "bpm" in data:
            if not isinstance(data["bpm"], (int, float)) or data["bpm"] <= 0:
                errors.append("Field 'bpm' must be a positive number")

        # 验证relative字段
        if "offset" in data:
            if not isinstance(data["offset"], (int, float)):
                errors.append("Field 'offset' must be a number")

        # 验证description字段
        if "description" in data:
            if not isinstance(data["description"], str):
                errors.append("Field 'description' must be a string")

        # 验证jianpu字段
        if "jianpu" in data:
            jianpu_errors = self._validate_jianpu(data["jianpu"])
            errors.extend(jianpu_errors)

        return errors

    def _validate_jianpu(self, jianpu: Any) -> List[str]:
        """验证简谱数据的格式

        Args:
            jianpu: 简谱数据

        Returns:
            错误信息列表
        """
        errors = []

        if not isinstance(jianpu, list):
            errors.append("Field 'jianpu' must be a list")
            return errors

        if len(jianpu) == 0:
            errors.append("Field 'jianpu' cannot be empty")
            return errors

        # 检查是否为字符串化格式
        if jianpu and isinstance(jianpu[0], str):
            # 字符串化格式验证
            for i, bar_str in enumerate(jianpu):
                if not isinstance(bar_str, str):
                    errors.append(f"Bar {i+1} must be a string in stringified format")
                    continue

                if not bar_str.strip():
                    errors.append(f"Bar {i+1} cannot be empty")
                    continue

                # 验证字符串格式，支持|分割的多小节
                if "|" in bar_str:
                    # 多小节用|分割
                    sub_bars = bar_str.split("|")
                    for k, sub_bar_str in enumerate(sub_bars):
                        sub_bar_str = sub_bar_str.strip()
                        if not sub_bar_str:
                            continue  # 跳过空的子小节

                        try:
                            from ..parsers.token_parser import TokenParser

                            tokens = TokenParser.tokenize_bar_string(sub_bar_str)
                            for j, token in enumerate(tokens):
                                if not TokenParser.is_valid_note_token(token):
                                    errors.append(
                                        f"Bar {i+1}.{k+1}, Note {j+1}: Invalid token '{token}'"
                                    )
                        except Exception as e:
                            errors.append(f"Bar {i+1}.{k+1}: Failed to parse - {e}")
                else:
                    # 单小节
                    try:
                        from ..parsers.token_parser import TokenParser

                        tokens = TokenParser.tokenize_bar_string(bar_str)
                        for j, token in enumerate(tokens):
                            if not TokenParser.is_valid_note_token(token):
                                errors.append(
                                    f"Bar {i+1}, Note {j+1}: Invalid token '{token}'"
                                )
                    except Exception as e:
                        errors.append(f"Bar {i+1}: Failed to parse - {e}")
        else:
            # 传统格式验证
            for i, bar in enumerate(jianpu):
                if not isinstance(bar, list):
                    errors.append(f"Bar {i+1} must be a list")
                    continue

                if len(bar) == 0:
                    errors.append(f"Bar {i+1} cannot be empty")
                    continue

                for j, note in enumerate(bar):
                    note_errors = self._validate_note(note, i + 1, j + 1)
                    errors.extend(note_errors)

        return errors

    def _validate_note(self, note: Any, bar_num: int, note_num: int) -> List[str]:
        """验证单个音符的格式

        Args:
            note: 音符数据
            bar_num: 小节号
            note_num: 音符号

        Returns:
            错误信息列表
        """
        errors = []
        position = f"Bar {bar_num}, Note {note_num}"

        # 简化格式验证（字符串格式）
        if isinstance(note, str):
            if not TokenValidator.is_valid_note_string(note):
                errors.append(f"{position}: Invalid note string format '{note}'")

        # Legacy格式验证（元组、数字、字符串）
        elif isinstance(note, (int, float)):
            if not self._is_valid_note_number(note):
                errors.append(f"{position}: Invalid note number {note}")

        elif isinstance(note, tuple):
            for i, sub_note in enumerate(note):
                sub_errors = self._validate_note(sub_note, bar_num, f"{note_num}.{i+1}")
                errors.extend(sub_errors)

        else:
            errors.append(f"{position}: Unsupported note type {type(note)}")

        return errors

    def _is_valid_note_number(self, note_num: Union[int, float]) -> bool:
        """检查音符数字是否有效

        Args:
            note_num: 音符数字

        Returns:
            是否有效
        """
        # 通常音符范围在0-7之间，但允许一些扩展
        return isinstance(note_num, (int, float)) and -10 <= note_num <= 20
