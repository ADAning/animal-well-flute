"""Enhanced Song Table Widget for the TUI"""

from typing import List, Dict, Any, Optional
from textual.widgets import DataTable
from textual.reactive import reactive

from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongTable(DataTable):
    """Enhanced DataTable specifically for displaying songs"""
    
    DEFAULT_CSS = """
    SongTable {
        background: #1a1f38;
        color: #c0c0c0;
        border: solid #00ffff;
        border-title-style: bold;
        border-title-color: #00ffff;
        border-title-align: center;
    }
    
    SongTable > .datatable--header {
        background: #00ffff;
        color: #0a0f28;
        text-style: bold;
    }
    
    SongTable > .datatable--cursor {
        background: #00ffff;
        color: #0a0f28;
        text-style: bold;
    }
    
    SongTable > .datatable--hover {
        background: #ff00ff 20%;
        color: #c0c0c0;
    }
    
    .song-row-playable {
        color: #44ff44;
    }
    
    .song-row-complex {
        color: #ffaa00;
    }
    
    .song-row-error {
        color: #ff4444;
    }
    """
    
    # Reactive attributes
    search_query: reactive[str] = reactive("", init=False)
    
    def __init__(self, **kwargs):
        """Initialize the song table"""
        super().__init__(
            zebra_stripes=True,
            cursor_type="row",
            show_header=True,
            **kwargs
        )
        self.songs_data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []
        # Set border title
        self.border_title = "🎵 Song Library"
    
    def setup_columns(self) -> None:
        """Set up the table columns"""
        self.add_columns("Title", "Artist", "BPM", "Bars", "Difficulty")
    
    def load_songs(self, songs: List[Dict[str, Any]]) -> None:
        """Load songs into the table
        
        Args:
            songs: List of song dictionaries
        """
        self.songs_data = songs
        self.filtered_data = songs.copy()
        self.populate_table()
        logger.info(f"Loaded {len(songs)} songs into table")
    
    def populate_table(self) -> None:
        """Populate the table with current filtered data"""
        # Clear existing rows
        self.clear()
        
        # Add filtered songs
        for song in self.filtered_data:
            # Determine difficulty/complexity
            difficulty = self._calculate_difficulty(song)
            
            # Format display values
            title = song.get("name", "Unknown")
            artist = song.get("artist", "")
            bpm = song.get("bpm", "")
            bars = song.get("bars", "")
            
            # Truncate long titles
            if len(title) > 25:
                title = title[:22] + "..."
            
            # Truncate long artist names
            if len(artist) > 15:
                artist = artist[:12] + "..."
            
            self.add_row(
                title,
                artist,
                str(bpm),
                str(bars),
                difficulty,
                key=song.get("name", "")
            )
        
        logger.debug(f"Populated table with {len(self.filtered_data)} songs")
    
    def _calculate_difficulty(self, song: Dict[str, Any]) -> str:
        """Calculate a simple difficulty indicator for a song
        
        Args:
            song: Song data dictionary
            
        Returns:
            Difficulty string with emoji
        """
        try:
            bpm = int(song.get("bpm", 120))
            bars = int(song.get("bars", 0))
            
            # Simple difficulty calculation
            if bpm > 150 or bars > 20:
                return "🔴 Hard"
            elif bpm > 100 or bars > 10:
                return "🟡 Medium"
            else:
                return "🟢 Easy"
                
        except (ValueError, TypeError):
            return "❓ Unknown"
    
    def filter_songs(self, query: str) -> None:
        """Filter songs based on search query
        
        Args:
            query: Search query string
        """
        self.search_query = query.lower()
        
        if not self.search_query:
            self.filtered_data = self.songs_data.copy()
        else:
            self.filtered_data = [
                song for song in self.songs_data
                if (self.search_query in song.get("name", "").lower() or
                    self.search_query in song.get("artist", "").lower() or
                    self.search_query in song.get("description", "").lower())
            ]
        
        self.populate_table()
        logger.debug(f"Filtered to {len(self.filtered_data)} songs")
    
    def get_selected_song(self) -> Optional[str]:
        """Get the currently selected song name
        
        Returns:
            Selected song name or None
        """
        if self.cursor_row is not None and self.cursor_row >= 0:
            try:
                # Get the row key which should be the song name
                row_key = self.get_row_at(self.cursor_row)
                if row_key:
                    return str(row_key[0])  # Return the row key (song name)
            except (IndexError, AttributeError):
                pass
        
        return None
    
    def refresh_data(self) -> None:
        """Refresh the table data"""
        self.populate_table()
    
    def sort_by_column(self, column: str, reverse: bool = False) -> None:
        """Sort songs by a specific column
        
        Args:
            column: Column name to sort by
            reverse: Whether to reverse the sort order
        """
        sort_map = {
            "Title": "name",
            "Artist": "artist", 
            "BPM": "bpm",
            "Bars": "bars"
        }
        
        sort_key = sort_map.get(column)
        if not sort_key:
            return
        
        try:
            if sort_key in ["bpm", "bars"]:
                # Numeric sort
                self.filtered_data.sort(
                    key=lambda x: int(x.get(sort_key, 0)),
                    reverse=reverse
                )
            else:
                # String sort
                self.filtered_data.sort(
                    key=lambda x: x.get(sort_key, "").lower(),
                    reverse=reverse
                )
            
            self.populate_table()
            logger.debug(f"Sorted by {column} (reverse={reverse})")
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error sorting by {column}: {e}")
    
    def get_song_count(self) -> tuple[int, int]:
        """Get the count of filtered and total songs
        
        Returns:
            Tuple of (filtered_count, total_count)
        """
        return len(self.filtered_data), len(self.songs_data)