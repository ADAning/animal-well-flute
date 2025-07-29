"""App Header Component for Cosmic Flute TUI"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label


class AppHeader(Horizontal):
    """Application header displaying title and cosmic branding"""
    
    DEFAULT_CSS = """
    AppHeader {
        height: 3;
        background: #1a1f38;
        color: #c0c0c0;
        border: solid #00ffff;
        dock: top;
    }
    
    AppHeader Label {
        text-align: center;
        width: 1fr;
        content-align: center middle;
    }
    
    .app-title {
        color: #00ffff;
        text-style: bold;
    }
    
    .app-subtitle {
        color: #808080;
        text-style: italic;
    }
    """
    
    def __init__(self, show_subtitle: bool = True, **kwargs):
        """Initialize the app header
        
        Args:
            show_subtitle: Whether to show the subtitle
        """
        super().__init__(**kwargs)
        self.show_subtitle = show_subtitle
    
    def compose(self) -> ComposeResult:
        """Compose the header layout"""
        if self.show_subtitle:
            yield Label("🎵 [b]Cosmic Flute[/b] - Animal Well Edition", classes="app-title")
        else:
            yield Label("🎵 [b]Cosmic Flute[/b]", classes="app-title")
        
        # Add some cosmic flair with Unicode characters
        yield Label("✨ Navigate the musical cosmos ✨", classes="app-subtitle")