"""应用配置管理系统 - 集中管理所有硬编码值"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
import os
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AppConfig:
    """应用配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        # 音乐相关
        "music": {
            "default_bpm": 90,
            "default_offset": 0.0,
            "default_ready_time": 5,
            "beat_interval_calculation": "60.0 / bpm"
        },
        
        # 文件路径相关
        "paths": {
            "songs_dir": "songs",
            "sheets_dir": "sheets",
            "backup_dir": "backup",
            "temp_dir": "temp"
        },
        
        # 图片处理相关
        "image_processing": {
            "max_image_size": 2048,
            "split_threshold": 1500,
            "jpeg_quality": 85,
            "supported_extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]
        },
        
        # AI服务相关
        "ai_services": {
            "default_provider": None,  # 自动选择第一个可用的
            "retry_count": 3,
            "timeout_seconds": 30
        },
        
        # 日志相关
        "logging": {
            "default_level": "INFO",
            "log_to_file": False,
            "log_file_path": "logs/app.log"
        },
        
        # 验证相关
        "validation": {
            "max_validation_errors_display": 3,
            "strict_mode": False
        },
        
        # 性能相关
        "performance": {
            "enable_caching": True,
            "cache_expiry_minutes": 30,
            "max_cache_size_mb": 100
        }
    }
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config.json")
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()
        self._load_env_overrides()
    
    def _load_config(self) -> None:
        """从配置文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self._merge_config(self.config, user_config)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
                logger.info("Using default configuration")
    
    def _load_env_overrides(self) -> None:
        """从环境变量加载覆盖配置"""
        env_mappings = {
            "ANIMAL_WELL_DEFAULT_BPM": ("music", "default_bpm", int),
            "ANIMAL_WELL_READY_TIME": ("music", "default_ready_time", int),
            "ANIMAL_WELL_SONGS_DIR": ("paths", "songs_dir", str),
            "ANIMAL_WELL_LOG_LEVEL": ("logging", "default_level", str),
            "ANIMAL_WELL_ENABLE_CACHE": ("performance", "enable_caching", bool),
            "ANIMAL_WELL_MAX_IMAGE_SIZE": ("image_processing", "max_image_size", int),
        }
        
        for env_key, (section, key, value_type) in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                try:
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        converted_value = value_type(env_value)
                    
                    if section not in self.config:
                        self.config[section] = {}
                    self.config[section][key] = converted_value
                    logger.debug(f"Override from env {env_key}: {section}.{key} = {converted_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable {env_key}={env_value}: {e}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            section: 配置段名
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(section, {}).get(key, default)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置段
        
        Args:
            section: 配置段名
            
        Returns:
            配置段字典
        """
        return self.config.get(section, {})
    
    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            section: 配置段名
            key: 配置键名
            value: 配置值
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        logger.debug(f"Set config {section}.{key} = {value}")
    
    def save_config(self, file_path: Optional[Path] = None) -> None:
        """保存配置到文件
        
        Args:
            file_path: 保存路径，为None时使用默认路径
        """
        save_path = file_path or self.config_file
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {save_path}: {e}")
    
    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults")
    
    def get_paths(self) -> Dict[str, Path]:
        """获取所有路径配置
        
        Returns:
            路径配置字典，值为Path对象
        """
        paths = {}
        for key, value in self.get_section("paths").items():
            paths[key] = Path(value)
        return paths
    
    # 便捷访问方法
    @property
    def default_bpm(self) -> int:
        """默认BPM"""
        return self.get("music", "default_bpm", 90)
    
    @property
    def default_ready_time(self) -> int:
        """默认准备时间"""
        return self.get("music", "default_ready_time", 5)
    
    @property
    def songs_dir(self) -> Path:
        """歌曲目录路径"""
        return Path(self.get("paths", "songs_dir", "songs"))
    
    @property
    def max_image_size(self) -> int:
        """最大图片尺寸"""
        return self.get("image_processing", "max_image_size", 2048)
    
    @property
    def supported_image_extensions(self) -> list:
        """支持的图片扩展名"""
        return self.get("image_processing", "supported_extensions", [".png", ".jpg", ".jpeg"])
    
    @property
    def enable_caching(self) -> bool:
        """是否启用缓存"""
        return self.get("performance", "enable_caching", True)
    
    @property
    def log_level(self) -> str:
        """日志级别"""
        return self.get("logging", "default_level", "INFO")


# 全局配置实例
_app_config: Optional[AppConfig] = None


def get_app_config() -> AppConfig:
    """获取全局应用配置实例"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


def reload_config(config_file: Optional[Path] = None) -> AppConfig:
    """重新加载配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        新的配置实例
    """
    global _app_config
    _app_config = AppConfig(config_file)
    return _app_config