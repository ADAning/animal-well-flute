"""日志系统"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取配置好的日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 设置日志级别
    logger.setLevel(getattr(logging, level.upper()))

    # 不添加处理器，让日志器继承根日志器的配置
    return logger


def setup_logging(level: str = "INFO", tui_mode: bool = False) -> None:
    """设置全局日志配置

    Args:
        level: 日志级别
        tui_mode: 是否为TUI模式，如果是则不输出到控制台
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    
    # 强制清除所有现有的处理器
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    
    # 也清除所有子日志器的处理器
    for name in logging.Logger.manager.loggerDict:
        logger_instance = logging.getLogger(name)
        for handler in logger_instance.handlers[:]:
            handler.close()
            logger_instance.removeHandler(handler)
    
    # 设置日志级别
    root_logger.setLevel(getattr(logging, level.upper()))
    
    if tui_mode:
        # TUI模式：完全禁用日志输出到控制台
        # 设置非常高的日志级别，基本禁用所有日志
        root_logger.setLevel(logging.CRITICAL)
        
        # 使用NullHandler完全静默
        null_handler = logging.NullHandler()
        root_logger.addHandler(null_handler)
        
        # 强制所有现有的logger也使用这个配置
        for name in logging.Logger.manager.loggerDict:
            logger_instance = logging.getLogger(name)
            logger_instance.setLevel(logging.CRITICAL)
            logger_instance.propagate = False  # 阻止传播到父logger
        
        # 可选：如果需要调试，可以同时输出到文件（但设置更高的级别）
        try:
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / "tui.log", encoding='utf-8')
            file_handler.setLevel(logging.ERROR)  # 只记录错误
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception:
            pass  # 如果文件创建失败，只使用NullHandler
    else:
        # CLI模式：正常输出到控制台
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    
    # 禁用 logging.basicConfig() 的后续调用
    logging.root.handlers = root_logger.handlers
