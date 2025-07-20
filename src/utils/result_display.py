"""统一的结果显示器 - 合并重复的打印逻辑"""

from typing import Dict, Any, List
from pathlib import Path
import re
import ast


class ImportResultDisplay:
    """导入结果显示器"""
    
    @staticmethod
    def display_import_results(result, debug: bool = False) -> None:
        """显示导入结果总览
        
        Args:
            result: ImportResult对象
            debug: 是否显示调试信息
        """
        # 处理每个结果
        for item in result.results:
            ImportResultDisplay._display_single_result(item, debug)
        
        # 显示总结（如果有多个结果）
        if len(result.results) > 1:
            ImportResultDisplay._display_summary(result)
    
    @staticmethod
    def _display_single_result(result_item: Dict[str, Any], debug: bool = False) -> None:
        """显示单个导入结果"""
        if isinstance(result_item, dict) and "result" in result_item:
            # 批量导入格式
            result = result_item["result"]
            context = result_item
        else:
            # 直接结果格式
            result = result_item
            context = {}
        
        if result.get("success", False):
            ImportResultDisplay._display_success_result(result, context, debug)
        else:
            ImportResultDisplay._display_failure_result(result, context, debug)
    
    @staticmethod
    def _display_success_result(result: Dict[str, Any], context: Dict[str, Any], debug: bool) -> None:
        """显示成功结果"""
        # 检查是否是多图片合并结果
        is_multi_image = "combined_result" in result or "sections_count" in result
        
        if result.get("has_warnings", False):
            # 有警告的成功
            if is_multi_image:
                print(f"⚠️ 多图片合并完成（有警告）!")
                ImportResultDisplay._print_multi_image_info(result)
            else:
                image_path = context.get("image_path", "未知")
                print(f"⚠️ 导入完成（有警告）: {Path(image_path).name if image_path != '未知' else image_path}")
                ImportResultDisplay._print_single_image_info(result)
            
            print(f"   ⚠️ 警告: {result['warning_message']}")
            
            # 显示AI响应用于调试
            ImportResultDisplay._display_ai_response(result, debug)
        else:
            # 完全成功
            if is_multi_image:
                print(f"✅ 多图片合并成功!")
                ImportResultDisplay._print_multi_image_info(result)
            else:
                image_path = context.get("image_path", "未知")
                print(f"✅ 导入成功: {Path(image_path).name if image_path != '未知' else image_path}")
                ImportResultDisplay._print_single_image_info(result)
        
        # 显示额外信息
        ImportResultDisplay._display_extra_info(result, debug)
    
    @staticmethod
    def _display_failure_result(result: Dict[str, Any], context: Dict[str, Any], debug: bool) -> None:
        """显示失败结果"""
        is_multi_image = "combined_result" in result or "sections_count" in result
        
        if is_multi_image:
            print(f"❌ 多图片合并失败")
        else:
            image_path = context.get("image_path", "未知")
            print(f"❌ 导入失败: {Path(image_path).name if image_path != '未知' else image_path}")
        
        error_msg = result.get('error', '未知错误')
        print(f"   错误: {error_msg}")
        
        # 显示失败的图片（多图片情况）
        if result.get('failed_image'):
            print(f"   失败图片: {result['failed_image']}")
        
        # 显示部分成功信息
        if result.get('processed_images'):
            print(f"   ✅ 已处理: {result['processed_images']} 张图片")
        if result.get('partial_results'):
            print(f"   📋 部分结果可用，但最终合并失败")
        
        # 显示AI响应（验证错误时）
        ImportResultDisplay._display_ai_response(result, debug)
        
        # 显示简化的验证错误
        ImportResultDisplay._display_validation_errors(error_msg)
    
    @staticmethod
    def _print_single_image_info(result: Dict[str, Any]) -> None:
        """打印单张图片信息"""
        if result.get('output_file'):
            print(f"   📄 输出文件: {result['output_file']}")
        if result.get('song_name'):
            print(f"   🎵 歌曲名称: {result['song_name']}")
        if result.get('measures_count'):
            print(f"   📊 小节数量: {result['measures_count']}")
        if result.get('provider_used'):
            print(f"   🤖 使用服务: {result['provider_used']}")
        if result.get('recognition_notes'):
            print(f"   📝 识别备注: {result['recognition_notes']}")
    
    @staticmethod
    def _print_multi_image_info(result: Dict[str, Any]) -> None:
        """打印多图片合并信息"""
        if result.get('output_file'):
            print(f"   📄 输出文件: {result['output_file']}")
        
        combined_result = result.get('combined_result', {})
        if combined_result.get('name'):
            print(f"   🎵 歌曲名称: {combined_result['name']}")
        
        if result.get('sections_count'):
            print(f"   📊 简谱行数: {result['sections_count']}")
        if result.get('images_processed'):
            print(f"   📸 处理图片: {result['images_processed']} 张")
        
        if combined_result.get('bpm'):
            print(f"   ⏱️ BPM: {combined_result['bpm']}")
        if combined_result.get('provider'):
            print(f"   🤖 使用服务: {combined_result['provider']}")
        if combined_result.get('notes'):
            print(f"   📝 合并备注: {combined_result['notes']}")
    
    @staticmethod
    def _display_ai_response(result: Dict[str, Any], debug: bool) -> None:
        """显示AI响应信息"""
        ai_info = result.get('ai_response_info', {})
        if ai_info.get('raw_response'):
            print(f"   🤖 AI完整响应:")
            print(f"      {ai_info['raw_response']}")
        elif result.get('raw_response'):
            print(f"   🤖 AI完整响应:")
            print(f"      {result['raw_response']}")
    
    @staticmethod
    def _display_extra_info(result: Dict[str, Any], debug: bool) -> None:
        """显示额外信息"""
        if result.get('model'):
            print(f"   🔧 AI模型: {result['model']}")
        if result.get('processing_time'):
            print(f"   ⏱️ 处理时间: {result['processing_time']:.2f}秒")
        if result.get('retry_count', 0) > 0:
            print(f"   🔄 重试次数: {result['retry_count']}")
    
    @staticmethod
    def _display_validation_errors(error_msg: str) -> None:
        """显示验证错误（简化格式）"""
        if "validation failed" in error_msg.lower():
            match = re.search(r'validation failed:\s*(\[.*\])', error_msg)
            if match:
                try:
                    error_list = ast.literal_eval(match.group(1))
                    if isinstance(error_list, list) and error_list:
                        print(f"   ❌ 验证错误 ({len(error_list)} 个):")
                        for error in error_list[:3]:  # 只显示前3个
                            print(f"      • {error}")
                        if len(error_list) > 3:
                            print(f"      • ... 还有 {len(error_list) - 3} 个错误")
                except (ValueError, SyntaxError):
                    pass
    
    @staticmethod
    def _display_summary(result) -> None:
        """显示导入总结"""
        print(f"\n📊 导入完成:")
        print(f"   完全成功: {result.total_success} 个")
        if result.total_warnings > 0:
            print(f"   有警告: {result.total_warnings} 个（文件已生成，但需要手动修复）")
        print(f"   失败: {result.total_failed} 个")


class BatchResultDisplay:
    """批量结果显示器"""
    
    @staticmethod
    def display_batch_result(batch_result: Dict[str, Any], debug: bool = False) -> None:
        """显示批量导入结果"""
        total = batch_result["total_images"]
        success = batch_result["successful_imports"]
        failed = batch_result["failed_imports"]
        
        print(f"\n📊 批量导入完成:")
        print(f"   总计: {total} 个文件")
        print(f"   成功: {success} 个")
        print(f"   失败: {failed} 个")
        
        if failed > 0:
            print("\n❌ 失败的文件:")
            for item in batch_result["results"]:
                if not item["result"].get("success", False):
                    filename = Path(item['image_path']).name
                    error_msg = item['result'].get('error', '未知错误')
                    print(f"   {filename}: {error_msg}")
                    
                    # 显示AI响应（最重要的调试信息）
                    if item['result'].get('ai_response_info', {}).get('raw_response'):
                        ai_response = item['result']['ai_response_info']['raw_response']
                        print(f"      🤖 AI响应: {ai_response}")