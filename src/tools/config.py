"""工具配置管理"""

import os
from typing import Dict, Optional, Any
from pathlib import Path
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 简谱识别Prompt
JIANPU_RECOGNITION_PROMPT = """# 角色与任务
你是一名精通乐理且专业的OCR工程师, 擅长将图片中的简谱(Jianpu)精确地转换为指定的YAML格式. 你的任务是分析提供的简谱图片, 并根据以下详细规则进行转录.

# 核心规则
- **专注于乐谱:** 忽略所有歌词, 文本注释或和弦, 除非它们是标题或BPM标记的一部分.
- **逐行处理:** 乐谱是按行组织的. 请分别处理每一行. 最终YAML中的`jianpu`列表应为图片中的每一行乐谱包含一个字符串条目.
- **小节线:** 在单行乐谱中, 使用竖线`|`来分隔小节. 不要进行双竖线的转录, 例如`||:`, `:||`, `||`等.

# 音符转录规则

1.  **基本音符:** 将音符`1`到`7`转录为对应的数字. 将休止符转录为`0`.
2.  **高低八度:**
    - 音符**上方**的圆点表示高八度. 在音符前加上`h`. (例如: `h1`, 它可能长得会像`i`)
    - 音符**下方**的圆点表示低八度. 在音符前加上`l`. (例如: `l1`, 它可能长得会像`!`, `l2`, 它可能长得会像`?`)
3. **高低半音:**
    - 音符**左侧**的井号`#`表示升半音. 转录时去掉`#`, 但将音符值+0.5. (例如: `h2`升半音为`h2.5`)
    - 音符**左侧**的字母`b`表示降半音. 转录时去掉`b`, 但将音符值-0.5. (例如: `h2`降半音为`h1.5`) 
4.  **节奏(时值):**
    - **下划线:** 音符(或一组音符)下方的下划线数量决定其时值. 每有一条下划线, 就用一层括号将音符括起来. 
        - 一条下划线: `(3)`
        - 两条下划线: `((3))`
        - 多个音符均有下划线: `(1 2)`, `((3 5))`
    - **附点:** 音符**右侧**的圆点表示延长其时值. 在音符后加上`d`. (例如: `6d`)
    - **延音线:** 音符后面的破折号`-`表示音符的持续. 每个`-`代表该音符持续一个节拍.
5.  **组合修饰符:** 八度修饰符和附点可以组合使用. 顺序为`(八度)(音符)(附点)`.
    - 示例: 一个高八度的`6`带一个附点, 应记为`h6d`.
    - 示例: 一个低八度的`2`带一条下划线, 应记为`(l2)`.
6. **注意观察**: 在乐谱中, 专注于圆点的位置, 下划线数量及覆盖范围的观察, 因为它们与转录密切相关.

# YAML 输出格式

你必须严格按照以下结构输出一个单独的, 格式正确的YAML代码块. 不要在YAML代码块前后添加任何解释性文字.

```yaml
bpm: BPM值
name: "歌曲标题"
jianpu:
  - "第一行内容..."
  - "第二行内容..."
notes: "转录说明或遇到的问题"
```

- `bpm`: 如果图片中存在BPM标记(例如 "♩=120"), 请提取数字`120`. 如果没有, 则使用`null`.
- `name`: 从图片中提取歌曲的标题. 如果没有标题, 则使用`null`.
- `jianpu`: 这是一个字符串列表. 每个字符串代表一行完整的乐谱, 需严格按照上述规则转录.
- `notes`: 使用此字段描述在转录过程中遇到的任何不确定性, 无法辨认的部分或其他问题. 如果没有问题, 请留空字符串`""`.

# 输出示例

```yaml
bpm: 90
name: "我的歌"
jianpu:
  - "1 2 | 3 (4 5) | 6 - - - |"
  - "l1 2 | ((3 4)) h5d | 0 |"
notes: ""
```"""


class ToolsConfig:
    """工具模块配置管理"""

    # 支持的AI服务提供商
    SUPPORTED_PROVIDERS = {
        "gemini": {
            "name": "Google Gemini 2.5 Flash",
            "env_key": "GOOGLE_API_KEY",
            "model": "gemini-2.5-flash",
            "base_url": None,
        },
        "doubao": {
            "name": "Doubao Vision (豆包)",
            "env_key": "ARK_API_KEY",
            "model": "doubao-seed-1-6-250615",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        },
    }

    # 默认配置
    DEFAULT_CONFIG = {
        "ai_provider": "gemini",  # 默认使用Gemini
        "max_image_size": 2048,  # 最大图片尺寸(像素)
        "split_threshold": 1500,  # 超过此尺寸时进行分割
        "image_quality": 85,  # JPEG压缩质量
        "retry_attempts": 3,  # API调用重试次数
        "timeout": 30,  # API调用超时时间(秒)
    }

    def __init__(self, config_file: Optional[Path] = None):
        """初始化配置

        Args:
            config_file: 可选的配置文件路径
        """
        self.config_file = (
            config_file or Path.home() / ".animal-well-flute" / "tools_config.json"
        )
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                self.config.update(file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")

    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
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

        env_key = self.SUPPORTED_PROVIDERS[provider]["env_key"]
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
                "name": config["name"],
                "model": config["model"],
                "configured": api_key is not None,
                "valid": self.validate_provider(provider),
                "env_key": config["env_key"],
            }
        return status
