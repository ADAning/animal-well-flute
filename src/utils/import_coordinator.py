"""简谱导入协调器 - 分离导入流程的各个步骤"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import glob
from ..tools import JianpuSheetImporter, ToolsConfig
from .logger import get_logger

logger = get_logger(__name__)


class ImportResult:
    """导入结果封装"""

    def __init__(self, success: bool = False, error: Optional[str] = None):
        self.success = success
        self.error = error
        self.total_success = 0
        self.total_warnings = 0
        self.total_failed = 0
        self.results = []

    def add_result(self, result: Dict[str, Any]):
        """添加单个结果"""
        self.results.append(result)
        if result.get("success", False):
            if result.get("has_warnings", False):
                self.total_warnings += 1
            else:
                self.total_success += 1
        else:
            self.total_failed += 1


class ImportPathResolver:
    """导入路径解析器"""

    @staticmethod
    def resolve_image_paths(image_patterns: List[str]) -> List[Path]:
        """解析图片路径模式

        Args:
            image_patterns: 图片路径模式列表

        Returns:
            解析后的图片文件路径列表
        """
        image_files = []

        for pattern in image_patterns:
            path = Path(pattern)
            if path.is_file():
                image_files.append(path)
            elif path.is_dir():
                # 递归搜索目录中的图片文件
                image_files.extend(ImportPathResolver._scan_directory(path))
            else:
                # 使用glob模式匹配
                matched_files = glob.glob(str(path))
                image_files.extend([Path(f) for f in matched_files])

        if not image_files:
            logger.warning(f"No image files found for patterns: {image_patterns}")
            return []

        # 去重并排序
        image_files = sorted(list(set(image_files)))
        logger.info(f"Found {len(image_files)} image files")

        return image_files

    @staticmethod
    def _scan_directory(directory: Path) -> List[Path]:
        """扫描目录中的图片文件"""
        image_files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"]:
            image_files.extend(directory.rglob(ext))
            image_files.extend(directory.rglob(ext.upper()))
        return image_files

    @staticmethod
    def group_by_folder(image_files: List[Path]) -> Dict[Path, List[Path]]:
        """按文件夹分组图片

        Args:
            image_files: 图片文件列表

        Returns:
            按文件夹分组的图片字典
        """
        folder_groups = {}
        for image_file in image_files:
            folder_path = image_file.parent
            if folder_path not in folder_groups:
                folder_groups[folder_path] = []
            folder_groups[folder_path].append(image_file)

        # 对每个分组按文件名排序
        for folder_path in folder_groups:
            folder_groups[folder_path].sort()

        logger.info(f"Grouped into {len(folder_groups)} folders")
        return folder_groups


class ImportExecutor:
    """导入执行器"""

    def __init__(self, config: ToolsConfig, output_dir: Optional[Path] = None):
        self.config = config
        self.output_dir = output_dir or Path("songs")
        self.importer = JianpuSheetImporter(config, self.output_dir)

    def execute_single_image(self, image_path: Path, provider: str) -> Dict[str, Any]:
        """执行单张图片导入"""
        logger.info(f"Processing single image: {image_path.name}")
        return self.importer.import_single_image(image_path, provider)

    def execute_multi_image(
        self, image_files: List[Path], provider: str, folder_name: str
    ) -> Dict[str, Any]:
        """执行多张图片合并导入"""
        logger.info(f"Processing {len(image_files)} images from folder '{folder_name}'")
        return self.importer.import_multiple_images(image_files, provider, folder_name)

    def get_available_providers(self) -> List[str]:
        """获取可用的AI服务提供商"""
        return self.importer.list_available_providers()

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取AI服务提供商状态"""
        return self.importer.get_provider_status()


class ImportCoordinator:
    """导入协调器主类"""

    def __init__(self, output_dir: Optional[Path] = None, debug: bool = False):
        self.output_dir = output_dir
        self.debug = debug
        self.config = ToolsConfig()
        self.executor = ImportExecutor(self.config, output_dir)
        self.path_resolver = ImportPathResolver()

    def coordinate_import(
        self, image_patterns: List[str], ai_provider: Optional[str] = None
    ) -> ImportResult:
        """协调整个导入流程

        Args:
            image_patterns: 图片路径模式列表
            ai_provider: 指定的AI服务提供商

        Returns:
            导入结果
        """
        # 1. 检查AI服务配置
        provider_check = self._check_ai_providers(ai_provider)
        if not provider_check.success:
            result = ImportResult()
            result.success = False
            result.error = provider_check.error
            if hasattr(provider_check, "provider_status"):
                result.provider_status = provider_check.provider_status
            if hasattr(provider_check, "available_providers"):
                result.available_providers = provider_check.available_providers
            return result

        selected_provider = provider_check.selected_provider

        # 2. 解析图片路径
        image_files = self.path_resolver.resolve_image_paths(image_patterns)
        if not image_files:
            result = ImportResult()
            result.error = f"No image files found for patterns: {image_patterns}"
            return result

        # 3. 按文件夹分组
        folder_groups = self.path_resolver.group_by_folder(image_files)

        # 显示分析信息
        print(f"📁 找到 {len(image_files)} 个图片文件")
        print(f"📂 检测到 {len(folder_groups)} 个文件夹")
        for folder_path, files_in_folder in folder_groups.items():
            folder_name = folder_path.name if folder_path.name != "." else "root"
            print(f"   📁 {folder_name}: {len(files_in_folder)} 个文件")

        print(f"🤖 使用AI服务: {selected_provider}")

        # 4. 执行导入
        return self._execute_grouped_import(folder_groups, selected_provider)

    def _check_ai_providers(self, ai_provider: Optional[str]) -> "ProviderCheckResult":
        """检查AI服务提供商配置"""
        available_providers = self.executor.get_available_providers()

        if not available_providers:
            result = ProviderCheckResult(False)
            result.error = "未配置任何AI服务提供商"
            result.provider_status = self.executor.get_provider_status()
            return result

        # 选择提供商
        if ai_provider:
            if ai_provider not in available_providers:
                result = ProviderCheckResult(False)
                result.error = f"指定的AI服务提供商 '{ai_provider}' 不可用"
                result.available_providers = available_providers
                return result
            selected_provider = ai_provider
        else:
            selected_provider = available_providers[0]

        logger.info(f"Using AI provider: {selected_provider}")

        result = ProviderCheckResult(True)
        result.selected_provider = selected_provider
        return result

    def _execute_grouped_import(
        self, folder_groups: Dict[Path, List[Path]], provider: str
    ) -> ImportResult:
        """执行分组导入"""
        result = ImportResult(success=True)

        for folder_path, files_in_folder in folder_groups.items():
            folder_name = folder_path.name if folder_path.name != "." else "root"

            try:
                if len(files_in_folder) == 1:
                    # 单张图片
                    print(f"\n📄 处理单张图片: {folder_name}")
                    import_result = self.executor.execute_single_image(
                        files_in_folder[0], provider
                    )
                else:
                    # 多张图片合并
                    print(
                        f"\n🎵 合并文件夹 '{folder_name}' 中的 {len(files_in_folder)} 张图片..."
                    )
                    import_result = self.executor.execute_multi_image(
                        files_in_folder, provider, folder_name
                    )

                result.add_result(import_result)

            except Exception as e:
                logger.error(f"Error processing folder '{folder_name}': {e}")
                print(f"\n❌ 处理文件夹 '{folder_name}' 时发生异常: {e}")
                print(f"   跳过此文件夹，继续处理其他文件夹...")
                import traceback

                print(f"   详细错误: {traceback.format_exc()}")

                error_result = {
                    "success": False,
                    "error": f"Processing failed: {e}",
                    "folder": folder_name,
                }
                result.add_result(error_result)

        return result


class ProviderCheckResult:
    """AI提供商检查结果"""

    def __init__(self, success: bool):
        self.success = success
        self.error: Optional[str] = None
        self.selected_provider: Optional[str] = None
        self.available_providers: Optional[List[str]] = None
        self.provider_status: Optional[Dict[str, Dict[str, Any]]] = None
