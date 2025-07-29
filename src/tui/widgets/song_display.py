"""Song Display Widget for rendering musical notation"""

from typing import List, Any, Optional
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from rich.text import Text
from rich.console import Console

from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongDisplayWidget(Widget):
    """Widget for displaying song notation with current note highlighting"""
    
    DEFAULT_CSS = """
    SongDisplayWidget {
        border: solid #00ffff;
        border-title-style: bold;
        border-title-color: #00ffff;
        border-title-align: center;
        height: 1fr;
        width: 1fr;
        padding: 1;
    }
    
    .notation-bar {
        height: 3;
        margin: 0 0 1 0;
        padding: 1;
        background: #1a1f38;
        border: solid #808080;
    }
    
    .current-bar {
        border: solid #00ffff;
        background: #00ffff 10%;
    }
    
    .notation-text {
        color: #c0c0c0;
    }
    
    .current-note {
        background: #00ffff;
        color: #0a0f28;
        text-style: bold;
    }
    
    .rest-note {
        color: #808080;
        text-style: dim;
    }
    
    .unplayable-note {
        color: #ff4444;
        text-style: strike;
    }
    """
    
    # Reactive attributes
    current_note_index: reactive[int] = reactive(0, init=False)
    
    def __init__(self, **kwargs):
        """Initialize the song display widget"""
        super().__init__(**kwargs)
        self.parsed_notes = []
        self.converted_notes = []
        self.notation_bars = []
        # Set border title
        self.border_title = "♪ Musical Notation ♪"
    
    def compose(self):
        """Compose the widget layout"""
        with Vertical(id="notation-container"):
            yield Static("No song loaded", id="notation-display", classes="notation-text")
    
    def load_song(self, parsed_notes: List[Any], converted_notes: List[Any]) -> None:
        """Load a song for display
        
        Args:
            parsed_notes: Parsed musical notes
            converted_notes: Converted notes for playing
        """
        self.parsed_notes = parsed_notes
        self.converted_notes = converted_notes
        self.render_notation()
        logger.info(f"Loaded song with {len(parsed_notes)} bars")
    
    def render_notation(self) -> None:
        """Render the musical notation"""
        if not self.parsed_notes:
            self.update_display("No song loaded")
            return
        
        # Create notation display
        notation_lines = []
        notation_lines.append("📜 Musical Notation - Jianpu Style")
        notation_lines.append("=" * 50)
        
        for bar_index, bar in enumerate(self.parsed_notes):
            bar_line = self._render_bar(bar_index, bar)
            notation_lines.append(bar_line)
        
        notation_lines.append("=" * 50)
        notation_lines.append("🎹 Legend: 1-7=notes, 0=rest, h=high, l=low")
        
        self.update_display("\n".join(notation_lines))
    
    def _render_bar(self, bar_index: int, bar: List[Any]) -> str:
        """Render a single bar of notation
        
        Args:
            bar_index: Index of the bar
            bar: List of notes in the bar
            
        Returns:
            Formatted string representation of the bar
        """
        bar_parts = []
        
        # Bar number
        bar_parts.append(f"Bar {bar_index + 1:2d}:")
        
        # Render notes
        note_strs = []
        for note in bar:
            note_str = self._format_note(note)
            note_strs.append(note_str)
        
        # Join notes with spacing
        bar_content = " ".join(note_strs)
        bar_parts.append(bar_content)
        
        return " ".join(bar_parts)
    
    def _format_note(self, note: Any) -> str:
        """Format a single note for display
        
        Args:
            note: Note to format
            
        Returns:
            Formatted string representation
        """
        if hasattr(note, 'relative_pitch'):
            # This is a parsed note with pitch information
            if note.relative_pitch == 0:
                return "0"  # Rest
            else:
                # Convert pitch to jianpu notation
                return self._pitch_to_jianpu(note.relative_pitch)
        elif isinstance(note, (int, float)):
            if note == 0:
                return "0"
            else:
                return str(int(note))
        elif isinstance(note, str):
            return note
        elif isinstance(note, tuple):
            # Group of notes
            sub_notes = [self._format_note(sub_note) for sub_note in note]
            return f"({' '.join(sub_notes)})"
        else:
            return str(note)
    
    def _pitch_to_jianpu(self, pitch: float) -> str:
        """Convert relative pitch to jianpu notation
        
        Args:
            pitch: Relative pitch in semitones
            
        Returns:
            Jianpu notation string
        """
        # Simple mapping - this could be more sophisticated
        pitch_map = {
            -12: "l7", -10: "l1", -8: "l2", -7: "l3", -5: "l4", -3: "l5", -1: "l6",
            0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7",
            12: "h1", 14: "h2", 16: "h3", 17: "h4", 19: "h5", 21: "h6", 23: "h7"
        }
        
        # Find closest match
        closest_pitch = min(pitch_map.keys(), key=lambda x: abs(x - pitch))
        result = pitch_map[closest_pitch]
        
        # Add sharp/flat indicators if needed
        diff = pitch - closest_pitch
        if diff > 0.3:
            result += "#"
        elif diff < -0.3:
            result += "b"
        
        return result
    
    def update_display(self, content: str) -> None:
        """Update the display content
        
        Args:
            content: Content to display
        """
        try:
            display = self.query_one("#notation-display", Static)
            display.update(content)
        except:
            # Widget not mounted yet
            pass
    
    def set_current_note(self, note_index: int) -> None:
        """Set the current note position for highlighting
        
        Args:
            note_index: Index of the current note
        """
        self.current_note_index = note_index
        # Re-render with highlighting
        self._render_with_highlight()
    
    def _render_with_highlight(self) -> None:
        """Render notation with current note highlighted"""
        if not self.parsed_notes:
            return
        
        # Create highlighted notation
        notation_lines = []
        notation_lines.append("📜 Musical Notation - Jianpu Style")
        notation_lines.append("=" * 50)
        
        current_global_index = 0
        
        for bar_index, bar in enumerate(self.parsed_notes):
            bar_line = self._render_bar_with_highlight(
                bar_index, bar, current_global_index
            )
            notation_lines.append(bar_line)
            current_global_index += len(bar)
        
        notation_lines.append("=" * 50)
        notation_lines.append("🎹 Legend: 1-7=notes, 0=rest, h=high, l=low")
        notation_lines.append(f"🎯 Current: Note {self.current_note_index + 1}")
        
        self.update_display("\n".join(notation_lines))
    
    def _render_bar_with_highlight(
        self, bar_index: int, bar: List[Any], start_index: int
    ) -> str:
        """Render a bar with current note highlighting
        
        Args:
            bar_index: Index of the bar
            bar: List of notes in the bar
            start_index: Global index where this bar starts
            
        Returns:
            Formatted string with highlighting
        """
        bar_parts = []
        
        # Check if current note is in this bar
        current_in_bar = (
            start_index <= self.current_note_index < start_index + len(bar)
        )
        
        # Bar number with highlighting
        if current_in_bar:
            bar_parts.append(f"►Bar {bar_index + 1:2d}:")
        else:
            bar_parts.append(f" Bar {bar_index + 1:2d}:")
        
        # Render notes with highlighting
        note_strs = []
        for note_index, note in enumerate(bar):
            global_note_index = start_index + note_index
            note_str = self._format_note(note)
            
            # Highlight current note
            if global_note_index == self.current_note_index:
                note_str = f"[reverse bold cyan]{note_str}[/reverse bold cyan]"
            
            note_strs.append(note_str)
        
        # Join notes with spacing
        bar_content = " ".join(note_strs)
        bar_parts.append(bar_content)
        
        return " ".join(bar_parts)
    
    def scroll_to_current_note(self) -> None:
        """Scroll the display to show the current note"""
        # This would be implemented to auto-scroll the container
        # to keep the current note visible
        pass