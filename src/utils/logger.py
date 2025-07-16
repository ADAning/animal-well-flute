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


def setup_logging(level: str = "INFO") -> None:
    """设置全局日志配置
    
    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )