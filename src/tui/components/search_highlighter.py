"""搜索高亮器组件"""

import re
from rich.highlighter import Highlighter
from rich.style import Style
from rich.text import Text
from typing import Optional


class SearchHighlighter(Highlighter):
    """搜索结果高亮器，用于高亮搜索匹配的文本"""

    def __init__(self, search_query: Optional[str] = None, highlight_style: str = "bold yellow on blue") -> None:
        """
        初始化搜索高亮器
        
        Args:
            search_query: 搜索查询字符串
            highlight_style: 高亮样式
        """
        super().__init__()
        self.search_query = search_query
        self.highlight_style = highlight_style

    def update_search_query(self, query: Optional[str]) -> None:
        """更新搜索查询"""
        self.search_query = query

    def highlight(self, text: Text) -> None:
        """高亮文本中匹配搜索查询的部分"""
        if not self.search_query or not self.search_query.strip():
            return

        query = self.search_query.strip()
        if not query:
            return

        # 创建不区分大小写的正则表达式
        pattern = re.escape(query)
        regex = re.compile(pattern, re.IGNORECASE)
        
        # 查找所有匹配并高亮
        for match in regex.finditer(text.plain):
            start, end = match.span()
            text.stylize(self.highlight_style, start, end)


def highlight_search_matches(text: str, search_query: Optional[str], highlight_style: str = "bold yellow on blue") -> Text:
    """
    为文本中的搜索匹配项添加高亮
    
    Args:
        text: 要处理的原始文本
        search_query: 搜索查询字符串
        highlight_style: 高亮样式
        
    Returns:
        带有高亮的Text对象
    """
    rich_text = Text(text)
    
    if search_query and search_query.strip():
        query = search_query.strip()
        pattern = re.escape(query)
        regex = re.compile(pattern, re.IGNORECASE)
        
        for match in regex.finditer(text):
            start, end = match.span()
            rich_text.stylize(highlight_style, start, end)
    
    return rich_text


def create_highlighted_song_display(
    song_name: str, 
    description: str, 
    search_query: Optional[str],
    name_style: str = "bold cyan",
    description_style: str = "dim",
    highlight_style: str = "bold yellow on blue"
) -> tuple[Text, Text]:
    """
    创建带有搜索高亮的歌曲显示文本
    
    Args:
        song_name: 歌曲名称
        description: 歌曲描述
        search_query: 搜索查询
        name_style: 歌曲名称基础样式
        description_style: 描述基础样式
        highlight_style: 搜索匹配高亮样式
        
    Returns:
        (高亮的歌曲名称Text, 高亮的描述Text)
    """
    # 创建基础样式的文本
    name_text = Text(song_name, style=name_style)
    desc_text = Text(description, style=description_style)
    
    # 如果有搜索查询，添加高亮
    if search_query and search_query.strip():
        query = search_query.strip()
        pattern = re.escape(query)
        regex = re.compile(pattern, re.IGNORECASE)
        
        # 高亮歌曲名称中的匹配
        for match in regex.finditer(song_name):
            start, end = match.span()
            name_text.stylize(highlight_style, start, end)
        
        # 高亮描述中的匹配
        for match in regex.finditer(description):
            start, end = match.span()
            desc_text.stylize(highlight_style, start, end)
    
    return name_text, desc_text