"""乐曲管理器"""

from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import json
import yaml
import re

from .sample_songs import Song
from .sample_songs import get_sample_songs
from ...utils.exceptions import SongNotFoundError
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongManager:
    """乐曲管理器 - 负责加载和管理乐曲数据"""

    def __init__(self, songs_dir: Optional[Path] = None):
        self.songs_dir = songs_dir or Path("songs")
        self.songs: Dict[str, Song] = {}  # key -> Song
        self.name_to_key: Dict[str, str] = {}  # name -> key 映射
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

                # 检测并处理不同的YAML格式
                format_type = self._detect_yaml_format(data)

                if format_type == "string_based":
                    # 统一处理所有基于字符串的格式
                    logger.debug(f"Detected string-based format in {file_path}")
                    data["jianpu"] = self._parse_unified_jianpu(data["jianpu"])
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

    def _parse_unified_jianpu(
        self, jianpu_data: Union[List[List[str]], List[str]]
    ) -> List[List[Any]]:
        """统一解析字符串化和简化格式的简谱数据

        Args:
            jianpu_data: 简谱数据（字符串列表或嵌套字符串列表）

        Returns:
            解析后的简谱数据
        """
        parsed_jianpu = []

        # 检查是否为字符串化格式（每小节一个字符串）
        if jianpu_data and isinstance(jianpu_data[0], str):
            # 字符串化格式：每小节一个字符串或多小节用|分割
            for bar_str in jianpu_data:
                # 检查是否包含|分割符
                if "|" in bar_str:
                    # 多小节用|分割
                    sub_bars = bar_str.split("|")
                    for sub_bar_str in sub_bars:
                        sub_bar_str = sub_bar_str.strip()
                        if sub_bar_str:  # 跳过空字符串
                            parsed_bar = self._parse_bar_string(sub_bar_str)
                            parsed_jianpu.append(parsed_bar)
                else:
                    # 单小节
                    parsed_bar = self._parse_bar_string(bar_str)
                    parsed_jianpu.append(parsed_bar)
        else:
            # 简化格式：嵌套列表，每个音符都是字符串
            for bar in jianpu_data:
                parsed_bar = []
                for note in bar:
                    if isinstance(note, str):
                        parsed_bar.append(self._parse_note_token(note))
                    else:
                        parsed_bar.append(note)
                parsed_jianpu.append(parsed_bar)

        return parsed_jianpu

    def _parse_bar_string(self, bar_str: str) -> List[Any]:
        """解析小节字符串

        Args:
            bar_str: 小节字符串，如 "0 0 (0,3) (3,4)"

        Returns:
            解析后的小节数据
        """
        notes = []
        tokens = self._tokenize_bar_string(bar_str)

        for token in tokens:
            notes.append(self._parse_note_token(token))

        return notes

    def _tokenize_bar_string(self, bar_str: str) -> List[str]:
        """将小节字符串分词 - 按空格分割，保持括号完整性

        Args:
            bar_str: 小节字符串，如 "0 0 (0 3) (3 4)"

        Returns:
            分词后的列表，如 ["0", "0", "(0 3)", "(3 4)"]
        """
        tokens = []
        current_token = ""
        bracket_count = 0

        for char in bar_str:
            if char == "(":
                bracket_count += 1
                current_token += char
            elif char == ")":
                bracket_count -= 1
                current_token += char
            elif char.isspace() and bracket_count == 0:
                # 只在括号外的空格处分割
                if current_token.strip():
                    tokens.append(current_token.strip())
                    current_token = ""
            else:
                current_token += char

        # 处理最后的token
        if current_token.strip():
            tokens.append(current_token.strip())

        return tokens

    def _parse_note_token(self, token: str) -> Any:
        """统一的token解析器 - 处理所有类型的音符token

        Args:
            token: 音符token，如 "3", "(3 4)", "h1", "(l5 (1 2))" 等

        Returns:
            解析后的音符数据：数字、字符串或元组
        """
        return self._parse_token_recursive(token.strip())

    def _parse_token_recursive(self, token: str) -> Any:
        """递归解析token - 统一处理括号和基本token

        Args:
            token: 要解析的token

        Returns:
            解析后的数据
        """
        if not token:
            return ""

        # 处理括号表达式
        if token.startswith("(") and token.endswith(")"):
            inner = token[1:-1].strip()
            if not inner:
                return ()

            # 智能分割并递归解析
            parts = self._split_by_space_smart(inner)
            parsed_parts = []

            for part in parts:
                part = part.strip()
                if part:
                    parsed_parts.append(self._parse_token_recursive(part))

            # 返回适当的元组格式
            return (
                tuple(parsed_parts)
                if len(parsed_parts) > 1
                else (parsed_parts[0],) if parsed_parts else ()
            )

        # 处理基本token（数字或字符串）
        return self._parse_basic_token(token)

    def _parse_basic_token(self, token: str) -> Any:
        """解析基本token - 数字或字符串

        Args:
            token: 基本token如 "3", "h1", "5d", "-" 等

        Returns:
            int, float 或 str
        """
        # 尝试解析为数字
        try:
            return float(token) if "." in token else int(token)
        except ValueError:
            # 不是数字，返回字符串
            return token

    def _detect_yaml_format(self, data: Dict) -> str:
        """检测YAML文件的格式类型

        Args:
            data: 从YAML文件加载的数据

        Returns:
            格式类型：'string_based', 'legacy', 'unknown'
        """
        if "jianpu" not in data:
            return "unknown"

        jianpu = data["jianpu"]
        if not isinstance(jianpu, list) or not jianpu:
            return "unknown"

        # 检查是否为字符串化格式（每小节一个字符串）
        if jianpu and isinstance(jianpu[0], str):
            return "string_based"

        # 检查是否为简化格式（嵌套列表，每个音符都是字符串）
        if isinstance(jianpu[0], list):
            # 检查前几个音符是否都是字符串
            sample_notes = []
            for bar in jianpu[:2]:  # 检查前2个小节
                if isinstance(bar, list):
                    sample_notes.extend(bar[:3])  # 每小节取前3个音符

            # 如果样本音符都是字符串，认为是string_based格式
            if sample_notes and all(isinstance(note, str) for note in sample_notes):
                return "string_based"

        # 默认返回legacy格式
        return "legacy"

    def _convert_to_simplified_format(self, jianpu: List[List[Any]]) -> List[str]:
        """将简谱数据转换为字符串化格式

        Args:
            jianpu: 原始简谱数据

        Returns:
            字符串化格式的简谱数据（每小节一个字符串）
        """
        simplified_jianpu = []

        for bar in jianpu:
            bar_notes = []
            for note in bar:
                bar_notes.append(self._note_to_string(note, "unified"))
            simplified_jianpu.append(" ".join(bar_notes))

        return simplified_jianpu

    def _note_to_string(self, note: Any, format_style: str = "unified") -> str:
        """将音符转换为字符串格式

        Args:
            note: 音符数据（可以是字符串、数字、元组等）
            format_style: 格式化风格 ("unified" 或 "legacy")

        Returns:
            字符串格式的音符
        """
        if isinstance(note, str):
            if format_style == "unified":
                # 统一格式：简单音符不需要括号，复杂的加括号
                if (
                    note in ["-", "0"]
                    or note.isdigit()
                    or any(c in note for c in ["h", "l", "d"])
                ):
                    return note
                else:
                    return f"({note})"
            else:
                return note

        elif isinstance(note, (int, float)):
            return str(note)

        elif isinstance(note, tuple):
            # 递归转换每个元素
            parts = [self._note_to_string(part, format_style) for part in note]

            if format_style == "unified":
                # 统一格式：所有元组都用括号包围，用逗号分隔
                return f"({','.join(parts)})"
            else:
                # 传统格式：保持原有逻辑
                if len(parts) == 1:
                    return f"({parts[0]})"

                # 如果元组中包含其他元组，需要使用括号
                if any(" " in part and "(" in part for part in parts):
                    formatted_parts = []
                    for part in parts:
                        if " " in part and "(" in part:
                            formatted_parts.append(f"({part})")
                        else:
                            formatted_parts.append(part)
                    return " ".join(formatted_parts)
                else:
                    return " ".join(parts)
        else:
            return str(note)

    def save_song_simplified(self, song: Song, file_path: Path) -> None:
        """保存乐曲为字符串化格式的YAML文件

        Args:
            song: 乐曲对象
            file_path: 文件路径
        """
        # 转换为字符串化格式
        stringified_jianpu = self._convert_to_simplified_format(song.jianpu)

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
                    format_type = self._detect_yaml_format(data)
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
                            tokens = self._tokenize_bar_string(sub_bar_str)
                            for j, token in enumerate(tokens):
                                if not self._is_valid_note_token(token):
                                    errors.append(
                                        f"Bar {i+1}.{k+1}, Note {j+1}: Invalid token '{token}'"
                                    )
                        except Exception as e:
                            errors.append(f"Bar {i+1}.{k+1}: Failed to parse - {e}")
                else:
                    # 单小节
                    try:
                        tokens = self._tokenize_bar_string(bar_str)
                        for j, token in enumerate(tokens):
                            if not self._is_valid_note_token(token):
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

    def _is_valid_note_token(self, token: str) -> bool:
        """检查音符token是否有效

        Args:
            token: 音符token

        Returns:
            是否有效
        """
        token = token.strip()
        if not token:
            return False

        # 递归验证token结构
        return self._validate_token_structure(token)

    def _validate_token_structure(self, token: str) -> bool:
        """递归验证token结构

        Args:
            token: 要验证的token

        Returns:
            是否有效
        """
        token = token.strip()

        # 如果不是括号格式，验证基本token
        if not token.startswith("(") or not token.endswith(")"):
            return self._is_valid_basic_token(token)

        # 验证括号平衡
        if not self._is_balanced_parentheses(token):
            return False

        # 去掉外层括号
        inner = token[1:-1]
        if not inner:
            return True  # 空括号是有效的

        # 分割并递归验证每个部分
        try:
            parts = self._split_by_space_smart(inner)
            for part in parts:
                part = part.strip()
                if part and not self._validate_token_structure(part):
                    return False
            return True
        except:
            return False

    def _is_valid_basic_token(self, token: str) -> bool:
        """验证基本token（非括号格式）

        Args:
            token: 基本token

        Returns:
            是否有效
        """
        token = token.strip()

        # 简单音符：数字、浮点数、休止符、特殊标记
        if (
            token.isdigit()
            or token in ["-", "0"]
            or any(c in token for c in ["h", "l", "d"])
        ):
            return True

        # 检查是否为浮点数（半音）
        try:
            float(token)
            return True
        except ValueError:
            pass

        # 检查是否为有效的音符字符串格式
        import re

        valid_patterns = [
            r"^[lh]?\d+(\.\d+)?d?$",  # 标准音符格式，如 l1, h2, 1.5d
            r"^-+$",  # 延长音符号
            r"^0+$",  # 休止符
        ]

        for pattern in valid_patterns:
            if re.match(pattern, token):
                return True

        return False

    def _is_balanced_parentheses(self, token: str) -> bool:
        """检查括号是否平衡

        Args:
            token: 要检查的字符串

        Returns:
            括号是否平衡
        """
        count = 0
        for char in token:
            if char == "(":
                count += 1
            elif char == ")":
                count -= 1
                if count < 0:
                    return False
        return count == 0

    def _split_by_space_smart(self, text: str) -> List[str]:
        """智能按空格分割，考虑括号嵌套

        Args:
            text: 要分割的文本

        Returns:
            分割后的部分列表
        """
        parts = []
        current_part = ""
        bracket_count = 0

        for char in text:
            if char == "(":
                bracket_count += 1
                current_part += char
            elif char == ")":
                bracket_count -= 1
                current_part += char
            elif char == " " and bracket_count == 0:
                # 只在顶级空格处分割
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char

        # 添加最后一部分
        if current_part.strip():
            parts.append(current_part.strip())

        return parts

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
            if not self._is_valid_note_string(note):
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

    def _is_valid_note_string(self, note_str: str) -> bool:
        """检查音符字符串是否有效

        Args:
            note_str: 音符字符串

        Returns:
            是否有效
        """
        # 允许的基本音符格式
        valid_patterns = [
            r"^-$",  # 休止符
            r"^\d+$",  # 数字音符
            r"^\d+\.\d+$",  # 浮点数音符（半音）
            r"^[lh]\d+$",  # 低音(l)或高音(h)
            r"^[lh]\d+\.\d+$",  # 低音/高音的浮点数
            r"^\d+d$",  # 带d的音符
            r"^\d+\.\d+d$",  # 带d的浮点数音符
            r"^[\d\. ()lh-]+$",  # 复合格式（空格、括号等，包含小数点）
        ]

        import re

        for pattern in valid_patterns:
            if re.match(pattern, note_str):
                return True

        return False

    def _is_valid_note_number(self, note_num: Union[int, float]) -> bool:
        """检查音符数字是否有效

        Args:
            note_num: 音符数字

        Returns:
            是否有效
        """
        # 通常音符范围在0-7之间，但允许一些扩展
        return isinstance(note_num, (int, float)) and -10 <= note_num <= 20
