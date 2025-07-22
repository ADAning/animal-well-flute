"""简谱解析器 - 从SongManager中提取的解析逻辑"""

from typing import List, Any, Union
from .token_parser import TokenParser, TokenValidator
from ...utils.logger import get_logger

logger = get_logger(__name__)


class JianpuParser:
    """简谱解析器 - 处理各种格式的简谱数据解析"""

    def __init__(self):
        self.token_parser = TokenParser()
        self.validator = TokenValidator()

    def parse_unified_jianpu(
        self, jianpu_data: Union[List[List[str]], List[str]]
    ) -> List[List[Any]]:
        """
        统一解析字符串化和简化格式的简谱数据

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
                parsed_bars = self._parse_bar_string_with_separator(bar_str)
                parsed_jianpu.extend(parsed_bars)
        else:
            # 简化格式：嵌套列表，每个音符都是字符串
            for bar in jianpu_data:
                parsed_bar = []
                for note in bar:
                    if isinstance(note, str):
                        parsed_bar.append(self.token_parser.parse_note_token(note))
                    else:
                        parsed_bar.append(note)
                parsed_jianpu.append(parsed_bar)

        return parsed_jianpu

    def _parse_bar_string_with_separator(self, bar_str: str) -> List[List[Any]]:
        """
        解析可能包含分隔符的小节字符串

        Args:
            bar_str: 可能包含|分隔符的小节字符串

        Returns:
            解析后的小节列表
        """
        parsed_bars = []

        # 检查是否包含|分割符
        if "|" in bar_str:
            # 多小节用|分割
            sub_bars = bar_str.split("|")
            for sub_bar_str in sub_bars:
                sub_bar_str = sub_bar_str.strip()
                if sub_bar_str:  # 跳过空字符串
                    parsed_bar = self._parse_single_bar_string(sub_bar_str)
                    parsed_bars.append(parsed_bar)
        else:
            # 单小节
            parsed_bar = self._parse_single_bar_string(bar_str)
            parsed_bars.append(parsed_bar)

        return parsed_bars

    def _parse_single_bar_string(self, bar_str: str) -> List[Any]:
        """
        解析单个小节字符串

        Args:
            bar_str: 小节字符串，如 "0 0 (0,3) (3,4)"

        Returns:
            解析后的小节数据
        """
        notes = []
        tokens = self.token_parser.tokenize_bar_string(bar_str)

        for token in tokens:
            notes.append(self.token_parser.parse_note_token(token))

        return notes

    def detect_jianpu_format(self, data: dict) -> str:
        """
        检测简谱文件的格式类型

        Args:
            data: 从文件加载的数据

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

    def convert_to_string_format(self, jianpu: List[List[Any]]) -> List[str]:
        """
        将简谱数据转换为字符串化格式

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
        """
        将音符转换为字符串格式

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
