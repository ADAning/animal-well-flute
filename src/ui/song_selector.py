"""歌曲选择和搜索界面模块"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from difflib import SequenceMatcher

from rich.console import Console
from rich.table import Table
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog

from ..data.songs.song_manager import SongManager


@dataclass
class SongInfo:
    """歌曲信息"""

    key: str
    name: str
    bpm: int
    description: str
    bars: int

    def matches_search(self, query: str) -> bool:
        """检查是否匹配搜索关键词"""
        query = query.lower().strip()
        if not query:
            return True

        # 检查名称
        if query in self.name.lower():
            return True

        # 检查key
        if query in self.key.lower():
            return True

        # 检查描述
        if self.description and query in self.description.lower():
            return True

        # 检查BPM
        if query.isdigit() and str(self.bpm) == query:
            return True

        return False

    def similarity_score(self, query: str) -> float:
        """计算与搜索词的相似度（优先考虑Name匹配）"""
        query = query.lower().strip()
        if not query:
            return 1.0

        # 计算名称相似度（权重更高）
        name_ratio = SequenceMatcher(None, query, self.name.lower()).ratio()

        # 计算key相似度（权重较低，用于兼容性）
        key_ratio = SequenceMatcher(None, query, self.key.lower()).ratio() * 0.8

        # 检查是否包含关键词（Name匹配的bonus更高）
        if query in self.name.lower():
            contains_bonus = 0.5
        elif query in self.key.lower():
            contains_bonus = 0.3
        else:
            contains_bonus = 0

        return max(name_ratio, key_ratio) + contains_bonus


class SongCompleter(Completer):
    """歌曲名称自动补全"""

    def __init__(self, songs: List[SongInfo]):
        self.songs = songs

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lower()

        for song in self.songs:
            # 只基于歌曲名称进行补全，交互界面不需要暴露key概念
            if text in song.name.lower():
                yield Completion(
                    song.name,
                    start_position=-len(text),
                    display=f"{song.name} (BPM: {song.bpm})",
                )


class SongSelector:
    """歌曲选择器 - 提供交互式歌曲选择和搜索功能"""

    def __init__(self, song_manager: SongManager):
        self.song_manager = song_manager
        self.console = Console()
        self.songs: List[SongInfo] = []
        self.filtered_songs: List[SongInfo] = []
        self.current_search = ""
        self.selected_index = 0
        self.page_size = 10
        self.current_page = 0

        self._load_songs()

    def _load_songs(self):
        """加载所有歌曲信息"""
        self.songs = []

        # 使用新的list_songs_with_info方法获取详细信息
        try:
            songs_info = self.song_manager.list_songs_with_info()
            for song_info_dict in songs_info:
                song_info = SongInfo(
                    key=song_info_dict["key"],
                    name=song_info_dict["name"],
                    bpm=int(song_info_dict["bpm"]),
                    description=song_info_dict["description"],
                    bars=int(song_info_dict["bars"]),
                )
                self.songs.append(song_info)
        except Exception:
            # 如果新方法失败，回退到旧方法
            for song_key in self.song_manager.list_songs():
                try:
                    song = self.song_manager.get_song(song_key)
                    song_info = SongInfo(
                        key=song_key,
                        name=song.name,
                        bpm=song.bpm,
                        description=song.description or "",
                        bars=len(song.jianpu),
                    )
                    self.songs.append(song_info)
                except Exception as e:
                    # 忽略加载失败的歌曲
                    continue

        # 按名称排序
        self.songs.sort(key=lambda x: x.name)
        self.filtered_songs = self.songs.copy()

    def search_songs(self, query: str) -> List[SongInfo]:
        """搜索歌曲"""
        if not query.strip():
            return self.songs

        # 过滤匹配的歌曲
        matching_songs = [song for song in self.songs if song.matches_search(query)]

        # 按相似度排序
        matching_songs.sort(key=lambda x: x.similarity_score(query), reverse=True)

        return matching_songs

    def select_song_simple(
        self,
        prompt_text: str = "选择歌曲",
        for_playing: bool = False,
        auto_confirm: bool = False,
    ) -> Optional[str]:
        """简单的歌曲选择界面 - 使用序号选择（与analyze/play相同的动态搜索）

        Args:
            prompt_text: 提示文本
            for_playing: 是否用于演奏目的（影响单首歌匹配时的询问文本）
            auto_confirm: 是否自动确认唯一匹配结果（不询问用户）
        """
        if not self.songs:
            self.console.print("[red]❌ 没有可用的歌曲[/red]")
            return None

        while True:
            # 显示搜索提示
            self.console.print(f"\n[bold cyan]{prompt_text}[/bold cyan]")
            self.console.print("[dim]输入关键词搜索歌曲[/dim]")

            # 获取搜索输入
            try:
                search_query = prompt(
                    "搜索: ",
                    completer=SongCompleter(self.songs),
                    complete_while_typing=True,
                ).strip()
            except KeyboardInterrupt:
                return None

            # 搜索歌曲
            if search_query:
                filtered_songs = self.search_songs(search_query)
            else:
                filtered_songs = self.songs

            if not filtered_songs:
                self.console.print("[red]❌ 没有找到匹配的歌曲[/red]")
                continue

            # 显示搜索结果
            self._display_song_list(filtered_songs, max_display=20)

            # 获取用户选择
            if len(filtered_songs) == 1:
                # 只有一个结果
                self.console.print(
                    f"\n[cyan]找到唯一匹配: {filtered_songs[0].name}[/cyan]"
                )

                # 如果设置了自动确认，直接返回结果
                if auto_confirm:
                    return filtered_songs[0].name

                # 否则询问是否选择或演奏
                try:
                    if for_playing:
                        confirm = prompt("是否要现在演奏? (y/n): ").lower().strip()
                    else:
                        confirm = prompt("选择这首歌? (y/n): ").lower().strip()
                    if confirm in ["y", "yes", "是", ""]:
                        return filtered_songs[0].name
                except KeyboardInterrupt:
                    return None
            else:
                # 多个结果，让用户选择
                try:
                    choice = prompt(
                        f"请选择 (1-{len(filtered_songs)}), 或输入新的搜索词, 或 'q' 退出: "
                    ).strip()

                    if choice.lower() in ["q", "quit", "exit"]:
                        return None

                    # 尝试解析为数字
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(filtered_songs):
                            return filtered_songs[index].name
                        else:
                            self.console.print("[red]❌ 无效的序号[/red]")
                    except ValueError:
                        # 不是数字，当作新的搜索词
                        search_query = choice
                        continue

                except KeyboardInterrupt:
                    return None

    def select_song_advanced(self, prompt_text: str = "选择歌曲") -> Optional[str]:
        """高级的歌曲选择界面 - 使用radiolist对话框"""
        if not self.songs:
            self.console.print("[red]❌ 没有可用的歌曲[/red]")
            return None

        # 获取搜索关键词
        try:
            search_query = input_dialog(
                title="歌曲搜索", text="输入搜索关键词 (留空显示所有歌曲):"
            ).run()

            if search_query is None:  # 用户取消
                return None

        except KeyboardInterrupt:
            return None

        # 搜索歌曲
        if search_query and search_query.strip():
            filtered_songs = self.search_songs(search_query.strip())
        else:
            filtered_songs = self.songs

        if not filtered_songs:
            self.console.print("[red]❌ 没有找到匹配的歌曲[/red]")
            return None

        # 构建选项列表
        values = []
        for song in filtered_songs[:50]:  # 限制最多50个选项避免界面过长
            display_text = f"{song.name} (BPM: {song.bpm})"
            if song.description:
                display_text += f" - {song.description[:30]}..."
            values.append((song.name, display_text))

        # 显示选择对话框
        try:
            result = radiolist_dialog(
                title=prompt_text,
                text=f"找到 {len(filtered_songs)} 首歌曲"
                + (f" (显示前50首)" if len(filtered_songs) > 50 else ""),
                values=values,
            ).run()

            return result

        except KeyboardInterrupt:
            return None

    def _display_song_list_paginated(
        self, songs: List[SongInfo], page: int = 0, page_size: int = 20
    ):
        """分页显示歌曲列表"""
        if not songs:
            self.console.print("[red]没有歌曲可显示[/red]")
            return

        total_pages = (len(songs) - 1) // page_size + 1
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(songs))
        display_songs = songs[start_idx:end_idx]

        # 创建表格
        page_info = f"第 {page + 1}/{total_pages} 页" if total_pages > 1 else ""
        table = Table(
            title=f"歌曲列表 (共 {len(songs)} 首) {page_info}",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )

        table.add_column("序号", style="cyan", width=6)
        table.add_column("歌曲名称", style="bold", min_width=20)
        table.add_column("BPM", style="green", width=6)
        table.add_column("小节数", style="yellow", width=6)
        table.add_column("描述", style="dim", min_width=20)

        # 添加行数据，序号保持全局序号
        for i, song in enumerate(display_songs):
            global_idx = start_idx + i + 1
            description = (
                song.description[:30] + "..."
                if len(song.description) > 30
                else song.description
            )
            table.add_row(
                str(global_idx),
                song.name,
                str(song.bpm),
                str(song.bars),
                description or "[dim]无描述[/dim]",
            )

        self.console.print(table)

        # 显示翻页提示
        if total_pages > 1:
            nav_tips = []
            if page > 0:
                nav_tips.append("'p' 或 'prev' 上一页")
            if page < total_pages - 1:
                nav_tips.append("'n' 或 'next' 下一页")
            if nav_tips:
                self.console.print(f"[dim]导航: {' | '.join(nav_tips)}[/dim]")

    def _display_song_list(self, songs: List[SongInfo], max_display: int = 20):
        """显示歌曲列表 - 保持向后兼容"""
        self._display_song_list_paginated(songs, page=0, page_size=max_display)

    def get_song_info(self, song_key: str) -> Optional[Dict]:
        """获取歌曲详细信息"""
        try:
            return self.song_manager.get_song_info(song_key)
        except Exception:
            return None

    def list_all_songs(self) -> Optional[str]:
        """列出所有歌曲 - 支持翻页浏览（直接按键响应）"""
        if not self.songs:
            self.console.print("[red]❌ 没有可用的歌曲[/red]")
            return None

        import sys

        current_page = 0
        page_size = 20
        total_pages = (len(self.songs) - 1) // page_size + 1

        def get_single_char():
            """获取单个字符输入（不需要回车）- 跨平台兼容"""
            if sys.platform == "win32":
                try:
                    import msvcrt

                    # Windows: 使用msvcrt.getch()获取单字符
                    while True:
                        if msvcrt.kbhit():
                            char = msvcrt.getch()
                            if isinstance(char, bytes):
                                try:
                                    return char.decode("utf-8").lower()
                                except UnicodeDecodeError:
                                    # 处理特殊键如方向键
                                    if char == b"\xe0":  # 扩展键前缀
                                        msvcrt.getch()  # 读取后续字符
                                    continue
                            return char.lower()
                except ImportError:
                    return None
            else:
                try:
                    import tty
                    import termios

                    # Unix系统: 使用termios/tty
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.cbreak(fd)
                        char = sys.stdin.read(1).lower()
                        return char
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except (ImportError, OSError, AttributeError):
                    return None
            return None

        while True:
            # 清屏并显示当前页
            self.console.clear()
            self._display_song_list_paginated(
                self.songs, page=current_page, page_size=page_size
            )

            # 显示导航提示
            nav_tips = []
            if current_page > 0:
                nav_tips.append("[cyan]p[/cyan] 上一页")
            if current_page < total_pages - 1:
                nav_tips.append("[cyan]n[/cyan] 下一页")
            nav_tips.append("[cyan]s[/cyan] 选择歌曲")
            nav_tips.append("[cyan]q[/cyan] 退出")

            self.console.print(f"\n[dim]导航: {' | '.join(nav_tips)}[/dim]")
            self.console.print("[dim]请按键 (无需回车):[/dim]", end=" ")

            try:
                # 获取单个字符
                char = get_single_char()

                if char is None:
                    # 如果直接按键不可用，回退到传统方式
                    self.console.print(
                        "\n[yellow]直接按键不可用，使用传统输入模式[/yellow]"
                    )
                    choice = (
                        prompt("请输入 p(上一页)/n(下一页)/s(选择歌曲)/q(退出): ")
                        .strip()
                        .lower()
                    )
                    if choice == "q":
                        break
                    elif choice == "p" and current_page > 0:
                        current_page -= 1
                    elif choice == "n" and current_page < total_pages - 1:
                        current_page += 1
                    elif choice == "s":
                        return self._select_song_from_list(current_page, page_size)
                    continue

                if char == "q":
                    break
                elif char == "p" and current_page > 0:
                    current_page -= 1
                elif char == "n" and current_page < total_pages - 1:
                    current_page += 1
                elif char == "s":
                    return self._select_song_from_list(current_page, page_size)
                elif char == "\x03":  # Ctrl+C
                    break
                # 忽略其他按键

            except KeyboardInterrupt:
                break
            except Exception as e:
                # 处理其他异常，回退到传统方式
                self.console.print(
                    f"\n[yellow]按键输入出错 ({str(e)})，使用传统输入模式[/yellow]"
                )
                try:
                    choice = (
                        prompt("请输入 p(上一页)/n(下一页)/s(选择歌曲)/q(退出): ")
                        .strip()
                        .lower()
                    )
                    if choice == "q":
                        break
                    elif choice == "p" and current_page > 0:
                        current_page -= 1
                    elif choice == "n" and current_page < total_pages - 1:
                        current_page += 1
                    elif choice == "s":
                        return self._select_song_from_list(current_page, page_size)
                except KeyboardInterrupt:
                    break

        return None

    def _select_song_from_list(
        self, current_page: int, page_size: int
    ) -> Optional[str]:
        """从当前页面选择歌曲"""
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(self.songs))
        page_songs = self.songs[start_idx:end_idx]

        self.console.print("\n[cyan]请选择歌曲:[/cyan]")
        try:
            choice = (
                prompt(f"请输入歌曲序号 (1-{len(page_songs)}) 或 'c' 取消: ")
                .strip()
                .lower()
            )

            if choice == "c":
                return None

            try:
                index = int(choice) - 1
                if 0 <= index < len(page_songs):
                    selected_song = page_songs[index]
                    self.console.print(f"\n[green]已选择: {selected_song.name}[/green]")
                    return selected_song.name
                else:
                    self.console.print("[red]❌ 无效的序号[/red]")
                    return None
            except ValueError:
                self.console.print("[red]❌ 请输入有效的数字[/red]")
                return None

        except KeyboardInterrupt:
            return None

    def search_and_display(self, query: str):
        """搜索并显示结果"""
        filtered_songs = self.search_songs(query)
        self.console.print(f"\n[cyan]搜索 '{query}' 的结果:[/cyan]")
        self._display_song_list(filtered_songs)
