"""交互式界面基础功能模块"""

from typing import List, Optional, Dict, Any, Callable
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
import sys


class InteractiveManager:
    """交互式界面管理器 - 提供通用的交互式界面功能"""

    def __init__(self):
        self.console = Console()

    def show_welcome(self, title: str = "Animal Well 笛子自动演奏"):
        """显示欢迎信息"""
        welcome_text = Text(title, style="bold cyan")
        panel = Panel(
            welcome_text,
            title="🎵 欢迎",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def show_menu(
        self,
        title: str,
        options: List[Dict[str, str]],
        show_quit: bool = True,
    ) -> Optional[str]:
        """
        显示菜单并获取用户选择

        Args:
            title: 菜单标题
            options: 选项列表，每个选项是包含'key'和'desc'的字典
            show_quit: 是否显示退出选项

        Returns:
            选择的选项key，如果退出则返回None
        """
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        self.console.print()

        # 构建选项映射
        option_map = {}
        for i, option in enumerate(options, 1):
            key = option.get("key", str(i))
            desc = option.get("desc", f"选项 {i}")
            option_map[str(i)] = key
            option_map[key.lower()] = key
            self.console.print(f"  [cyan]{i}[/cyan]. {desc}")

        if show_quit:
            self.console.print(f"  [cyan]q[/cyan]. 退出")
            option_map["q"] = None
            option_map["quit"] = None
            option_map["exit"] = None

        self.console.print()

        while True:
            try:
                choice = (
                    Prompt.ask(
                        "请选择",
                        default="q" if show_quit else "1",
                        show_default=False,
                    )
                    .lower()
                    .strip()
                )

                if choice in option_map:
                    return option_map[choice]
                else:
                    self.console.print("[red]❌ 无效选择，请重新输入[/red]")
            except KeyboardInterrupt:
                return None

    def confirm(self, message: str, default: bool = False) -> bool:
        """显示确认对话框"""
        try:
            return Confirm.ask(message, default=default)
        except KeyboardInterrupt:
            return False

    def show_error(self, message: str):
        """显示错误信息"""
        self.console.print(f"[red]❌ {message}[/red]")

    def show_success(self, message: str):
        """显示成功信息"""
        self.console.print(f"[green]✅ {message}[/green]")

    def show_warning(self, message: str):
        """显示警告信息"""
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")

    def show_info(self, message: str):
        """显示信息"""
        self.console.print(f"[blue]ℹ️ {message}[/blue]")

    def show_progress(self, message: str):
        """显示进度信息"""
        self.console.print(f"[cyan]🔄 {message}[/cyan]")

    def input_text(
        self,
        prompt: str,
        default: Optional[str] = None,
        password: bool = False,
    ) -> Optional[str]:
        """
        获取用户文本输入

        Args:
            prompt: 提示信息
            default: 默认值
            password: 是否为密码输入

        Returns:
            用户输入的文本，取消则返回None
        """
        try:
            return Prompt.ask(
                prompt,
                default=default,
                password=password,
                show_default=bool(default),
            )
        except KeyboardInterrupt:
            return None

    def input_number(
        self,
        prompt: str,
        default: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Optional[float]:
        """
        获取用户数字输入

        Args:
            prompt: 提示信息
            default: 默认值
            min_value: 最小值
            max_value: 最大值

        Returns:
            用户输入的数字，取消则返回None
        """
        while True:
            try:
                value_str = Prompt.ask(
                    prompt,
                    default=str(default) if default is not None else None,
                    show_default=bool(default is not None),
                )

                if value_str is None:
                    return None

                value = float(value_str)

                if min_value is not None and value < min_value:
                    self.show_error(f"输入值不能小于 {min_value}")
                    continue

                if max_value is not None and value > max_value:
                    self.show_error(f"输入值不能大于 {max_value}")
                    continue

                return value

            except ValueError:
                self.show_error("请输入有效的数字")
                continue
            except KeyboardInterrupt:
                return None

    def show_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[str]],
        show_lines: bool = True,
    ):
        """
        显示表格

        Args:
            title: 表格标题
            headers: 表头
            rows: 行数据
            show_lines: 是否显示行分割线
        """
        table = Table(
            title=title,
            show_header=True,
            header_style="bold cyan",
            show_lines=show_lines,
        )

        for header in headers:
            table.add_column(header)

        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def clear_screen(self):
        """清屏"""
        self.console.clear()

    def pause(self, message: str = "按回车键继续..."):
        """暂停等待用户按键"""
        try:
            Prompt.ask(message, default="", show_default=False)
        except KeyboardInterrupt:
            pass

    def exit_gracefully(self, message: str = "再见！"):
        """优雅退出"""
        self.console.print(f"\n[cyan]{message}[/cyan]")
        sys.exit(0)
