"""Main Screen - The Bridge - for Cosmic Flute TUI"""

from typing import List, Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Input, Markdown, Button
from textual.reactive import reactive
from textual.binding import Binding
from textual import events
from textual.events import Key

from ..components.header import AppHeader
from ..components.footer import AppFooter
from ...services import SongServiceBase
from ...utils.logger import get_logger

logger = get_logger(__name__)


class MainScreen(Screen):
    """Main Screen - The Bridge
    
    Central hub for song selection and accessing other features.
    Features a song library table and song details panel.
    """
    
    BINDINGS = [
        Binding("enter", "select_song", "Play Song"),
        Binding("i", "import_song", "Import"),
        Binding("?", "help", "Help"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("/", "focus_search", "Search", show=False),
        Binding("escape", "clear_search", "Clear Search", show=False),
    ]
    
    # Reactive attributes
    search_query: reactive[str] = reactive("", init=False)
    selected_song: reactive[str] = reactive("", init=False)
    
    def __init__(self, song_service: SongServiceBase, **kwargs):
        """Initialize the main screen
        
        Args:
            song_service: Service for song operations
        """
        super().__init__(**kwargs)
        self.song_service = song_service
        self.songs_data: List[Dict[str, str]] = []
        self.filtered_songs: List[Dict[str, str]] = []
        
    def compose(self) -> ComposeResult:
        """Compose the main screen layout"""
        yield AppHeader()
        
        with Grid(classes="three-row-grid"):
            # Search bar
            with Horizontal(id="search-bar"):
                yield Input(
                    placeholder="🔍 Search songs by name or artist...",
                    id="search-input"
                )
                yield Button("Import", id="import-button", variant="primary")
            
            # Main content area with two columns
            with Grid(classes="two-column-grid", id="main-content"):
                # Left pane: Song library table
                with Vertical(classes="song-library"):
                    yield DataTable(
                        id="song-table",
                        zebra_stripes=True,
                        cursor_type="row",
                        show_header=True
                    )
                
                # Right pane: Song details
                with Vertical(classes="song-details"):
                    yield Markdown(
                        "# 🌌 Starmap\n\nSelect a song from the library to view its details.",
                        id="song-details-content"
                    )
        
        yield AppFooter([
            ("Enter", "Play Song"),
            ("I", "Import"),
            ("?", "Help"),
            ("Ctrl+Q", "Quit")
        ])
    
    async def on_mount(self) -> None:
        """Initialize the screen when mounted"""
        logger.info("MainScreen mounted, loading songs")
        
        # Load songs data
        await self.load_songs()
        
        # Set up the data table
        self.setup_song_table()
        
        # Focus the search input initially
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    async def load_songs(self) -> None:
        """Load songs from the service"""
        try:
            self.songs_data = self.song_service.song_manager.list_songs_with_info()
            self.filtered_songs = self.songs_data.copy()
            logger.info(f"Loaded {len(self.songs_data)} songs")
        except Exception as e:
            logger.error(f"Failed to load songs: {e}")
            self.app.show_notification(f"Failed to load songs: {e}", "error")
            self.songs_data = []
            self.filtered_songs = []
    
    def setup_song_table(self) -> None:
        """Set up the song data table"""
        table = self.query_one("#song-table", DataTable)
        
        # Add columns
        table.add_columns("Title", "BPM", "Bars", "Description")
        
        # Add rows from filtered songs
        self.populate_table()
    
    def populate_table(self) -> None:
        """Populate the table with current filtered songs"""
        table = self.query_one("#song-table", DataTable)
        
        # Clear existing rows
        table.clear()
        
        # Add filtered songs
        for song in self.filtered_songs:
            # Truncate description for table display
            desc = song.get("description", "")
            if len(desc) > 40:
                desc = desc[:37] + "..."
            
            table.add_row(
                song["name"],
                song["bpm"],
                song["bars"],
                desc,
                key=song["name"]  # Use song name as row key
            )
        
        logger.debug(f"Populated table with {len(self.filtered_songs)} songs")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search-input":
            self.search_query = event.value.lower()
            self.filter_songs()
    
    def filter_songs(self) -> None:
        """Filter songs based on search query"""
        if not self.search_query:
            self.filtered_songs = self.songs_data.copy()
        else:
            self.filtered_songs = [
                song for song in self.songs_data
                if (self.search_query in song["name"].lower() or
                    self.search_query in song.get("description", "").lower())
            ]
        
        # Update the table
        self.populate_table()
        logger.debug(f"Filtered to {len(self.filtered_songs)} songs with query: '{self.search_query}'")
    

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle song selection in the table (both click and Enter key)"""
        if event.data_table.id == "song-table":
            # Get the selected song name from the row key
            # Handle different possible types of row_key
            song_name = None
            
            try:
                # Get song name from row key
                # In Textual 5.0.1, event.row_key is a RowKey object
                # We need to get the actual value, not the object string representation
                
                # Try multiple approaches to get the actual song name
                if isinstance(event.row_key, str):
                    # Direct string (unlikely in modern Textual)
                    song_name = event.row_key
                elif hasattr(event.row_key, 'value'):
                    # RowKey with value attribute
                    song_name = str(event.row_key.value)
                else:
                    # Last resort: check if str() gives us the actual value
                    str_key = str(event.row_key)
                    # If it looks like an object representation, try to find the key differently
                    if str_key.startswith('<') and 'object at' in str_key:
                        # This is an object reference, try to get the actual key from the table
                        table = event.data_table
                        # Get the row data and use the first column as song name
                        try:
                            coordinate = table.get_cell_coordinate(event.cursor_row, 0)
                            song_name = str(table.get_cell_at(coordinate))
                        except:
                            song_name = None
                    else:
                        song_name = str_key
                
                if song_name and isinstance(song_name, str):
                    self.selected_song = song_name
                    self.update_song_details(song_name)
                    logger.debug(f"Selected song: {song_name}")
                    
                    # Don't automatically navigate - let user use Enter key or action_select_song
                else:
                    raise ValueError(f"Could not extract valid song name from row_key: {event.row_key}")
                    
            except Exception as e:
                logger.error(f"Error handling song selection: {e}")
                logger.error(f"Row key type: {type(event.row_key)}, value: {repr(event.row_key)}")
                self.app.show_notification("Failed to select song", "error")
    
    def on_key(self, event: Key) -> None:
        """Handle key events for the screen"""
        # Check if Enter was pressed when DataTable has focus and a song is selected
        if event.key == "enter" and self.selected_song:
            # Check if the DataTable has focus
            table = self.query_one("#song-table", DataTable)
            if table.has_focus:
                logger.info(f"Enter key pressed, navigating to player for: {self.selected_song}")
                self.app.navigate_to_player(self.selected_song)
                event.prevent_default()  # Prevent default Enter handling
    
    def update_song_details(self, song_name: str) -> None:
        """Update the song details panel
        
        Args:
            song_name: Name of the selected song
        """
        try:
            # Get song details from service
            success, song, error_msg = self.song_service.get_song_safely(song_name)
            
            if not success:
                markdown_content = f"# ❌ Error\n\n{error_msg}"
            else:
                # Create markdown content for song details
                markdown_content = f"""# 🎵 {song.name}

## Musical Details
- **BPM**: {song.bpm}
- **Bars**: {len(song.jianpu) if song.jianpu else 0}
- **Offset**: {song.offset:+.1f} semitones

## Description
{song.description or "*No description available*"}

## Jianpu Preview
```
{self._get_jianpu_preview(song.jianpu)}
```

---
*Press **Enter** to play this song*
"""
            
            # Update the markdown widget
            details_widget = self.query_one("#song-details-content", Markdown)
            details_widget.update(markdown_content)
            
            logger.debug(f"Updated details for song: {song_name}")
            
        except Exception as e:
            logger.error(f"Failed to update song details: {e}")
            error_content = f"# ❌ Error\n\nFailed to load song details: {e}"
            details_widget = self.query_one("#song-details-content", Markdown)
            details_widget.update(error_content)
    
    def _get_jianpu_preview(self, jianpu: List[Any]) -> str:
        """Get a preview of the jianpu notation
        
        Args:
            jianpu: The jianpu data
            
        Returns:
            String preview of the notation
        """
        if not jianpu:
            return "No notation available"
        
        # Show first few bars as preview
        preview_bars = jianpu[:3]  # First 3 bars
        preview_lines = []
        
        for i, bar in enumerate(preview_bars, 1):
            if isinstance(bar, list):
                # Convert bar to string representation
                bar_str = " ".join(str(note) for note in bar)
            else:
                bar_str = str(bar)
            
            preview_lines.append(f"Bar {i}: {bar_str}")
        
        if len(jianpu) > 3:
            preview_lines.append(f"... and {len(jianpu) - 3} more bars")
        
        return "\n".join(preview_lines)
    
    def action_select_song(self) -> None:
        """Action to select and play the current song"""
        logger.info(f"action_select_song called, selected_song='{self.selected_song}'")
        
        if self.selected_song:
            logger.info(f"User selected song for playing: {self.selected_song}")
            try:
                self.app.navigate_to_player(self.selected_song)
                logger.info(f"Successfully called navigate_to_player for: {self.selected_song}")
            except Exception as e:
                logger.error(f"Failed to navigate to player: {e}")
                self.app.show_notification(f"Failed to open player: {e}", "error")
        else:
            logger.warning("No song selected when Enter pressed")
            self.app.show_notification("Please select a song first", "warning")
    
    def action_import_song(self) -> None:
        """Action to open the import screen"""
        logger.info("User requested song import")
        self.app.navigate_to_import()
    
    def action_help(self) -> None:
        """Action to show help"""
        logger.info("User requested help from main screen")
        self.app.push_screen("help")
    
    def action_quit(self) -> None:
        """Action to quit the application"""
        self.app.action_quit()
    
    def action_focus_search(self) -> None:
        """Focus the search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    def action_clear_search(self) -> None:
        """Clear the search query"""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.search_query = ""
        self.filter_songs()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "import-button":
            self.action_import_song()
    
    def refresh_data(self) -> None:
        """Refresh the screen data"""
        logger.info("Refreshing main screen")
        self.run_worker(self.load_songs())
        self.app.show_notification("Song library refreshed", "success")