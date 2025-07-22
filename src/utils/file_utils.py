"""文件处理工具类 - 统一文件和路径处理逻辑"""

from typing import List, Dict, Set
from pathlib import Path
import glob
from .logger import get_logger

logger = get_logger(__name__)


class FileUtils:
    """文件处理工具类 - 提供通用的文件和路径处理功能"""

    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

    # 支持的音频扩展名
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg"}

    # 支持的文档扩展名
    DOCUMENT_EXTENSIONS = {".yaml", ".yml", ".json", ".txt", ".md"}

    @classmethod
    def get_supported_extensions(cls, file_type: str = "all") -> Set[str]:
        """
        获取支持的文件扩展名

        Args:
            file_type: 文件类型 ("image", "audio", "document", "all")

        Returns:
            扩展名集合
        """
        if file_type == "image":
            return cls.IMAGE_EXTENSIONS
        elif file_type == "audio":
            return cls.AUDIO_EXTENSIONS
        elif file_type == "document":
            return cls.DOCUMENT_EXTENSIONS
        else:
            return cls.IMAGE_EXTENSIONS | cls.AUDIO_EXTENSIONS | cls.DOCUMENT_EXTENSIONS

    @classmethod
    def scan_directory_for_files(
        self, directory: Path, file_type: str = "all", recursive: bool = True
    ) -> List[Path]:
        """
        扫描目录中的特定类型文件

        Args:
            directory: 要扫描的目录
            file_type: 文件类型 ("image", "audio", "document", "all")
            recursive: 是否递归扫描子目录

        Returns:
            找到的文件路径列表
        """
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Directory does not exist: {directory}")
            return []

        extensions = self.get_supported_extensions(file_type)
        files = []

        scan_method = directory.rglob if recursive else directory.glob

        for ext in extensions:
            # 扫描小写和大写扩展名
            files.extend(scan_method(f"*{ext}"))
            files.extend(scan_method(f"*{ext.upper()}"))

        # 去重并排序
        unique_files = sorted(list(set(files)))
        logger.info(f"Found {len(unique_files)} {file_type} files in {directory}")

        return unique_files

    @classmethod
    def resolve_file_patterns(cls, patterns: List[str]) -> List[Path]:
        """
        解析文件路径模式

        Args:
            patterns: 文件路径模式列表

        Returns:
            解析后的文件路径列表
        """
        resolved_files = []

        for pattern in patterns:
            path = Path(pattern)

            if path.is_file():
                resolved_files.append(path)
            elif path.is_dir():
                # 递归扫描目录
                resolved_files.extend(cls.scan_directory_for_files(path))
            else:
                # 使用glob模式匹配
                try:
                    matched_files = glob.glob(str(path), recursive=True)
                    resolved_files.extend([Path(f) for f in matched_files])
                except Exception as e:
                    logger.warning(f"Failed to resolve pattern '{pattern}': {e}")

        # 去重并排序
        unique_files = sorted(list(set(resolved_files)))
        logger.info(f"Resolved {len(unique_files)} files from patterns")

        return unique_files

    @classmethod
    def group_files_by_directory(cls, files: List[Path]) -> Dict[Path, List[Path]]:
        """
        按目录分组文件

        Args:
            files: 文件路径列表

        Returns:
            按目录分组的文件字典
        """
        groups = {}

        for file_path in files:
            directory = file_path.parent
            if directory not in groups:
                groups[directory] = []
            groups[directory].append(file_path)

        # 对每个分组按文件名排序
        for directory in groups:
            groups[directory].sort(key=lambda x: x.name.lower())

        logger.info(f"Grouped files into {len(groups)} directories")
        return groups

    @classmethod
    def filter_files_by_extension(
        cls, files: List[Path], extensions: Set[str]
    ) -> List[Path]:
        """
        按扩展名过滤文件

        Args:
            files: 文件路径列表
            extensions: 允许的扩展名集合

        Returns:
            过滤后的文件列表
        """
        filtered = [
            f
            for f in files
            if f.suffix.lower() in extensions or f.suffix.upper() in extensions
        ]

        logger.info(f"Filtered {len(filtered)} files from {len(files)} total")
        return filtered

    @classmethod
    def ensure_directory_exists(cls, directory: Path) -> bool:
        """
        确保目录存在

        Args:
            directory: 目录路径

        Returns:
            是否成功创建或已存在
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False

    @classmethod
    def get_file_stats(cls, files: List[Path]) -> Dict[str, int]:
        """
        获取文件统计信息

        Args:
            files: 文件路径列表

        Returns:
            统计信息字典
        """
        stats = {
            "total_files": len(files),
            "total_size_mb": 0,
            "by_extension": {},
            "by_directory": {},
        }

        total_size = 0

        for file_path in files:
            if file_path.exists():
                # 文件大小
                size = file_path.stat().st_size
                total_size += size

                # 按扩展名统计
                ext = file_path.suffix.lower()
                stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1

                # 按目录统计
                directory = str(file_path.parent)
                stats["by_directory"][directory] = (
                    stats["by_directory"].get(directory, 0) + 1
                )

        stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        return stats
