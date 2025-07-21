"""简谱识别器 - 多模态AI服务统一接口"""

import base64
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests
from io import BytesIO

from .config import ToolsConfig, JIANPU_RECOGNITION_PROMPT
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JianpuRecognitionProvider(ABC):
    """简谱识别服务提供者抽象基类"""

    def __init__(self, api_key: str, config: ToolsConfig):
        self.api_key = api_key
        self.config = config
        self.timeout = config.get("timeout", 30)
        self.retry_attempts = config.get("retry_attempts", 3)

    @abstractmethod
    def recognize_jianpu(self, image_data: bytes, image_format: str) -> Dict[str, Any]:
        """识别简谱图片

        Args:
            image_data: 图片二进制数据
            image_format: 图片格式 (png, jpg, etc.)

        Returns:
            识别结果字典
        """
        pass

    def _encode_image(self, image_data: bytes) -> str:
        """将图片编码为base64字符串"""
        return base64.b64encode(image_data).decode("utf-8")

    def _clean_response_content(self, content: str) -> str:
        """清理API响应中的不应该出现的起始符和结束符

        Args:
            content: 原始响应内容

        Returns:
            清理后的内容
        """
        if not content:
            return content

        # 移除开头和结尾的不应该出现的标记
        content = content.strip()
        while True:
            original_content = content
            # 移除开头的标记
            if content.startswith("||:"):
                content = content[3:].strip()
            elif content.startswith("||"):
                content = content[2:].strip()
            elif content.endswith(":||"):
                content = content[:-3].strip()
            elif content.endswith("||"):
                content = content[:-2].strip()
            else:
                break
            # 如果没有变化，防止无限循环
            if content == original_content:
                break

        return content

    def _get_unified_prompt(self) -> str:
        """获取统一的简谱识别提示词"""
        return JIANPU_RECOGNITION_PROMPT

    def _parse_recognition_result(
        self, content: str, provider_name: str
    ) -> Dict[str, Any]:
        """解析AI识别结果 - 统一的解析方法

        Args:
            content: API响应内容
            provider_name: 提供者名称

        Returns:
            解析后的结果字典
        """
        try:
            import yaml

            # 清理响应内容中的不应该出现的标记
            content = self._clean_response_content(content)

            # 提取YAML部分
            if "```yaml" in content:
                yaml_start = content.find("```yaml")
                # 查找```yaml后的换行符，如果没有换行符就使用```yaml后的位置
                newline_after_yaml = content.find("\n", yaml_start)
                if newline_after_yaml != -1:
                    start = newline_after_yaml + 1
                else:
                    start = yaml_start + 7  # len('```yaml') = 7

                end = content.rfind("```")
                if start < end:
                    content = content[start:end].strip()
            elif "```" in content:
                code_start = content.find("```")
                # 查找```后的换行符，如果没有换行符就使用```后的位置
                newline_after_code = content.find("\n", code_start)
                if newline_after_code != -1:
                    start = newline_after_code + 1
                else:
                    start = code_start + 3  # len('```') = 3

                end = content.rfind("```")
                if start < end:
                    content = content[start:end].strip()

            # 解析YAML
            result = yaml.safe_load(content)
            if isinstance(result, dict):
                # 清理jianpu内容中的无效标记
                if "jianpu" in result and isinstance(result["jianpu"], list):
                    result["jianpu"] = self._clean_jianpu_content(result["jianpu"])

                result["success"] = True
                result["provider"] = provider_name
                return result
            else:
                raise ValueError("YAML content is not a dictionary")

        except Exception as e:
            logger.error(f"Failed to parse {provider_name} response as YAML: {e}")
            return {
                "success": False,
                "error": f"YAML parsing failed: {e}",
                "raw_content": content,
            }

    def _clean_jianpu_content(self, jianpu_lines: List[str]) -> List[str]:
        """清理简谱内容中的无效标记

        Args:
            jianpu_lines: 简谱行列表

        Returns:
            清理后的简谱行列表
        """
        cleaned_lines = []

        for line in jianpu_lines:
            if not isinstance(line, str):
                cleaned_lines.append(line)
                continue

            # 移除重复记号标记 ||:, :||, ||
            cleaned_line = line

            # 移除行首的标记
            while True:
                original = cleaned_line
                if cleaned_line.startswith("||:"):
                    cleaned_line = cleaned_line[3:].strip()
                elif cleaned_line.startswith("||"):
                    cleaned_line = cleaned_line[2:].strip()
                else:
                    break
                # 防止无限循环
                if cleaned_line == original:
                    break

            # 移除行尾的标记
            while True:
                original = cleaned_line
                if cleaned_line.endswith(":||"):
                    cleaned_line = cleaned_line[:-3].strip()
                elif cleaned_line.endswith("||"):
                    cleaned_line = cleaned_line[:-2].strip()
                else:
                    break
                # 防止无限循环
                if cleaned_line == original:
                    break

            # 移除行中的标记 (通常出现在引号中)
            cleaned_line = (
                cleaned_line.replace("||:", "").replace(":||", "").replace("||", "")
            )

            # 移除多余的空格
            cleaned_line = " ".join(cleaned_line.split())

            if cleaned_line:  # 只添加非空行
                cleaned_lines.append(cleaned_line)

        return cleaned_lines

    def _make_request_with_retry(
        self, url: str, headers: Dict, data: Dict
    ) -> requests.Response:
        """带重试的HTTP请求"""
        last_exception = None

        for attempt in range(self.retry_attempts):
            try:
                logger.debug(
                    f"Making API request (attempt {attempt + 1}/{self.retry_attempts})"
                )
                response = requests.post(
                    url, headers=headers, json=data, timeout=self.timeout
                )
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    wait_time = 2**attempt  # 指数退避
                    logger.debug(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

        raise last_exception


class GeminiJianpuProvider(JianpuRecognitionProvider):
    """Google Gemini 简谱识别服务"""

    def __init__(self, api_key: str, config: ToolsConfig):
        super().__init__(api_key, config)
        self.model = config.get_provider_config("gemini")["model"]
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化Gemini客户端"""
        try:
            from google import genai
            from google.genai import types

            # 初始化客户端（API密钥通过环境变量GOOGLE_API_KEY自动读取）
            self.client = genai.Client(api_key=self.api_key)
            self.types = types
            logger.debug("Gemini client initialized successfully")

        except ImportError:
            logger.error(
                "google-genai library not installed. Please run: pip install google-genai"
            )
            raise ImportError("google-genai library is required for Gemini API")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def recognize_jianpu(self, image_data: bytes, image_format: str) -> Dict[str, Any]:
        """使用Gemini识别简谱"""

        if not self.client:
            return {"success": False, "error": "Gemini client not initialized"}

        try:
            # 处理图片格式
            mime_type = f"image/{image_format}"
            if image_format == "jpg":
                mime_type = "image/jpeg"

            # 构建请求内容 - 按照官方示例的正确格式
            contents = [
                self._get_unified_prompt(),  # 使用统一的提示词
                self.types.Part.from_bytes(data=image_data, mime_type=mime_type),
            ]

            # 调用API
            logger.debug(f"Calling Gemini API with model: {self.model}")
            start_time = time.time()
            response = self.client.models.generate_content(
                model=self.model, contents=contents
            )
            processing_time = time.time() - start_time

            # 获取响应文本
            if hasattr(response, "text") and response.text:
                content = response.text
                parsed_result = self._parse_recognition_result(content, "gemini")
                # 添加调试信息
                parsed_result["raw_response"] = content
                parsed_result["processing_time"] = processing_time
                parsed_result["model"] = self.model
                return parsed_result
            else:
                return {"success": False, "error": "No text response from Gemini API"}

        except Exception as e:
            logger.error(f"Gemini recognition failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "gemini",
                "model": self.model,
            }


class DoubaoJianpuProvider(JianpuRecognitionProvider):
    """Doubao (豆包) 简谱识别服务"""

    def __init__(self, api_key: str, config: ToolsConfig):
        super().__init__(api_key, config)
        self.model = config.get_provider_config("doubao")["model"]
        self.base_url = config.get_provider_config("doubao")["base_url"]

    def recognize_jianpu(self, image_data: bytes, image_format: str) -> Dict[str, Any]:
        """使用Doubao识别简谱"""

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 使用统一的简谱识别提示词
        prompt = self._get_unified_prompt()

        # 编码图片
        image_base64 = self._encode_image(image_data)

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1,
        }

        try:
            start_time = time.time()
            response = self._make_request_with_retry(url, headers, data)
            processing_time = time.time() - start_time
            result = response.json()

            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                parsed_result = self._parse_recognition_result(content, "doubao")
                # 添加调试信息
                parsed_result["raw_response"] = content
                parsed_result["processing_time"] = processing_time
                parsed_result["model"] = self.model
                return parsed_result
            else:
                raise Exception(f"Unexpected API response format: {result}")

        except Exception as e:
            logger.error(f"Doubao recognition failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "doubao",
                "model": self.model,
            }


class JianpuRecognizer:
    """简谱识别器主类"""

    def __init__(self, config: Optional[ToolsConfig] = None):
        """初始化简谱识别器

        Args:
            config: 工具配置对象
        """
        self.config = config or ToolsConfig()
        self._providers = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化可用的识别服务提供者"""
        provider_classes = {
            "gemini": GeminiJianpuProvider,
            "doubao": DoubaoJianpuProvider,
        }

        for provider_name, provider_class in provider_classes.items():
            api_key = self.config.get_api_key(provider_name)
            if api_key:
                try:
                    self._providers[provider_name] = provider_class(
                        api_key, self.config
                    )
                    logger.debug(f"Initialized provider: {provider_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize provider {provider_name}: {e}"
                    )

    def get_available_providers(self) -> List[str]:
        """获取可用的识别服务提供者列表"""
        return list(self._providers.keys())

    def recognize(
        self, image_data: bytes, image_format: str, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """识别简谱图片

        Args:
            image_data: 图片二进制数据
            image_format: 图片格式
            provider: 指定使用的服务提供者，None则使用默认

        Returns:
            识别结果字典
        """
        if not self._providers:
            return {
                "success": False,
                "error": "No AI providers configured. Please set up API keys.",
            }

        # 选择提供者
        if provider and provider in self._providers:
            selected_provider = self._providers[provider]
            provider_name = provider
        else:
            # 使用第一个可用的提供者
            provider_name = list(self._providers.keys())[0]
            selected_provider = self._providers[provider_name]

        logger.info(f"Using provider: {provider_name}")

        try:
            result = selected_provider.recognize_jianpu(image_data, image_format)
            result["used_provider"] = provider_name
            return result

        except Exception as e:
            logger.error(f"Recognition failed with provider {provider_name}: {e}")
            return {
                "success": False,
                "error": f"Recognition failed: {e}",
                "provider": provider_name,
            }

    def list_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """列出所有提供者的状态"""
        return self.config.list_providers_status()
