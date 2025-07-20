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
from src.utils.song_service import get_song_manager
from src.utils.logger import setup_logging
from src.utils.import_coordinator import ImportCoordinator
from src.utils.result_display import ImportResultDisplay
from src.config import get_app_config
from src.tools import JianpuSheetImporter, ToolsConfig
import time
from pathlib import Path
import glob


def auto_play(song_name, strategy_args=["optimal"], bpm=None, ready_time=None):
    """自动演奏功能"""
    
    # 获取配置
    config = get_app_config()

    # 设置日志
    setup_logging(config.log_level)

    # 获取共享的歌曲管理器
    song_manager = get_song_manager(config.songs_dir)

    try:
        song = song_manager.get_song(song_name)
    except Exception as e:
        print(f"❌ 乐曲 '{song_name}' 不存在")
        print(f"📋 可用乐曲: {', '.join(song_manager.list_songs())}")
        return False
    final_bpm = bpm or song.bpm or config.default_bpm
    final_ready_time = ready_time if ready_time is not None else config.default_ready_time

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

    print(f"⏱️ 准备时间: {final_ready_time} 秒")
    print("🎹 请切换到游戏窗口...")

    for i in range(final_ready_time, 0, -1):
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
    
    # 获取配置
    config = get_app_config()

    # 获取共享的歌曲管理器
    song_manager = get_song_manager(config.songs_dir)

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
        # 获取配置
        config = get_app_config()
        
        # 设置日志
        setup_logging(config.log_level)
        
        # 使用导入协调器处理整个流程
        coordinator = ImportCoordinator(
            output_dir=Path(output_dir) if output_dir else config.songs_dir,
            debug=debug
        )
        
        # 执行导入
        result = coordinator.coordinate_import(image_paths, ai_provider)
        
        # 处理AI服务配置错误
        if not result.success and result.error and "未配置任何AI服务提供商" in result.error:
            print("❌ 未配置任何AI服务提供商")
            print("请设置以下环境变量之一:")
            if hasattr(result, 'provider_status'):
                for provider, info in result.provider_status.items():
                    print(f"   {info['env_key']} - {info['name']}")
            return False
        
        # 处理AI服务提供商不可用错误
        if not result.success and result.error and "不可用" in result.error:
            print(f"❌ {result.error}")
            if hasattr(result, 'available_providers'):
                print(f"可用的服务商: {', '.join(result.available_providers)}")
            return False
        
        # 处理其他错误
        if not result.success:
            print(f"❌ {result.error}")
            return False
        
        # 显示结果
        ImportResultDisplay.display_import_results(result, debug)
        
        return (result.total_success + result.total_warnings) > 0
    
    except Exception as e:
        print(f"\n💥 导入过程中发生未预期的异常: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False


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
    # 获取配置和共享的歌曲管理器
    config = get_app_config()
    song_manager = get_song_manager(config.songs_dir)

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
    play_parser.add_argument("--ready-time", type=int, help="准备时间（默认从配置读取）")

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析乐曲")
    analyze_parser.add_argument("song", help="乐曲名称")

    # import 命令
    import_parser = subparsers.add_parser("import", help="从图片导入简谱")
    import_parser.add_argument("name", nargs="?", default="sheets", 
                              help="图片文件、目录名或文件夹路径 (默认: sheets/) - 同一文件夹中的图片自动合并为一首歌")
    import_parser.add_argument("--ai-provider", choices=["gemini", "doubao"], 
                              help="指定AI服务提供商")
    import_parser.add_argument("--output-dir", help="输出目录（默认从配置读取）")
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
