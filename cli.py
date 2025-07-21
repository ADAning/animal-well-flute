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
from src.ui import InteractiveManager, SongSelector
import time
from pathlib import Path
import glob


def auto_play(
    song_name, strategy_args=["optimal"], bpm=None, ready_time=None, interactive=False
):
    """自动演奏功能"""

    # 获取配置
    config = get_app_config()

    # 设置日志
    setup_logging(config.log_level)

    # 获取共享的歌曲管理器
    song_manager = get_song_manager(config.songs_dir)

    # 交互式选择歌曲
    if interactive or song_name is None:
        ui_manager = InteractiveManager()
        song_selector = SongSelector(song_manager)

        ui_manager.show_welcome()
        selected_song_key = song_selector.select_song_simple("🎵 选择要演奏的歌曲")

        if selected_song_key is None:
            ui_manager.show_info("演奏已取消")
            return False

        song_name = selected_song_key

    try:
        song = song_manager.get_song(song_name)
    except Exception as e:
        print(f"❌ 乐曲 '{song_name}' 不存在")
        song_names = song_manager.list_song_names()
        print(f"📋 可用乐曲: {', '.join(song_names)}")
        return False
    final_bpm = bpm or song.bpm or config.default_bpm
    final_ready_time = (
        ready_time if ready_time is not None else config.default_ready_time
    )

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


def analyze_song(song_name, interactive=False):
    """分析乐曲"""

    # 获取配置
    config = get_app_config()

    # 获取共享的歌曲管理器
    song_manager = get_song_manager(config.songs_dir)

    # 交互式选择歌曲
    if interactive or song_name is None:
        ui_manager = InteractiveManager()
        song_selector = SongSelector(song_manager)

        ui_manager.show_welcome()
        selected_song_key = song_selector.select_song_simple("🎼 选择要分析的歌曲")

        if selected_song_key is None:
            ui_manager.show_info("分析已取消")
            return False

        song_name = selected_song_key

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
            output_dir=Path(output_dir) if output_dir else config.songs_dir, debug=debug
        )

        # 执行导入
        result = coordinator.coordinate_import(image_paths, ai_provider)

        # 处理AI服务配置错误
        if (
            not result.success
            and result.error
            and "未配置任何AI服务提供商" in result.error
        ):
            print("❌ 未配置任何AI服务提供商")
            print("请设置以下环境变量之一:")
            if hasattr(result, "provider_status"):
                for provider, info in result.provider_status.items():
                    print(f"   {info['env_key']} - {info['name']}")
            return False

        # 处理AI服务提供商不可用错误
        if not result.success and result.error and "不可用" in result.error:
            print(f"❌ {result.error}")
            if hasattr(result, "available_providers"):
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
        status_icon = "✅" if info["valid"] else "❌"
        config_icon = "🔑" if info["configured"] else "⚪"
        print(f"   {status_icon} {provider:8s} - {info['name']}")
        print(f"      {config_icon} 环境变量: {info['env_key']}")
        print(f"      📋 模型: {info['model']}")
        if not info["configured"]:
            print(f"         请设置环境变量 {info['env_key']}")
        print()


def interactive_list_songs():
    """交互式歌曲列表浏览功能 - 使用与analyze/play相同的动态选择界面"""
    # 获取配置和组件
    config = get_app_config()
    song_manager = get_song_manager(config.songs_dir)
    ui_manager = InteractiveManager()
    song_selector = SongSelector(song_manager)

    ui_manager.show_welcome("歌曲列表浏览")

    while True:
        options = [
            {"key": "browse", "desc": "🎵 浏览和选择歌曲 (动态搜索)"},
            {"key": "list", "desc": "📋 显示所有歌曲 (静态列表)"},
        ]

        choice = ui_manager.show_menu("歌曲浏览模式", options, show_quit=True)

        if choice is None:
            break

        try:
            if choice == "browse":
                # 使用与analyze/play相同的动态选择界面
                ui_manager.show_info("进入动态歌曲浏览模式...")
                ui_manager.show_info(
                    "💡 提示: 输入关键词可实时搜索，输入数字可直接选择"
                )

                # 使用SongSelector的select_song_simple方法，这与analyze/play使用的是同一个
                selected_song = song_selector.select_song_simple(
                    "🎵 浏览歌曲 (支持实时搜索)"
                )

                if selected_song:
                    ui_manager.show_success(f"您选择了: {selected_song}")

                    # 显示歌曲详细信息
                    try:
                        song = song_manager.get_song(selected_song)
                        ui_manager.show_info(f"🎼 歌曲名称: {song.name}")
                        ui_manager.show_info(f"🎵 BPM: {song.bpm}")
                        if song.description:
                            ui_manager.show_info(f"📝 描述: {song.description}")
                        ui_manager.show_info(f"📊 小节数: {len(song.jianpu)}")

                        # 询问是否要演奏
                        if ui_manager.confirm("🎹 是否要演奏这首歌？", default=True):
                            ui_manager.show_progress("准备演奏...")

                            # 询问演奏参数
                            play_options = [
                                {"key": "default", "desc": "🎵 使用默认设置演奏"},
                                {"key": "custom", "desc": "⚙️ 自定义演奏参数"},
                            ]

                            play_choice = ui_manager.show_menu(
                                "演奏选项", play_options, show_quit=False
                            )

                            # 准备演奏参数
                            strategy_args = ["optimal"]  # 默认策略
                            bpm = None  # 使用歌曲默认BPM
                            ready_time = None  # 使用配置默认准备时间

                            if play_choice == "custom":
                                # 自定义参数
                                strategy_options = [
                                    {"key": "optimal", "desc": "🎯 最佳策略 (推荐)"},
                                    {"key": "high", "desc": "⬆️ 高音优先策略"},
                                    {"key": "low", "desc": "⬇️ 低音优先策略"},
                                ]

                                strategy_choice = ui_manager.show_menu(
                                    "选择演奏策略", strategy_options, show_quit=False
                                )
                                if strategy_choice:
                                    strategy_args = [strategy_choice]

                                # 可选的BPM设置
                                custom_bpm = ui_manager.input_number(
                                    f"自定义BPM (当前: {song.bpm}, 留空使用默认)",
                                    default=None,
                                    min_value=30,
                                    max_value=300,
                                )
                                if custom_bpm:
                                    bpm = int(custom_bpm)

                                # 可选的准备时间
                                custom_ready_time = ui_manager.input_number(
                                    "准备时间(秒) (留空使用默认)",
                                    default=None,
                                    min_value=0,
                                    max_value=30,
                                )
                                if custom_ready_time is not None:
                                    ready_time = int(custom_ready_time)

                            # 执行演奏
                            ui_manager.show_info("🎼 开始演奏...")
                            try:
                                result = auto_play(
                                    selected_song,
                                    strategy_args,
                                    bpm,
                                    ready_time,
                                    interactive=False,
                                )
                                if result:
                                    ui_manager.show_success("🎉 演奏完成！")
                                else:
                                    ui_manager.show_warning("演奏未完成")
                            except Exception as e:
                                ui_manager.show_error(f"演奏时发生错误: {e}")
                        else:
                            ui_manager.show_info("已取消演奏")

                    except Exception as e:
                        ui_manager.show_warning(f"无法获取歌曲详细信息: {e}")
                else:
                    ui_manager.show_info("未选择歌曲")

                ui_manager.pause()

            elif choice == "list":
                # 显示所有歌曲的静态列表
                ui_manager.show_info("正在加载歌曲列表...")
                song_selector.list_all_songs()
                ui_manager.pause()

        except KeyboardInterrupt:
            ui_manager.show_info("\n操作已取消")
            break
        except Exception as e:
            ui_manager.show_error(f"执行操作时发生错误: {e}")
            ui_manager.pause()

    ui_manager.exit_gracefully()


def list_songs(interactive=False):
    """列出可用乐曲"""
    if interactive:
        interactive_list_songs()
        return

    # 原有的非交互式实现
    config = get_app_config()
    song_manager = get_song_manager(config.songs_dir)

    print("📋 可用乐曲:")
    songs_info = song_manager.list_songs_with_info()
    for song_info in songs_info:
        name = song_info["name"]
        bpm = song_info["bpm"]
        description = song_info["description"]
        desc_text = f" - {description[:40]}..." if description else ""
        print(f"   {name:<25} (BPM: {bpm}){desc_text}")


def interactive_main_menu():
    """交互式主菜单"""
    ui_manager = InteractiveManager()

    ui_manager.show_welcome("Animal Well 笛子自动演奏 - 交互式模式")

    while True:
        options = [
            {"key": "play", "desc": "🎵 自动演奏歌曲"},
            {"key": "analyze", "desc": "🎼 分析歌曲"},
            {"key": "list", "desc": "📋 列出所有歌曲"},
            {"key": "import", "desc": "📸 从图片导入简谱"},
            {"key": "ai-status", "desc": "🤖 检查AI服务状态"},
        ]

        choice = ui_manager.show_menu("主菜单", options, show_quit=True)

        if choice is None:
            ui_manager.exit_gracefully()

        try:
            if choice == "play":
                auto_play(None, interactive=True)
            elif choice == "analyze":
                analyze_song(None, interactive=True)
            elif choice == "list":
                # 在交互式主菜单中默认使用交互式列表
                list_songs(interactive=True)
            elif choice == "import":
                ui_manager.show_info("进入图片导入功能...")
                # 这里可以添加交互式的导入功能
                ui_manager.show_warning("交互式导入功能开发中，请使用命令行模式")
                ui_manager.pause()
            elif choice == "ai-status":
                check_ai_status()
                ui_manager.pause()
        except KeyboardInterrupt:
            ui_manager.show_info("\n操作已取消")
        except Exception as e:
            ui_manager.show_error(f"执行命令时发生错误: {e}")
            ui_manager.pause()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Animal Well 笛子自动演奏")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # play 命令
    play_parser = subparsers.add_parser("play", help="自动演奏")
    play_parser.add_argument(
        "song", nargs="?", help="乐曲名称（可选，留空则进入交互式选择）"
    )
    play_parser.add_argument(
        "--strategy",
        nargs="+",
        default=["optimal"],
        help="映射策略: auto high/low/optimal, manual <offset|song>, none (manual song 使用乐曲文件中的相对偏移量)",
    )
    play_parser.add_argument("--bpm", type=int, help="BPM (覆盖默认值)")
    play_parser.add_argument(
        "--ready-time", type=int, help="准备时间（默认从配置读取）"
    )
    play_parser.add_argument(
        "--interactive", "-i", action="store_true", help="使用交互式模式选择歌曲"
    )

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析乐曲")
    analyze_parser.add_argument(
        "song", nargs="?", help="乐曲名称（可选，留空则进入交互式选择）"
    )
    analyze_parser.add_argument(
        "--interactive", "-i", action="store_true", help="使用交互式模式选择歌曲"
    )

    # import 命令
    import_parser = subparsers.add_parser("import", help="从图片导入简谱")
    import_parser.add_argument(
        "name",
        nargs="?",
        default="sheets",
        help="图片文件、目录名或文件夹路径 (默认: sheets/) - 同一文件夹中的图片自动合并为一首歌",
    )
    import_parser.add_argument(
        "--ai-provider", choices=["gemini", "doubao"], help="指定AI服务提供商"
    )
    import_parser.add_argument("--output-dir", help="输出目录（默认从配置读取）")
    import_parser.add_argument(
        "--debug", action="store_true", help="显示详细的AI响应信息"
    )
    import_parser.add_argument(
        "--interactive", "-i", action="store_true", help="使用交互式模式选择文件和选项"
    )

    # ai-status 命令
    ai_status_parser = subparsers.add_parser("ai-status", help="检查AI服务状态")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出可用乐曲")
    list_parser.add_argument(
        "--interactive", "-i", action="store_true", help="使用交互式模式浏览和搜索歌曲"
    )

    # interactive 命令
    interactive_parser = subparsers.add_parser("interactive", help="进入交互式主菜单")

    args = parser.parse_args()

    if args.command == "play":
        auto_play(args.song, args.strategy, args.bpm, args.ready_time, args.interactive)
    elif args.command == "analyze":
        analyze_song(args.song, args.interactive)
    elif args.command == "import":
        if args.interactive:
            # 目前交互式导入功能开发中，显示提示信息
            ui_manager = InteractiveManager()
            ui_manager.show_welcome()
            ui_manager.show_warning("交互式导入功能开发中")
            ui_manager.show_info("请使用命令行模式: python cli.py import [path]")
            ui_manager.show_info(
                "例如: python cli.py import sheets/ --ai-provider gemini"
            )
        else:
            import_sheet([args.name], args.ai_provider, args.output_dir, args.debug)
    elif args.command == "ai-status":
        check_ai_status()
    elif args.command == "list":
        list_songs(args.interactive)
    elif args.command == "interactive":
        interactive_main_menu()
    else:
        # 没有指定命令时，显示帮助信息并询问是否进入交互式模式
        parser.print_help()
        print("\n" + "=" * 50)
        print("💡 提示：您可以使用以下方式:")
        print("   - 直接使用命令行参数（如上所示）")
        print("   - 运行 'python cli.py interactive' 进入交互式模式")
        print("   - 运行 'python cli.py play --interactive' 交互式选择歌曲")

        try:
            from rich.prompt import Confirm

            if Confirm.ask("\n是否现在进入交互式模式？", default=False):
                interactive_main_menu()
        except ImportError:
            # 如果rich不可用，回退到简单提示
            pass
        except KeyboardInterrupt:
            print("\n再见！")


if __name__ == "__main__":
    main()
