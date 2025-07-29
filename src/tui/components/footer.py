"""App Footer Component for Cosmic Flute TUI"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer as TextualFooter, Label


class AppFooter(Horizontal):
    """Application footer displaying keybindings and status"""
    
    DEFAULT_CSS = """
    AppFooter {
        height: 3;
        background: #1a1f38;
        color: #c0c0c0;
        border: solid #00ffff;
        dock: bottom;
    }
    
    AppFooter Label {
        padding: 0 1;
        content-align: center middle;
    }
    
    .keybinding {
        color: #00ffff;
        text-style: bold;
    }
    
    .separator {
        color: #808080;
    }
    """
    
    def __init__(self, keybindings: list[tuple[str, str]] = None, **kwargs):
        """Initialize the app footer
        
        Args:
            keybindings: List of (key, description) tuples to display
        """
        super().__init__(**kwargs)
        self.keybindings = keybindings or [
            ("Enter", "Select"),
            ("Esc", "Back"),
            ("F1", "Help"),
            ("Ctrl+Q", "Quit")
        ]
    
    def compose(self) -> ComposeResult:
        """Compose the footer layout"""
        # Create keybinding display
        keybinding_parts = []
        for key, desc in self.keybindings:
            keybinding_parts.append(f"[b cyan]{key}[/b cyan] {desc}")
        
        keybinding_text = " [dim]|[/dim] ".join(keybinding_parts)
        yield Label(keybinding_text, classes="keybinding")
    
    def update_keybindings(self, keybindings: list[tuple[str, str]]) -> None:
        """Update the displayed keybindings
        
        Args:
            keybindings: New list of (key, description) tuples
        """
        self.keybindings = keybindings
        
        # Update the label content
        keybinding_parts = []
        for key, desc in self.keybindings:
            keybinding_parts.append(f"[b cyan]{key}[/b cyan] {desc}")
        
        keybinding_text = " [dim]|[/dim] ".join(keybinding_parts)
        
        # Find and update the label
        try:
            label = self.query_one(Label)
            label.update(keybinding_text)
        except:
            # If we can't find the label, just ignore the update
            pass


class CosmicFooter(TextualFooter):
    """Enhanced footer with cosmic styling"""
    
    DEFAULT_CSS = """
    CosmicFooter {
        background: #1a1f38;
        color: #c0c0c0;
        height: 1;
    }
    
    CosmicFooter .footer--highlight {
        background: #00ffff;
        color: #0a0f28;
    }
    
    CosmicFooter .footer--highlight-key {
        background: #ff00ff;
        color: #0a0f28;
        text-style: bold;
    }
    """