"""Token解析器 - 处理复杂的token解析和验证逻辑"""

import re
from typing import List, Any, Union
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TokenValidator:
    """Token验证器 - 统一token格式验证逻辑"""

    @staticmethod
    def is_valid_basic_token(token: str) -> bool:
        """
        验证基本token（非括号格式）

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
        valid_patterns = [
            r"^[lh]?\d+(\.\d+)?d?$",  # 标准音符格式，如 l1, h2, 1.5d
            r"^-+$",  # 延长音符号
            r"^0+$",  # 休止符
        ]

        for pattern in valid_patterns:
            if re.match(pattern, token):
                return True

        return False

    @staticmethod
    def is_balanced_parentheses(token: str) -> bool:
        """
        检查括号是否平衡

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

    @staticmethod
    def is_valid_note_string(note_str: str) -> bool:
        """
        检查音符字符串是否有效

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

        for pattern in valid_patterns:
            if re.match(pattern, note_str):
                return True

        return False

    @classmethod
    def validate_token_structure(cls, token: str) -> bool:
        """
        递归验证token结构

        Args:
            token: 要验证的token

        Returns:
            是否有效
        """
        token = token.strip()

        # 如果不是括号格式，验证基本token
        if not token.startswith("(") or not token.endswith(")"):
            return cls.is_valid_basic_token(token)

        # 验证括号平衡
        if not cls.is_balanced_parentheses(token):
            return False

        # 去掉外层括号
        inner = token[1:-1]
        if not inner:
            return True  # 空括号是有效的

        # 分割并递归验证每个部分
        try:
            parts = TokenParser.split_by_space_smart(inner)
            for part in parts:
                part = part.strip()
                if part and not cls.validate_token_structure(part):
                    return False
            return True
        except Exception:
            return False


class TokenParser:
    """Token解析器 - 处理复杂的token解析逻辑"""

    @staticmethod
    def split_by_space_smart(text: str) -> List[str]:
        """
        智能按空格分割，考虑括号嵌套

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

    @staticmethod
    def tokenize_bar_string(bar_str: str) -> List[str]:
        """
        将小节字符串分词 - 按空格分割，保持括号完整性

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

    @classmethod
    def parse_basic_token(cls, token: str) -> Any:
        """
        解析基本token - 数字或字符串

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

    @classmethod
    def parse_token_recursive(cls, token: str) -> Any:
        """
        递归解析token - 统一处理括号和基本token

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
            parts = cls.split_by_space_smart(inner)
            parsed_parts = []

            for part in parts:
                part = part.strip()
                if part:
                    parsed_parts.append(cls.parse_token_recursive(part))

            # 返回适当的元组格式
            return (
                tuple(parsed_parts)
                if len(parsed_parts) > 1
                else (parsed_parts[0],) if parsed_parts else ()
            )

        # 处理基本token（数字或字符串）
        return cls.parse_basic_token(token)

    @classmethod
    def parse_note_token(cls, token: str) -> Any:
        """
        统一的token解析器 - 处理所有类型的音符token

        Args:
            token: 音符token，如 "3", "(3 4)", "h1", "(l5 (1 2))" 等

        Returns:
            解析后的音符数据：数字、字符串或元组
        """
        return cls.parse_token_recursive(token.strip())

    @classmethod
    def is_valid_note_token(cls, token: str) -> bool:
        """
        检查音符token是否有效

        Args:
            token: 音符token

        Returns:
            是否有效
        """
        token = token.strip()
        if not token:
            return False

        # 递归验证token结构
        return TokenValidator.validate_token_structure(token)
