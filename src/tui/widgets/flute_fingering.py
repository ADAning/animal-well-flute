"""Flute Fingering Widget for visualizing game input"""

from typing import Optional, Dict, List, Any
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from textual.reactive import reactive

from ...utils.logger import get_logger

logger = get_logger(__name__)


class FluteFingeringWidget(Widget):
    """Widget for displaying flute fingering patterns for game input"""
    
    DEFAULT_CSS = """
    FluteFingeringWidget {
        border: solid #ff00ff;
        border-title-style: bold;
        border-title-color: #ff00ff;
        border-title-align: center;
        height: 20;
        width: 1fr;
        padding: 1;
    }
    
    .fingering-display {
        color: #c0c0c0;
        text-align: center;
    }
    
    .active-key {
        color: #00ffff;
        text-style: bold;
        background: #00ffff 20%;
    }
    
    .inactive-key {
        color: #808080;
        text-style: dim;
    }
    
    .unplayable {
        color: #ff4444;
        text-style: strike;
    }
    """
    
    # Reactive attributes
    current_keys: reactive[List[str]] = reactive([], init=False)
    
    def __init__(self, **kwargs):
        """Initialize the flute fingering widget"""
        super().__init__(**kwargs)
        self.current_note = None
        # Set border title
        self.border_title = "🎹 Flute Controls"
        
        # Mapping of directions to visual representations
        self.direction_map = {
            'up': '↑',
            'down': '↓', 
            'left': '←',
            'right': '→',
            'up_left': '↖',
            'up_right': '↗',
            'down_left': '↙',
            'down_right': '↘'
        }
        
        # Create visual flute layout
        self.flute_layout = self._create_flute_layout()
    
    def compose(self):
        """Compose the widget layout"""
        with Vertical(id="fingering-container"):
            yield Static(self._get_default_display(), id="fingering-display", classes="fingering-display")
    
    def _create_flute_layout(self) -> str:
        """Create the ASCII art flute layout"""
        return """
        🎺 Animal Well Flute 🎺
        
    ┌─────────────────────────┐
    │     ↖  ↑  ↗            │
    │      \\ │ /              │
    │   ← ── ● ── →           │
    │      / │ \\              │
    │     ↙  ↓  ↘            │
    └─────────────────────────┘
    
    8-Direction Input System:
    Each note maps to directional input
    combinations for in-game performance.
        """
    
    def _get_default_display(self) -> str:
        """Get the default display when no note is selected"""
        return f"{self.flute_layout}\n\n🎵 Select a note to see its fingering pattern"
    
    def show_fingering(self, note: Any) -> None:
        """Show fingering pattern for a specific note
        
        Args:
            note: The note to display fingering for
        """
        self.current_note = note
        
        if not note:
            self.reset_display()
            return
        
        # Get key combination from note
        if hasattr(note, 'key_combination') and note.key_combination:
            self.current_keys = note.key_combination
            display_content = self._create_fingering_display(note)
        else:
            # Rest or unplayable note
            display_content = self._create_rest_display(note)
        
        self.update_display(display_content)
    
    def _create_fingering_display(self, note: Any) -> str:
        """Create the fingering display for a playable note
        
        Args:
            note: The note to create display for
            
        Returns:
            Formatted display string
        """
        lines = []
        
        # Title
        lines.append("🎹 Current Note Fingering")
        lines.append("=" * 25)
        lines.append("")
        
        # Note information
        if hasattr(note, 'physical_height'):
            lines.append(f"Physical Height: {note.physical_height:.1f}")
        
        if hasattr(note, 'notation'):
            lines.append(f"Notation: {note.notation}")
        
        if hasattr(note, 'time_factor'):
            lines.append(f"Duration: {note.time_factor:.1f}")
        
        lines.append("")
        
        # Key combination display
        if self.current_keys:
            lines.append("🎯 Press these keys:")
            lines.append("")
            
            # Create visual representation
            visual = self._create_key_visual(self.current_keys)
            lines.extend(visual.split('\n'))
            
            lines.append("")
            lines.append("Key sequence:")
            for i, key in enumerate(self.current_keys, 1):
                direction_symbol = self.direction_map.get(key, key)
                if key in ['1', '3']:
                    # Special handling for modifier keys
                    modifier_desc = "Lower octave" if key == '1' else "Sharp/flat"
                    lines.append(f"  {i}. {key} key ({modifier_desc})")
                else:
                    lines.append(f"  {i}. {key.upper()} {direction_symbol}")
        else:
            lines.append("❌ No key combination available")
        
        return '\n'.join(lines)
    
    def _create_key_visual(self, keys: List[str]) -> str:
        """Create a visual representation of the key combination
        
        Args:
            keys: List of key names
            
        Returns:
            ASCII art representation
        """
        # Create a 3x3 grid representing the 8 directions + center
        grid = [
            ['↖', '↑', '↗'],
            ['←', '●', '→'], 
            ['↙', '↓', '↘']
        ]
        
        # Map keys to grid positions (matching the actual flute key system)
        key_positions = {
            'up_left': (0, 0), 'up': (0, 1), 'up_right': (0, 2),
            'left': (1, 0), 'center': (1, 1), 'right': (1, 2),
            'down_left': (2, 0), 'down': (2, 1), 'down_right': (2, 2),
            # Additional mappings for special keys
            '1': (1, 1),  # Center position for the "1" key modifier
            '3': (1, 1),  # Center position for the "3" key modifier
        }
        
        # Highlight active keys
        visual_lines = []
        visual_lines.append("    ┌───┬───┬───┐")
        
        for row_idx, row in enumerate(grid):
            row_parts = []
            for col_idx, cell in enumerate(row):
                # Check if this position should be highlighted
                is_active = False
                for key in keys:
                    if key_positions.get(key) == (row_idx, col_idx):
                        is_active = True
                        break
                
                if is_active:
                    row_parts.append(f"[reverse bold cyan]{cell}[/reverse bold cyan]")
                else:
                    row_parts.append(f"[dim]{cell}[/dim]")
            
            visual_lines.append(f"    │ {' │ '.join(row_parts)} │")
            
            if row_idx < len(grid) - 1:
                visual_lines.append("    ├───┼───┼───┤")
        
        visual_lines.append("    └───┴───┴───┘")
        
        return '\n'.join(visual_lines)
    
    def _create_rest_display(self, note: Any) -> str:
        """Create display for a rest or unplayable note
        
        Args:
            note: The rest note
            
        Returns:
            Formatted display string
        """
        lines = []
        
        lines.append("🎹 Current Note")
        lines.append("=" * 15)
        lines.append("")
        
        # Determine note type
        if hasattr(note, 'physical_height') and note.physical_height is None:
            lines.append("🔇 Rest Note")
            lines.append("")
            lines.append("This is a silence/pause in the music.")
            lines.append("No keys need to be pressed.")
            lines.append("")
            lines.append("    ┌───┬───┬───┐")
            lines.append("    │   │   │   │")
            lines.append("    ├───┼───┼───┤")
            lines.append("    │   │ ○ │   │")
            lines.append("    ├───┼───┼───┤")
            lines.append("    │   │   │   │")
            lines.append("    └───┴───┴───┘")
            lines.append("      (no input)")
        else:
            lines.append("❌ Unplayable Note")
            lines.append("")
            lines.append("This note cannot be played")
            lines.append("with the current flute range.")
            
            if hasattr(note, 'notation'):
                lines.append(f"Original notation: {note.notation}")
            
            lines.append("")
            lines.append("    ┌───┬───┬───┐")
            lines.append("    │ ✗ │ ✗ │ ✗ │")
            lines.append("    ├───┼───┼───┤")
            lines.append("    │ ✗ │ ✗ │ ✗ │")
            lines.append("    ├───┼───┼───┤")
            lines.append("    │ ✗ │ ✗ │ ✗ │")
            lines.append("    └───┴───┴───┘")
            lines.append("    (out of range)")
        
        return '\n'.join(lines)
    
    def reset_display(self) -> None:
        """Reset to the default display"""
        self.current_note = None
        self.current_keys = []
        self.update_display(self._get_default_display())
    
    def update_display(self, content: str) -> None:
        """Update the display content
        
        Args:
            content: Content to display
        """
        try:
            display = self.query_one("#fingering-display", Static)
            display.update(content)
        except:
            # Widget not mounted yet
            pass
    
    def get_fingering_help(self) -> str:
        """Get help text for fingering patterns
        
        Returns:
            Help text explaining the fingering system
        """
        return """
🎹 Flute Fingering System Help

The Animal Well flute uses an 8-directional input system:

Directions:
  ↖ ↑ ↗    Up-Left, Up, Up-Right
  ← ● →    Left, Center, Right  
  ↙ ↓ ↘    Down-Left, Down, Down-Right

Notes are mapped to combinations of these directions.
Some notes may require multiple direction presses.

🎵 Tips:
- Highlighted directions show active keys
- Rest notes (○) require no input
- Unplayable notes (✗) are out of range
- Practice the patterns slowly at first
        """