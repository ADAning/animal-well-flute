"""居中对齐组件"""

from textual.widget import Widget


class CenterMiddle(Widget, inherit_bindings=False):
    """一个在水平和垂直方向都居中对齐子组件的容器"""

    DEFAULT_CSS = """
    CenterMiddle {
        align: center middle;
        width: 1fr;
        height: 1fr;
    }
    """