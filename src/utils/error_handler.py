"""统一的错误处理和用户反馈逻辑"""

import traceback
from typing import Optional, Callable, Any, Dict
from functools import wraps
from .logger import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """统一错误处理器 - 减少重复的错误处理逻辑"""

    @staticmethod
    def handle_song_not_found(
        song_name: str,
        available_songs: Optional[list] = None,
        show_suggestions: bool = True,
    ) -> str:
        """
        处理歌曲未找到错误

        Args:
            song_name: 歌曲名称
            available_songs: 可用歌曲列表
            show_suggestions: 是否显示建议

        Returns:
            格式化的错误消息
        """
        error_msg = f"❌ 乐曲 '{song_name}' 不存在"

        if show_suggestions and available_songs:
            if len(available_songs) <= 5:
                suggestion = f"📋 可用乐曲: {', '.join(available_songs)}"
            else:
                suggestion = f"📋 可用乐曲: {', '.join(available_songs[:5])} (等{len(available_songs)}首)"
            error_msg += f"\n{suggestion}"

        return error_msg

    @staticmethod
    def handle_generic_error(
        error: Exception, operation: str = "操作", show_traceback: bool = False
    ) -> str:
        """
        处理通用错误

        Args:
            error: 异常对象
            operation: 操作描述
            show_traceback: 是否显示详细堆栈信息

        Returns:
            格式化的错误消息
        """
        error_msg = f"❌ {operation}失败: {error}"

        logger.error(f"{operation} failed: {error}")

        if show_traceback:
            logger.debug(f"Traceback: {traceback.format_exc()}")
            error_msg += f"\n💥 详细错误: {traceback.format_exc()}"

        return error_msg

    @staticmethod
    def handle_validation_error(
        validation_errors: list, context: str = "数据验证"
    ) -> str:
        """
        处理验证错误

        Args:
            validation_errors: 验证错误列表
            context: 验证上下文

        Returns:
            格式化的错误消息
        """
        error_count = len(validation_errors)
        error_msg = f"❌ {context}失败 ({error_count} 个错误):"

        # 只显示前3个错误，避免输出过长
        for i, error in enumerate(validation_errors[:3]):
            error_msg += f"\n   • {error}"

        if error_count > 3:
            error_msg += f"\n   • ... 还有 {error_count - 3} 个错误"

        return error_msg

    @staticmethod
    def create_success_message(operation: str, details: Optional[str] = None) -> str:
        """
        创建成功消息

        Args:
            operation: 操作描述
            details: 详细信息

        Returns:
            格式化的成功消息
        """
        msg = f"✅ {operation}成功"
        if details:
            msg += f": {details}"
        return msg

    @staticmethod
    def create_warning_message(operation: str, warning: str) -> str:
        """
        创建警告消息

        Args:
            operation: 操作描述
            warning: 警告内容

        Returns:
            格式化的警告消息
        """
        return f"⚠️ {operation}完成（有警告）: {warning}"


def with_error_handling(
    operation_name: str = "操作",
    return_on_error: Any = False,
    show_traceback: bool = False,
):
    """
    错误处理装饰器

    Args:
        operation_name: 操作名称
        return_on_error: 发生错误时的返回值
        show_traceback: 是否显示堆栈跟踪
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = ErrorHandler.handle_generic_error(
                    e, operation_name, show_traceback
                )
                print(error_msg)
                return return_on_error

        return wrapper

    return decorator


class UserFeedback:
    """用户反馈处理器 - 统一的用户交互反馈"""

    @staticmethod
    def print_operation_start(operation: str, details: Optional[str] = None) -> None:
        """打印操作开始信息"""
        msg = f"🔄 开始{operation}"
        if details:
            msg += f": {details}"
        print(msg)

    @staticmethod
    def print_operation_complete(operation: str, success: bool = True) -> None:
        """打印操作完成信息"""
        if success:
            print(f"✅ {operation}完成")
        else:
            print(f"❌ {operation}失败")

    @staticmethod
    def print_progress(message: str, current: int = None, total: int = None) -> None:
        """打印进度信息"""
        if current is not None and total is not None:
            print(f"📊 {message} ({current}/{total})")
        else:
            print(f"📊 {message}")

    @staticmethod
    def print_info_block(title: str, info_dict: Dict[str, Any]) -> None:
        """打印信息块"""
        print(f"\n📋 {title}:")
        for key, value in info_dict.items():
            print(f"   {key}: {value}")

    @staticmethod
    def print_separator(char: str = "=", length: int = 50) -> None:
        """打印分隔线"""
        print(char * length)


# 全局实例
error_handler = ErrorHandler()
user_feedback = UserFeedback()
