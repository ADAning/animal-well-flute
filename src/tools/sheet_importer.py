"""简谱乐谱导入器 - 图片预处理和YAML生成"""

import os
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps
import io

from .jianpu_recognizer import JianpuRecognizer
from .config import ToolsConfig
from ..data.songs.song_manager import SongManager
from ..data.songs.sample_songs import Song
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SheetPreprocessor:
    """简谱乐谱预处理器"""
    
    def __init__(self, config: ToolsConfig):
        self.config = config
        self.max_size = config.get('max_image_size', 2048)
        self.split_threshold = config.get('split_threshold', 1500)
        self.jpeg_quality = config.get('image_quality', 85)
    
    def validate_image(self, image_path: Path) -> bool:
        """验证图片文件是否有效
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            是否为有效图片
        """
        try:
            # 检查文件扩展名
            valid_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}
            if image_path.suffix.lower() not in valid_extensions:
                logger.warning(f"Unsupported image format: {image_path.suffix}")
                return False
            
            # 检查文件是否存在
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return False
            
            # 尝试打开图片
            with Image.open(image_path) as img:
                img.verify()  # 验证图片完整性
            
            return True
            
        except Exception as e:
            logger.error(f"Image validation failed for {image_path}: {e}")
            return False
    
    def preprocess_image(self, image_path: Path) -> Tuple[bytes, str]:
        """预处理图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            (处理后的图片数据, 图片格式)
        """
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 图片增强
                img = self._enhance_image(img)
                
                # 调整尺寸
                img = self._resize_image(img)
                
                # 转换为字节数据
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=self.jpeg_quality, optimize=True)
                return img_bytes.getvalue(), 'jpeg'
                
        except Exception as e:
            logger.error(f"Image preprocessing failed for {image_path}: {e}")
            raise
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """增强图片质量"""
        try:
            # 自动调整对比度
            img = ImageOps.autocontrast(img, cutoff=1)
            
            # 轻微锐化
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # 调整亮度（轻微）
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.05)
            
            return img
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return img
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """调整图片尺寸"""
        width, height = img.size
        max_dimension = max(width, height)
        
        if max_dimension > self.max_size:
            # 按比例缩放
            scale = self.max_size / max_dimension
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        return img
    
    def should_split_image(self, image_path: Path) -> bool:
        """判断是否需要分割图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            是否需要分割
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                max_dimension = max(width, height)
                return max_dimension > self.split_threshold
                
        except Exception as e:
            logger.error(f"Failed to check image size for {image_path}: {e}")
            return False
    
    def split_image(self, image_path: Path) -> List[Path]:
        """分割大图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            分割后的图片路径列表
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # 简单的垂直分割策略
                if height > width:
                    # 竖向图片，水平分割
                    return self._split_horizontally(img, image_path)
                else:
                    # 横向图片，垂直分割
                    return self._split_vertically(img, image_path)
                    
        except Exception as e:
            logger.error(f"Image splitting failed for {image_path}: {e}")
            return [image_path]  # 返回原图片
    
    def _split_horizontally(self, img: Image.Image, original_path: Path) -> List[Path]:
        """水平分割图片"""
        width, height = img.size
        num_parts = (height // self.split_threshold) + 1
        part_height = height // num_parts
        
        split_paths = []
        temp_dir = original_path.parent / f"{original_path.stem}_splits"
        temp_dir.mkdir(exist_ok=True)
        
        for i in range(num_parts):
            top = i * part_height
            bottom = min((i + 1) * part_height, height)
            
            part_img = img.crop((0, top, width, bottom))
            part_path = temp_dir / f"{original_path.stem}_part_{i+1}{original_path.suffix}"
            part_img.save(part_path)
            split_paths.append(part_path)
            
            logger.debug(f"Created split part: {part_path}")
        
        return split_paths
    
    def _split_vertically(self, img: Image.Image, original_path: Path) -> List[Path]:
        """垂直分割图片"""
        width, height = img.size
        num_parts = (width // self.split_threshold) + 1
        part_width = width // num_parts
        
        split_paths = []
        temp_dir = original_path.parent / f"{original_path.stem}_splits"
        temp_dir.mkdir(exist_ok=True)
        
        for i in range(num_parts):
            left = i * part_width
            right = min((i + 1) * part_width, width)
            
            part_img = img.crop((left, 0, right, height))
            part_path = temp_dir / f"{original_path.stem}_part_{i+1}{original_path.suffix}"
            part_img.save(part_path)
            split_paths.append(part_path)
            
            logger.debug(f"Created split part: {part_path}")
        
        return split_paths


class JianpuSheetImporter:
    """简谱乐谱导入器主类"""
    
    def __init__(self, config: Optional[ToolsConfig] = None, 
                 songs_dir: Optional[Path] = None):
        """初始化导入器
        
        Args:
            config: 工具配置
            songs_dir: 歌曲目录
        """
        self.config = config or ToolsConfig()
        self.songs_dir = songs_dir or Path("songs")
        self.preprocessor = SheetPreprocessor(self.config)
        self.recognizer = JianpuRecognizer(self.config)
        self.song_manager = SongManager(self.songs_dir)
    
    def import_single_image(self, image_path: Path, 
                          provider: Optional[str] = None,
                          output_name: Optional[str] = None) -> Dict[str, Any]:
        """导入单张简谱图片
        
        Args:
            image_path: 图片文件路径
            provider: 指定AI服务提供商
            output_name: 输出文件名（不含扩展名）
            
        Returns:
            导入结果字典
        """
        logger.info(f"Starting import for image: {image_path}")
        
        # 验证图片
        if not self.preprocessor.validate_image(image_path):
            return {
                "success": False,
                "error": f"Invalid image file: {image_path}"
            }
        
        try:
            # 检查是否需要分割
            if self.preprocessor.should_split_image(image_path):
                logger.info("Large image detected, splitting into parts...")
                return self._import_split_image(image_path, provider, output_name)
            else:
                # 直接处理单张图片
                return self._import_single_part(image_path, provider, output_name)
                
        except Exception as e:
            logger.error(f"Import failed for {image_path}: {e}")
            return {
                "success": False,
                "error": f"Import failed: {e}"
            }
    
    def _import_single_part(self, image_path: Path, 
                           provider: Optional[str] = None,
                           output_name: Optional[str] = None) -> Dict[str, Any]:
        """导入单个图片部分"""
        
        # 预处理图片
        logger.debug("Preprocessing image...")
        image_data, image_format = self.preprocessor.preprocess_image(image_path)
        
        # AI识别
        logger.info("Recognizing jianpu notation...")
        recognition_result = self.recognizer.recognize(image_data, image_format, provider)
        
        if not recognition_result.get("success", False):
            return {
                "success": False,
                "error": f"Recognition failed: {recognition_result.get('error', 'Unknown error')}"
            }
        
        # 生成YAML文件
        output_name = output_name or image_path.stem
        return self._generate_yaml_file(recognition_result, output_name)
    
    def _import_split_image(self, image_path: Path, 
                           provider: Optional[str] = None,
                           output_name: Optional[str] = None) -> Dict[str, Any]:
        """导入分割后的图片"""
        
        # 分割图片
        split_paths = self.preprocessor.split_image(image_path)
        logger.info(f"Image split into {len(split_paths)} parts")
        
        all_jianpu = []
        errors = []
        
        # 依次处理每个部分
        for i, part_path in enumerate(split_paths):
            logger.info(f"Processing part {i+1}/{len(split_paths)}: {part_path}")
            
            try:
                # 预处理
                image_data, image_format = self.preprocessor.preprocess_image(part_path)
                
                # 识别
                recognition_result = self.recognizer.recognize(image_data, image_format, provider)
                
                if recognition_result.get("success", False):
                    part_jianpu = recognition_result.get("jianpu", [])
                    all_jianpu.extend(part_jianpu)
                    logger.debug(f"Part {i+1} recognized {len(part_jianpu)} measures")
                else:
                    error_msg = f"Part {i+1} recognition failed: {recognition_result.get('error', 'Unknown error')}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    
            except Exception as e:
                error_msg = f"Part {i+1} processing failed: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # 清理临时文件
        self._cleanup_split_files(split_paths)
        
        if not all_jianpu:
            return {
                "success": False,
                "error": "No jianpu data recognized from any part",
                "part_errors": errors
            }
        
        # 合并结果并生成YAML
        combined_result = {
            "success": True,
            "name": recognition_result.get("name", image_path.stem),
            "bpm": recognition_result.get("bpm", 90),
            "jianpu": all_jianpu,
            "notes": f"Imported from split image. Parts processed: {len(split_paths)}. Errors: {len(errors)}"
        }
        
        output_name = output_name or image_path.stem
        result = self._generate_yaml_file(combined_result, output_name)
        
        if errors:
            result["warnings"] = errors
        
        return result
    
    def _cleanup_split_files(self, split_paths: List[Path]):
        """清理分割生成的临时文件"""
        try:
            if split_paths:
                split_dir = split_paths[0].parent
                for path in split_paths:
                    if path.exists():
                        path.unlink()
                        
                # 删除临时目录（如果为空）
                if split_dir.exists() and not any(split_dir.iterdir()):
                    split_dir.rmdir()
                    logger.debug(f"Cleaned up split directory: {split_dir}")
                    
        except Exception as e:
            logger.warning(f"Failed to cleanup split files: {e}")
    
    def _generate_yaml_file(self, recognition_result: Dict[str, Any], 
                           output_name: str) -> Dict[str, Any]:
        """生成YAML文件
        
        Args:
            recognition_result: AI识别结果
            output_name: 输出文件名
            
        Returns:
            生成结果字典
        """
        try:
            # 构建歌曲数据
            song_data = {
                "name": recognition_result.get("name", output_name),
                "bpm": recognition_result.get("bpm", 90),
                "jianpu": recognition_result.get("jianpu", []),
                "offset": 0.0,  # 默认偏移
                "description": f"Imported from image using AI recognition. {recognition_result.get('notes', '')}"
            }
            
            # 验证数据
            validation_errors = self.song_manager.validate_song_data(song_data)
            has_validation_errors = bool(validation_errors)
            
            # 即使有验证错误，也尝试生成文件
            if has_validation_errors:
                # 修复数据以确保能生成有效的YAML文件
                if not song_data.get("name") or song_data["name"] == output_name:
                    song_data["name"] = f"未识别歌名_{output_name}"
                if not song_data.get("bpm") or song_data["bpm"] <= 0:
                    song_data["bpm"] = 90  # 默认BPM
                if not song_data.get("jianpu"):
                    song_data["jianpu"] = ["# 未识别到简谱内容，请手动添加"]
                
                # 添加验证错误信息到描述中
                error_note = f"⚠️ 验证错误: {validation_errors}"
                if song_data.get("description"):
                    song_data["description"] = f"{song_data['description']}\n{error_note}"
                else:
                    song_data["description"] = error_note
            
            # 生成输出路径
            output_path = self.songs_dir / f"{output_name}.yaml"
            
            # 检查文件是否已存在
            counter = 1
            original_path = output_path
            while output_path.exists():
                output_path = original_path.parent / f"{original_path.stem}_{counter}.yaml"
                counter += 1
            
            # 保存YAML文件
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(song_data, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False, indent=2)
            
            logger.info(f"Generated YAML file: {output_path}")
            
            result = {
                "success": True,
                "output_file": str(output_path),
                "song_name": song_data["name"],
                "measures_count": len(song_data["jianpu"]),
                "recognition_notes": recognition_result.get("notes", ""),
                "provider_used": recognition_result.get("provider", "unknown")
            }
            
            # 如果有验证错误，添加警告信息
            if has_validation_errors:
                result["validation_warnings"] = validation_errors
                result["has_warnings"] = True
                result["warning_message"] = f"文件已生成但存在验证警告: {validation_errors}"
                # 添加AI响应信息用于调试
                result["ai_response_info"] = {
                    "raw_response": recognition_result.get("raw_response", ""),
                    "provider_used": recognition_result.get("provider", "unknown"),
                    "model_used": recognition_result.get("model", ""),
                    "processing_time": recognition_result.get("processing_time", 0),
                    "retry_count": recognition_result.get("retry_count", 0)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"YAML generation failed: {e}")
            return {
                "success": False,
                "error": f"YAML generation failed: {e}"
            }
    
    def import_batch(self, image_paths: List[Path], 
                    provider: Optional[str] = None) -> Dict[str, Any]:
        """批量导入简谱图片
        
        Args:
            image_paths: 图片文件路径列表
            provider: 指定AI服务提供商
            
        Returns:
            批量导入结果字典
        """
        logger.info(f"Starting batch import for {len(image_paths)} images")
        
        results = []
        success_count = 0
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
            
            result = self.import_single_image(image_path, provider)
            results.append({
                "image_path": str(image_path),
                "result": result
            })
            
            if result.get("success", False):
                success_count += 1
        
        return {
            "total_images": len(image_paths),
            "successful_imports": success_count,
            "failed_imports": len(image_paths) - success_count,
            "results": results
        }
    
    def import_multiple_images(self, image_paths: List[Path],
                             provider: Optional[str] = None,
                             output_name: Optional[str] = None) -> Dict[str, Any]:
        """导入多张图片组成一首歌曲
        
        Args:
            image_paths: 图片文件路径列表（按顺序排列）
            provider: 指定AI服务提供商
            output_name: 输出文件名（不含扩展名）
            
        Returns:
            导入结果字典
        """
        if not image_paths:
            return {
                "success": False,
                "error": "No image paths provided"
            }
        
        logger.info(f"Starting multi-image import for {len(image_paths)} images")
        
        # 验证所有图片
        for i, image_path in enumerate(image_paths):
            if not self.preprocessor.validate_image(image_path):
                return {
                    "success": False,
                    "error": f"Invalid image file at index {i}: {image_path}"
                }
        
        try:
            # 识别每个图片部分
            all_sections = []
            recognition_results = []
            
            for i, image_path in enumerate(image_paths):
                logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
                
                # 预处理图片
                image_data, image_format = self.preprocessor.preprocess_image(image_path)
                
                # AI识别
                result = self.recognizer.recognize(image_data, image_format, provider)
                recognition_results.append(result)
                
                if result.get("success", False):
                    jianpu_lines = result.get("jianpu", [])
                    if jianpu_lines:
                        all_sections.extend(jianpu_lines)
                        logger.info(f"Added {len(jianpu_lines)} lines from image {i+1}")
                    else:
                        logger.warning(f"No jianpu content found in image {i+1}")
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Recognition failed for image {i+1}: {error_msg}")
                    return {
                        "success": False,
                        "error": f"Recognition failed for image {i+1}: {error_msg}",
                        "failed_image": str(image_path),
                        "partial_results": recognition_results
                    }
            
            if not all_sections:
                return {
                    "success": False,
                    "error": "No jianpu content recognized from any image",
                    "recognition_results": recognition_results
                }
            
            # 合并结果
            combined_result = self._combine_multi_image_results(
                recognition_results, all_sections, output_name
            )
            
            # 生成YAML文件
            output_result = self._generate_yaml_file(combined_result, output_name or "multi_image_song")
            
            if output_result.get("success", False):
                return {
                    "success": True,
                    "output_file": output_result["output_file"],
                    "combined_result": combined_result,
                    "sections_count": len(all_sections),
                    "images_processed": len(image_paths),
                    "recognition_details": recognition_results
                }
            else:
                return output_result
            
        except Exception as e:
            logger.error(f"Multi-image import failed: {e}")
            return {
                "success": False,
                "error": f"Multi-image import failed: {e}"
            }
    
    def import_folder_as_single_song(self, folder_path: Path,
                                    provider: Optional[str] = None,
                                    output_name: Optional[str] = None,
                                    file_pattern: str = "*.{png,jpg,jpeg,webp}") -> Dict[str, Any]:
        """将整个文件夹中的所有图片合并为一首歌曲
        
        Args:
            folder_path: 文件夹路径
            provider: 指定AI服务提供商
            output_name: 输出文件名（不含扩展名）
            file_pattern: 文件匹配模式
            
        Returns:
            导入结果字典
        """
        logger.info(f"Importing folder as single song: {folder_path}")
        
        if not folder_path.exists() or not folder_path.is_dir():
            return {
                "success": False,
                "error": f"Folder not found: {folder_path}"
            }
        
        # 获取所有图片文件（按名称排序）
        image_files = []
        for ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff']:
            image_files.extend(folder_path.glob(f"*.{ext}"))
            image_files.extend(folder_path.glob(f"*.{ext.upper()}"))
        
        image_files = sorted(image_files, key=lambda x: x.name)
        
        if not image_files:
            return {
                "success": False,
                "error": f"No image files found in folder: {folder_path}"
            }
        
        # 使用多图片导入功能
        result = self.import_multiple_images(
            image_files, 
            provider=provider, 
            output_name=output_name or folder_path.name
        )
        
        return result
    
    def _combine_multi_image_results(self, recognition_results: List[Dict[str, Any]], 
                                   all_sections: List[str], 
                                   output_name: Optional[str]) -> Dict[str, Any]:
        """合并多个图片的识别结果
        
        Args:
            recognition_results: 每个图片的识别结果
            all_sections: 所有识别的简谱行
            output_name: 输出文件名
            
        Returns:
            合并后的结果
        """
        # 收集所有建议的标题（优先选择非空的）
        titles = []
        for result in recognition_results:
            title = result.get("name")
            if title and title.strip() and title.lower() not in ["null", "none", "未知"]:
                titles.append(title.strip())
        
        # 选择最频繁的标题或使用输出名称
        final_title = output_name
        if titles:
            # 找到最频繁的标题
            title_counts = {}
            for title in titles:
                title_counts[title] = title_counts.get(title, 0) + 1
            final_title = max(title_counts.items(), key=lambda x: x[1])[0]
        
        # 收集BPM信息（优先选择非空的）
        bpms = []
        for result in recognition_results:
            bpm = result.get("bpm")
            if bpm and isinstance(bpm, (int, float)) and bpm > 0:
                bpms.append(bpm)
        
        # 使用平均BPM或默认值
        final_bpm = None
        if bpms:
            final_bpm = int(sum(bpms) / len(bpms))
        
        # 收集所有注释
        notes = []
        for i, result in enumerate(recognition_results):
            note = result.get("notes", "")
            if note and note.strip():
                notes.append(f"图片{i+1}: {note.strip()}")
        
        # 添加合并信息
        notes.append(f"由{len(recognition_results)}张图片合并而成，共{len(all_sections)}行简谱。")
        
        return {
            "name": final_title or "未知曲目",
            "bpm": final_bpm,
            "jianpu": all_sections,
            "notes": "; ".join(notes) if notes else "多图片合并导入",
            "success": True,
            "provider": recognition_results[0].get("provider", "unknown") if recognition_results else "unknown"
        }
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取AI服务提供商状态"""
        return self.recognizer.list_provider_status()
    
    def list_available_providers(self) -> List[str]:
        """列出可用的AI服务提供商"""
        return self.recognizer.get_available_providers()