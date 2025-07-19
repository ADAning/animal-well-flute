"""工具配置管理"""

import os
from typing import Dict, Optional, Any
from pathlib import Path
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class ToolsConfig:
    """工具模块配置管理"""
    
    # 支持的AI服务提供商
    SUPPORTED_PROVIDERS = {
        'gemini': {
            'name': 'Google Gemini 2.5 Flash',
            'env_key': 'GOOGLE_API_KEY',
            'model': 'gemini-2.5-flash',
            'base_url': None,
        },
        'doubao': {
            'name': 'Doubao Vision (豆包)',
            'env_key': 'ARK_API_KEY',
            'model': 'doubao-seed-1-6-250615',
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        },
    }
    
    # 默认配置
    DEFAULT_CONFIG = {
        'ai_provider': 'openai',  # 默认使用OpenAI
        'max_image_size': 2048,   # 最大图片尺寸(像素)
        'split_threshold': 1500,  # 超过此尺寸时进行分割
        'image_quality': 85,      # JPEG压缩质量
        'retry_attempts': 3,      # API调用重试次数
        'timeout': 30,            # API调用超时时间(秒)
    }
    
    def __init__(self, config_file: Optional[Path] = None):
        """初始化配置
        
        Args:
            config_file: 可选的配置文件路径
        """
        self.config_file = config_file or Path.home() / '.animal-well-flute' / 'tools_config.json'
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                self.config.update(file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save config file {self.config_file}: {e}")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取指定服务商的API密钥
        
        Args:
            provider: 服务商名称
            
        Returns:
            API密钥，如果未找到返回None
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            return None
        
        env_key = self.SUPPORTED_PROVIDERS[provider]['env_key']
        return os.getenv(env_key)
    
    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """获取指定服务商的配置
        
        Args:
            provider: 服务商名称
            
        Returns:
            服务商配置字典，如果不支持返回None
        """
        return self.SUPPORTED_PROVIDERS.get(provider)
    
    def validate_provider(self, provider: str) -> bool:
        """验证服务商配置是否有效
        
        Args:
            provider: 服务商名称
            
        Returns:
            配置是否有效
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            return False
        
        api_key = self.get_api_key(provider)
        return api_key is not None and len(api_key.strip()) > 0
    
    def get_available_providers(self) -> list:
        """获取可用的服务商列表
        
        Returns:
            可用服务商名称列表
        """
        available = []
        for provider in self.SUPPORTED_PROVIDERS:
            if self.validate_provider(provider):
                available.append(provider)
        return available
    
    def get_default_provider(self) -> str:
        """获取默认可用的服务商
        
        Returns:
            默认服务商名称，如果都不可用返回第一个
        """
        available = self.get_available_providers()
        if available:
            return available[0]
        return list(self.SUPPORTED_PROVIDERS.keys())[0]
    
    def update_config(self, **kwargs) -> None:
        """更新配置参数
        
        Args:
            **kwargs: 要更新的配置项
        """
        self.config.update(kwargs)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def list_providers_status(self) -> Dict[str, Dict[str, Any]]:
        """列出所有服务商的状态
        
        Returns:
            服务商状态字典
        """
        status = {}
        for provider, config in self.SUPPORTED_PROVIDERS.items():
            api_key = self.get_api_key(provider)
            status[provider] = {
                'name': config['name'],
                'model': config['model'],
                'configured': api_key is not None,
                'valid': self.validate_provider(provider),
                'env_key': config['env_key'],
            }
        return status