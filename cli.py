#!/usr/bin/env python3
"""简化的CLI工具"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.parser import RelativeParser
from src.core.converter import AutoConverter
from src.core.flute import AutoFlute
from src.data.songs import SongManager
from src.utils.logger import setup_logging
from src.tools import JianpuSheetImporter, ToolsConfig
import time
from pathlib import Path
import glob


def auto_play(song_name, strategy_args=["optimal"], bpm=None, ready_time=5):
    """自动演奏功能"""

    # 设置日志
    setup_logging("INFO")

    # 初始化歌曲管理器
    song_manager = SongManager(songs_dir=Path("songs"))

    try:
        song = song_manager.get_song(song_name)
    except Exception as e:
        print(f"❌ 乐曲 '{song_name}' 不存在")
        print(f"📋 可用乐曲: {', '.join(song_manager.list_songs())}")
        return False
    final_bpm = bpm or song.bpm

    print(f"🎵 乐曲: {song.name}")
    print(f"📊 BPM: {final_bpm}")

    # 解析策略参数
    strategy_type = strategy_args[0]
    strategy_param = None

    if strategy_type == "auto":
        if len(strategy_args) > 1:
            strategy_param = strategy_args[1]  # high/low/optimal
        else:
            strategy_param = "optimal"
        final_strategy = "auto"
    elif strategy_type == "manual":
        if len(strategy_args) > 1:
            try:
                strategy_param = float(strategy_args[1])  # offset
            except ValueError:
                if strategy_args[1] == "song":
                    offset = song.offset
                    if offset != 0.0:
                        strategy_param = offset
                        print(
                            f"🎵 使用乐曲 '{song_name}' 的乐谱相对偏移量: {offset:+.1f}"
                        )
                    else:
                        print(f"❌ 乐曲 '{song_name}' 的相对偏移量为0，无法使用")
                        return False
                else:
                    print(f"❌ 无效的偏移量: {strategy_args[1]}")
                    return False
        else:
            print("❌ 手动策略需要指定偏移量")
            return False
        final_strategy = "manual"
    elif strategy_type == "none":
        final_strategy = "manual"
        strategy_param = 0.0
    else:
        # optimal/high/low
        if strategy_type in ["optimal", "high", "low"]:
            final_strategy = strategy_type
        else:
            print(f"❌ 未知策略: {strategy_type}")
            return False

    if strategy_type == "auto":
        print(f"🎯 策略: auto ({strategy_param})")
    elif strategy_type == "manual":
        print(f"🎯 策略: manual (偏移: {strategy_param:+.1f})")
    elif strategy_type == "none":
        print(f"🎯 策略: none (无偏移)")
    else:
        print(f"🎯 策略: {final_strategy}")

    # 解析和转换
    parser = RelativeParser()
    converter = AutoConverter()

    parsed = parser.parse(song.jianpu)

    if final_strategy == "manual":
        converted = converter.convert_jianpu(
            parsed, strategy="manual", manual_offset=strategy_param
        )
    elif final_strategy == "auto":
        converted = converter.convert_jianpu(
            parsed, strategy="auto", auto_preference=strategy_param
        )
    else:
        converted = converter.convert_jianpu(parsed, strategy=final_strategy)

    # 显示音域信息
    range_info = parser.get_range_info(parsed)
    print(
        f"🎼 音域跨度: {range_info['span']:.1f} 半音 ({range_info['octaves']:.1f} 八度)"
    )

    # 准备演奏
    flute = AutoFlute()
    beat_interval = 60.0 / final_bpm

    # 检查无效音符
    invalid_count = sum(
        1
        for bar in converted
        for note in bar
        if note.physical_height is not None and not note.key_combination
    )

    if invalid_count > 0:
        print(f"⚠️ 发现 {invalid_count} 个无法演奏的音符")

    print(f"⏱️ 准备时间: {ready_time} 秒")
    print("🎹 请切换到游戏窗口...")

    for i in range(ready_time, 0, -1):
        print(f"   {i}...")
        time.sleep(1)

    print("🎵 开始演奏!")
    try:
        flute.play_song(converted, beat_interval)
        print("✅ 演奏完成!")
        return True
    except Exception as e:
        print(f"❌ 演奏失败: {e}")
        return False


def analyze_song(song_name):
    """分析乐曲"""

    # 初始化歌曲管理器
    song_manager = SongManager(songs_dir=Path("songs"))

    try:
        song = song_manager.get_song(song_name)
    except Exception as e:
        print(f"❌ 乐曲 '{song_name}' 不存在")
        return False
    print(f"🎵 分析乐曲: {song.name}")

    # 解析
    parser = RelativeParser()
    parsed = parser.parse(song.jianpu)

    # 音域分析
    range_info = parser.get_range_info(parsed)
    print(f"🎼 音域: {range_info['min']:.1f} ~ {range_info['max']:.1f} 半音")
    print(f"📐 跨度: {range_info['span']:.1f} 半音 ({range_info['octaves']:.1f} 八度)")

    # 映射建议
    converter = AutoConverter()
    preview = converter.get_conversion_preview(parsed)

    print("\n🎯 映射策略建议:")
    for strategy, info in preview.get("suggestions", {}).items():
        if strategy == "analysis":
            continue
        if "error" not in info:
            feasible = "✅" if info.get("feasible", True) else "❌"
            print(f"   {strategy:8s}: 偏移 {info['offset']:+5.1f} 半音 {feasible}")

    return True


def import_sheet(image_paths, ai_provider=None, output_dir=None, debug=False):
    """导入简谱图片功能"""
    
    try:
        # 设置日志
        setup_logging("INFO")
        
        # 初始化配置和导入器
        config = ToolsConfig()
        songs_dir = Path(output_dir) if output_dir else Path("songs")
        importer = JianpuSheetImporter(config, songs_dir)
        
        # 检查AI服务配置
        available_providers = importer.list_available_providers()
        if not available_providers:
            print("❌ 未配置任何AI服务提供商")
            print("请设置以下环境变量之一:")
            status = importer.get_provider_status()
            for provider, info in status.items():
                print(f"   {info['env_key']} - {info['name']}")
            return False
        
        # 选择AI服务提供商
        if ai_provider:
            if ai_provider not in available_providers:
                print(f"❌ 指定的AI服务提供商 '{ai_provider}' 不可用")
                print(f"可用的服务商: {', '.join(available_providers)}")
                return False
            selected_provider = ai_provider
        else:
            selected_provider = available_providers[0]
        
        print(f"🤖 使用AI服务: {selected_provider}")
        
        # 处理图片路径
        image_files = []
        for pattern in image_paths:
            path = Path(pattern)
            if path.is_file():
                image_files.append(path)
            elif path.is_dir():
                # 递归搜索目录中的图片文件（包括子目录）
                for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp']:
                    image_files.extend(path.rglob(ext))  # 使用rglob递归搜索
                    image_files.extend(path.rglob(ext.upper()))
            else:
                # 使用glob模式匹配
                matched_files = glob.glob(str(path))
                image_files.extend([Path(f) for f in matched_files])
        
        if not image_files:
            print(f"❌ 未找到任何图片文件: {image_paths}")
            return False
        
        # 去重并排序
        image_files = sorted(list(set(image_files)))
        print(f"📁 找到 {len(image_files)} 个图片文件")
        
        # 按文件夹分组图片
        folder_groups = {}
        for image_file in image_files:
            folder_path = image_file.parent
            if folder_path not in folder_groups:
                folder_groups[folder_path] = []
            folder_groups[folder_path].append(image_file)
        
        # 对每个分组按文件名排序
        for folder_path in folder_groups:
            folder_groups[folder_path].sort()
        
        print(f"📂 检测到 {len(folder_groups)} 个文件夹")
        
        # 显示文件夹信息
        for folder_path, files_in_folder in folder_groups.items():
            folder_name = folder_path.name if folder_path.name != "." else "root"
            print(f"   📁 {folder_name}: {len(files_in_folder)} 个文件")
        
        # 处理每个文件夹
        total_success = 0
        total_warnings = 0
        total_failed = 0
        
        for folder_path, files_in_folder in folder_groups.items():
            folder_name = folder_path.name if folder_path.name != "." else "root"
            
            try:
                if len(files_in_folder) == 1:
                    # 单张图片
                    print(f"\n📄 处理单张图片: {folder_name}")
                    result = importer.import_single_image(files_in_folder[0], selected_provider)
                    _print_import_result(result, files_in_folder[0], debug)
                    if result.get("success", False):
                        if result.get("has_warnings", False):
                            total_warnings += 1
                        else:
                            total_success += 1
                    else:
                        total_failed += 1
                else:
                    # 多张图片合并为一首歌
                    print(f"\n🎵 合并文件夹 '{folder_name}' 中的 {len(files_in_folder)} 张图片...")
                    result = importer.import_multiple_images(files_in_folder, selected_provider, folder_name)
                    _print_multi_image_result(result, debug)
                    if result.get("success", False):
                        if result.get("has_warnings", False):
                            total_warnings += 1
                        else:
                            total_success += 1
                    else:
                        total_failed += 1
            except Exception as e:
                print(f"\n❌ 处理文件夹 '{folder_name}' 时发生异常: {e}")
                print(f"   跳过此文件夹，继续处理其他文件夹...")
                total_failed += 1
                import traceback
                print(f"   详细错误: {traceback.format_exc()}")
                continue
        
        # 显示总结
        if len(folder_groups) > 1:
            print(f"\n📊 导入完成:")
            print(f"   完全成功: {total_success} 个")
            if total_warnings > 0:
                print(f"   有警告: {total_warnings} 个（文件已生成，但需要手动修复）")
            print(f"   失败: {total_failed} 个")
        
        return (total_success + total_warnings) > 0
    
    except Exception as e:
        print(f"\n💥 导入过程中发生未预期的异常: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False


def _print_multi_image_result(result, debug=False):
    """打印多图片合并导入结果"""
    if result.get("success", False):
        # 区分成功和带警告的成功
        if result.get("has_warnings", False):
            print(f"⚠️ 多图片合并完成（有警告）!")
            print(f"   📄 输出文件: {result['output_file']}")
            print(f"   🎵 歌曲名称: {result['combined_result']['name']}")
            print(f"   📊 简谱行数: {result['sections_count']}")
            print(f"   📸 处理图片: {result['images_processed']} 张")
            print(f"   ⚠️ 警告: {result['warning_message']}")
            
            # 显示AI响应用于调试
            if result.get('ai_response_info', {}).get('raw_response'):
                print(f"   🤖 AI完整响应:")
                print(f"      {result['ai_response_info']['raw_response']}")
        else:
            print(f"✅ 多图片合并成功!")
            print(f"   📄 输出文件: {result['output_file']}")
            print(f"   🎵 歌曲名称: {result['combined_result']['name']}")
            print(f"   📊 简谱行数: {result['sections_count']}")
            print(f"   📸 处理图片: {result['images_processed']} 张")
            if result['combined_result'].get('bpm'):
                print(f"   ⏱️ BPM: {result['combined_result']['bpm']}")
            print(f"   🤖 使用服务: {result['combined_result']['provider']}")
            if result['combined_result'].get('notes'):
                print(f"   📝 合并备注: {result['combined_result']['notes']}")
    else:
        print(f"❌ 多图片合并失败")
        error_msg = result.get('error', '未知错误')
        print(f"   错误: {error_msg}")
        if result.get('failed_image'):
            print(f"   失败图片: {result['failed_image']}")
        
        # 显示AI响应（验证错误时）
        if result.get('ai_response_info', {}).get('raw_response'):
            print(f"   🤖 AI完整响应:")
            print(f"      {result['ai_response_info']['raw_response']}")
        
        # 显示部分成功的图片
        if result.get('processed_images'):
            print(f"   ✅ 已处理: {result['processed_images']} 张图片")
        if result.get('partial_results'):
            print(f"   📋 部分结果可用，但最终合并失败")


def _print_import_result(result, image_path, debug=False):
    """打印单个导入结果"""
    if result.get("success", False):
        # 区分成功和带警告的成功
        if result.get("has_warnings", False):
            print(f"⚠️ 导入完成（有警告）: {image_path}")
            print(f"   📄 输出文件: {result['output_file']}")
            print(f"   🎵 歌曲名称: {result['song_name']}")
            print(f"   📊 小节数量: {result['measures_count']}")
            print(f"   🤖 使用服务: {result['provider_used']}")
            print(f"   ⚠️ 警告: {result['warning_message']}")
            
            # 显示AI响应用于调试
            if result.get('ai_response_info', {}).get('raw_response'):
                print(f"   🤖 AI完整响应:")
                print(f"      {result['ai_response_info']['raw_response']}")
        else:
            print(f"✅ 导入成功: {image_path}")
            print(f"   📄 输出文件: {result['output_file']}")
            print(f"   🎵 歌曲名称: {result['song_name']}")
            print(f"   📊 小节数量: {result['measures_count']}")
            print(f"   🤖 使用服务: {result['provider_used']}")
            if result.get('recognition_notes'):
                print(f"   📝 识别备注: {result['recognition_notes']}")
        
        # 显示额外的AI响应信息（debug模式）
        if debug and result.get('raw_response'):
            print(f"   🤖 AI完整响应:")
            print(f"      {result['raw_response']}")
        if result.get('model'):
            print(f"   🔧 AI模型: {result['model']}")
        if result.get('processing_time'):
            print(f"   ⏱️ 处理时间: {result['processing_time']:.2f}秒")
        if result.get('retry_count', 0) > 0:
            print(f"   🔄 重试次数: {result['retry_count']}")
    else:
        print(f"❌ 导入失败: {image_path}")
        error_msg = result.get('error', '未知错误')
        print(f"   错误: {error_msg}")
        
        # 显示AI完整响应（验证错误时的关键信息）
        if result.get('ai_response_info', {}).get('raw_response'):
            print(f"   🤖 AI完整响应:")
            print(f"      {result['ai_response_info']['raw_response']}")
        
        # 简化的验证错误显示
        if "validation failed" in error_msg.lower():
            import re
            match = re.search(r'validation failed:\s*(\[.*\])', error_msg)
            if match:
                try:
                    import ast
                    error_list = ast.literal_eval(match.group(1))
                    if isinstance(error_list, list) and error_list:
                        print(f"   ❌ 验证错误 ({len(error_list)} 个):")
                        for error in error_list[:3]:  # 只显示前3个
                            print(f"      • {error}")
                        if len(error_list) > 3:
                            print(f"      • ... 还有 {len(error_list) - 3} 个错误")
                except (ValueError, SyntaxError):
                    pass



def _print_batch_result(batch_result, debug=False):
    """打印批量导入结果"""
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


def check_ai_status():
    """检查AI服务状态"""
    config = ToolsConfig()
    importer = JianpuSheetImporter(config)
    status = importer.get_provider_status()
    
    print("🤖 AI服务提供商状态:")
    for provider, info in status.items():
        status_icon = "✅" if info['valid'] else "❌"
        config_icon = "🔑" if info['configured'] else "⚪"
        print(f"   {status_icon} {provider:8s} - {info['name']}")
        print(f"      {config_icon} 环境变量: {info['env_key']}")
        print(f"      📋 模型: {info['model']}")
        if not info['configured']:
            print(f"         请设置环境变量 {info['env_key']}")
        print()


def list_songs():
    """列出可用乐曲"""
    # 初始化歌曲管理器
    song_manager = SongManager(songs_dir=Path("songs"))

    print("📋 可用乐曲:")
    for song_key in sorted(song_manager.list_songs()):
        try:
            song = song_manager.get_song(song_key)
            print(f"   {song_key:20s} - {song.name} (BPM: {song.bpm})")
        except Exception as e:
            print(f"   {song_key:20s} - ❌ 加载失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Animal Well 笛子自动演奏")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # play 命令
    play_parser = subparsers.add_parser("play", help="自动演奏")
    play_parser.add_argument("song", help="乐曲名称")
    play_parser.add_argument(
        "--strategy",
        nargs="+",
        default=["optimal"],
        help="映射策略: auto high/low/optimal, manual <offset|song>, none (manual song 使用乐曲文件中的相对偏移量)",
    )
    play_parser.add_argument("--bpm", type=int, help="BPM (覆盖默认值)")
    play_parser.add_argument("--ready-time", type=int, default=5, help="准备时间")

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析乐曲")
    analyze_parser.add_argument("song", help="乐曲名称")

    # import 命令
    import_parser = subparsers.add_parser("import", help="从图片导入简谱")
    import_parser.add_argument("name", nargs="?", default="sheets", 
                              help="图片文件、目录名或文件夹路径 (默认: sheets/) - 同一文件夹中的图片自动合并为一首歌")
    import_parser.add_argument("--ai-provider", choices=["gemini", "doubao"], 
                              help="指定AI服务提供商")
    import_parser.add_argument("--output-dir", help="输出目录 (默认: songs/)")
    import_parser.add_argument("--debug", action="store_true", help="显示详细的AI响应信息")

    # ai-status 命令
    ai_status_parser = subparsers.add_parser("ai-status", help="检查AI服务状态")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出可用乐曲")

    args = parser.parse_args()

    if args.command == "play":
        auto_play(args.song, args.strategy, args.bpm, args.ready_time)
    elif args.command == "analyze":
        analyze_song(args.song)
    elif args.command == "import":
        import_sheet([args.name], args.ai_provider, args.output_dir, args.debug)
    elif args.command == "ai-status":
        check_ai_status()
    elif args.command == "list":
        list_songs()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
