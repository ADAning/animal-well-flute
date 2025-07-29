"""Song Player Screen - The Observatory - for Cosmic Flute TUI"""

import time
import logging
from typing import List, Any, Optional
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Static, ProgressBar, Button, Select, Input
from textual.reactive import reactive
from textual.binding import Binding
from textual import work
import asyncio

from ..components.header import AppHeader
from ..components.footer import AppFooter
from ..widgets.song_display import SongDisplayWidget
from ..widgets.flute_fingering import FluteFingeringWidget
from ...services import SongServiceBase
from ...core.parser import RelativeParser
from ...core.converter import AutoConverter
from ...core.flute import AutoFlute
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SongPlayerScreen(Screen):
    """Song Player Screen - The Observatory
    
    Interactive playing screen focused entirely on the music sheet.
    Features auto-scrolling notation and flute fingering display.
    """
    
    BINDINGS = [
        Binding("space", "play_pause", "Play/Pause"),
        Binding("left", "previous_note", "Previous"),
        Binding("right", "next_note", "Next"),
        Binding("home", "first_note", "First Note", show=False),
        Binding("end", "last_note", "Last Note", show=False),
        Binding("escape", "back", "Back to Library"),
        Binding("r", "restart", "Restart", show=False),
        Binding("ctrl+r", "refresh_settings", "Settings", show=False),
    ]
    
    # Reactive attributes
    current_note_index: reactive[int] = reactive(0, init=False)
    is_playing: reactive[bool] = reactive(False, init=False)
    song_name: reactive[str] = reactive("", init=False)
    
    def __init__(self, song_service: SongServiceBase, song_name: str = "", **kwargs):
        """Initialize the song player screen
        
        Args:
            song_service: Service for song operations
            song_name: Name of the song to play
        """
        super().__init__(**kwargs)
        self.song_service = song_service
        self.song_name = song_name
        self.song = None
        self.parsed_notes = []
        self.converted_notes = []
        self.flute = AutoFlute()
        self.play_task = None
        
        # Playback settings
        self.bpm = None
        self.strategy = "optimal"
        self.ready_time = 3
        self.total_notes_cache = 0  # Cache total notes to avoid recalculation
    
    def compose(self) -> ComposeResult:
        """Compose the song player layout"""
        yield AppHeader(show_subtitle=False)
        
        with Grid(classes="three-row-grid"):
            # Song info header
            with Horizontal(id="song-info-bar"):
                yield Static("", id="song-title", classes="cosmic-accent")
                yield Static("", id="song-bpm", classes="nebula-accent")
                yield Static("", id="song-progress", classes="aurora-accent")
            
            # Main player area
            with Grid(classes="two-column-grid", id="player-grid"):
                # Left: Song notation display
                with ScrollableContainer(classes="song-player", id="notation-container"):
                    yield SongDisplayWidget(id="song-display")
                
                # Right: Flute fingering and controls
                with Vertical(id="control-panel"):
                    yield FluteFingeringWidget(id="flute-fingering")
                    
                    with Vertical(id="playback-controls"):
                        yield Button("▶ Play", id="play-button", variant="primary")
                        yield Button("⏹ Stop", id="stop-button")
                        yield Button("⏮ Restart", id="restart-button")
                        
                        # Settings panel
                        with Vertical(id="settings-panel"):
                            yield Static("🎯 Strategy:", classes="bright-text")
                            yield Select(
                                options=[
                                    ("optimal", "🎯 Optimal"),
                                    ("high", "⬆️ High Priority"),
                                    ("low", "⬇️ Low Priority"),
                                    ("auto", "🤖 Auto Select")
                                ],
                                id="strategy-select"
                            )
                            
                            yield Static("🎵 Custom BPM:", classes="bright-text")
                            yield Input(
                                placeholder="Leave empty for default",
                                id="bpm-input",
                                type="integer"
                            )
            
            # Progress bar
            yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        
        yield AppFooter([
            ("Space", "Play/Pause"),
            ("←/→", "Navigate"),
            ("Esc", "Back"),
            ("R", "Restart")
        ])
    
    async def on_mount(self) -> None:
        """Initialize the screen when mounted"""
        logger.info(f"SongPlayerScreen mounted for song: {self.song_name}")
        
        # Set default values for Select components after mounting
        try:
            strategy_select = self.query_one("#strategy-select", Select)
            strategy_select.value = "optimal"
        except Exception as e:
            logger.warning(f"Failed to set strategy select default value: {e}")
        
        await self.load_song()
        self.update_display()
    
    async def load_song(self) -> None:
        """Load and prepare the song for playing"""
        try:
            # Get song from service
            success, song, error_msg = self.song_service.get_song_safely(self.song_name)
            
            if not success:
                self.app.show_notification(f"Failed to load song: {error_msg}", "error")
                logger.error(f"Failed to load song {self.song_name}: {error_msg}")
                return
            
            self.song = song
            self.bpm = song.bpm
            
            # Parse the song
            parser = RelativeParser()
            self.parsed_notes = parser.parse(song.jianpu)
            
            # Convert for playing
            converter = AutoConverter()
            self.converted_notes = converter.convert_jianpu(
                self.parsed_notes, 
                strategy=self.strategy
            )
            
            # Cache total notes count for performance
            self.total_notes_cache = sum(len(bar) for bar in self.parsed_notes)
            
            # Update UI
            self.update_song_info()
            self.update_progress_bar()
            
            # Load song into display widgets
            song_display = self.query_one("#song-display", SongDisplayWidget)
            song_display.load_song(self.parsed_notes, self.converted_notes)
            
            logger.info(f"Successfully loaded song: {self.song_name}")
            
        except Exception as e:
            logger.error(f"Error loading song: {e}")
            self.app.show_notification(f"Error loading song: {e}", "error")
    
    def update_song_info(self) -> None:
        """Update the song information display"""
        if not self.song:
            return
        
        # Update title
        title_widget = self.query_one("#song-title", Static)
        title_widget.update(f"🎵 {self.song.name}")
        
        # Update BPM
        bpm_widget = self.query_one("#song-bpm", Static)
        bpm_widget.update(f"♪ {self.bpm} BPM")
        
        # Update progress info
        progress_widget = self.query_one("#song-progress", Static)
        progress_widget.update(f"📊 Note {self.current_note_index + 1} / {self.total_notes_cache}")
    
    def update_progress_bar(self) -> None:
        """Update the progress bar"""
        if self.total_notes_cache <= 0:
            return
        
        progress = (self.current_note_index / self.total_notes_cache) * 100
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)
    
    def update_display(self) -> None:
        """Update all display elements"""
        self.update_song_info()
        self.update_progress_bar()
        
        # Update song display widget
        try:
            song_display = self.query_one("#song-display", SongDisplayWidget)
            song_display.set_current_note(self.current_note_index)
            
            # Update flute fingering
            flute_widget = self.query_one("#flute-fingering", FluteFingeringWidget)
            current_note = self.get_current_note()
            if current_note:
                flute_widget.show_fingering(current_note)
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def update_display_minimal(self) -> None:
        """Minimal display update during playback to avoid lag"""
        start_time = time.time()
        try:
            # Only update the most essential elements
            song_display = self.query_one("#song-display", SongDisplayWidget)
            song_display.set_current_note(self.current_note_index)
        except Exception as e:
            logger.debug(f"Error in minimal display update: {e}")
        finally:
            # Monitor UI update performance
            update_duration = time.time() - start_time
            if update_duration > 0.005:  # 5ms threshold for UI updates
                logger.debug(f"Slow UI update detected: minimal update took {update_duration*1000:.1f}ms")
    
    def get_current_note(self) -> Any:
        """Get the current note being played"""
        if not self.converted_notes:
            return None
        
        note_index = 0
        for bar in self.converted_notes:
            for note in bar:
                if note_index == self.current_note_index:
                    return note
                note_index += 1
        
        return None
    
    def action_play_pause(self) -> None:
        """Toggle play/pause state"""
        if self.is_playing:
            self.action_pause()
        else:
            self.action_play()
    
    def action_play(self) -> None:
        """Start playing the song"""
        if not self.converted_notes:
            self.app.show_notification("No song loaded", "warning")
            return
        
        logger.info(f"Starting playback of {self.song_name}")
        self.is_playing = True
        # Reset flute stop flag for new playback
        self.flute.stop_requested = False
        self.update_play_button()
        
        # Start playback in a worker
        self.play_task = self._play_song()
    
    def action_pause(self) -> None:
        """Pause the song"""
        logger.info("Pausing playback")
        self.is_playing = False
        # Signal flute to stop immediately
        self.flute.stop_requested = True
        self.update_play_button()
        
        if self.play_task:
            self.play_task.cancel()
            self.play_task = None
    
    def action_stop(self) -> None:
        """Stop the song and reset to beginning"""
        logger.info("Stopping playback")
        self.action_pause()
        self.current_note_index = 0
        self.update_display()
    
    def action_restart(self) -> None:
        """Restart the song from the beginning"""
        logger.info("Restarting song")
        was_playing = self.is_playing
        self.action_stop()
        if was_playing:
            self.action_play()
    
    def action_next_note(self) -> None:
        """Move to the next note"""
        if self.current_note_index < self.total_notes_cache - 1:
            self.current_note_index += 1
            self.update_display()
    
    def action_previous_note(self) -> None:
        """Move to the previous note"""
        if self.current_note_index > 0:
            self.current_note_index -= 1
            self.update_display()
    
    def action_first_note(self) -> None:
        """Jump to the first note"""
        self.current_note_index = 0
        self.update_display()
    
    def action_last_note(self) -> None:
        """Jump to the last note"""
        if self.total_notes_cache > 0:
            self.current_note_index = self.total_notes_cache - 1
            self.update_display()
    
    def action_back(self) -> None:
        """Go back to the main screen"""
        if self.is_playing:
            self.action_pause()
        logger.info("Returning to main screen")
        self.app.pop_screen()
    
    def update_play_button(self) -> None:
        """Update the play button text"""
        try:
            play_button = self.query_one("#play-button", Button)
            if self.is_playing:
                play_button.label = "⏸ Pause"
            else:
                play_button.label = "▶ Play"
        except:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "play-button":
            self.action_play_pause()
        elif event.button.id == "stop-button":
            self.action_stop()
        elif event.button.id == "restart-button":
            self.action_restart()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle strategy selection changes"""
        if event.select.id == "strategy-select":
            self.strategy = event.value
            logger.info(f"Strategy changed to: {self.strategy}")
            # Reload the song with new strategy
            self.reload_with_strategy()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle BPM input changes"""
        if event.input.id == "bpm-input":
            try:
                if event.value.strip():
                    new_bpm = int(event.value)
                    if 30 <= new_bpm <= 300:
                        self.bpm = new_bpm
                        self.update_song_info()
                        logger.info(f"BPM changed to: {new_bpm}")
                else:
                    # Reset to default
                    self.bpm = self.song.bpm if self.song else 120
                    self.update_song_info()
            except ValueError:
                pass  # Invalid input, ignore
    
    @work(exclusive=True)
    async def _play_song(self) -> None:
        """Play the song asynchronously"""
        try:
            beat_interval = 60.0 / self.bpm
            
            # Ready countdown
            for i in range(self.ready_time, 0, -1):
                if not self.is_playing:
                    return
                self.app.show_notification(f"Starting in {i}...", "info")
                await asyncio.sleep(1)
            
            if not self.is_playing:
                return
            
            self.app.show_notification("🎵 Playing!", "success")
            
            note_index = 0
            for bar_index, bar in enumerate(self.converted_notes):
                for note_index_in_bar, note in enumerate(bar):
                    if not self.is_playing:
                        return
                    
                    # Update current position
                    self.current_note_index = note_index
                    
                    # Minimal UI updates during playback to avoid any lag
                    if note_index_in_bar == 0:
                        # Only update at the start of each bar for basic progress tracking
                        try:
                            self.update_display_minimal()
                        except Exception:
                            pass  # Ignore UI errors during playback
                    # Skip all other UI updates to maintain precise timing
                    
                    # Play the note using the actual flute system
                    if hasattr(note, 'key_combination') and note.key_combination:
                        # Use the flute to actually play the note
                        try:
                            await self._play_single_note(note, beat_interval)
                        except Exception as e:
                            logger.warning(f"Failed to play note: {e}")
                            # Fallback sleep to maintain timing if _play_single_note failed completely
                            fallback_duration = beat_interval
                            if hasattr(note, 'time_factor') and note.time_factor > 0:
                                fallback_duration = note.time_factor * beat_interval
                            await asyncio.sleep(fallback_duration)
                    else:
                        # Rest or unplayable note - calculate correct duration with time_factor
                        rest_duration = beat_interval
                        if hasattr(note, 'time_factor') and note.time_factor > 0:
                            rest_duration = note.time_factor * beat_interval
                        await asyncio.sleep(rest_duration)
                    
                    note_index += 1
            
            # Song finished
            self.is_playing = False
            self.update_play_button()
            self.app.show_notification("🎉 Song completed!", "success")
            
        except asyncio.CancelledError:
            logger.info("Playback cancelled")
        except Exception as e:
            logger.error(f"Error during playback: {e}")
            self.app.show_notification(f"Playback error: {e}", "error")
            self.is_playing = False
            self.update_play_button()
    
    @work
    async def reload_with_strategy(self) -> None:
        """Reload the song with the new strategy"""
        if not self.song:
            return
        
        try:
            converter = AutoConverter()
            self.converted_notes = converter.convert_jianpu(
                self.parsed_notes,
                strategy=self.strategy
            )
            
            # Update display
            song_display = self.query_one("#song-display", SongDisplayWidget)
            song_display.load_song(self.parsed_notes, self.converted_notes)
            
            self.app.show_notification(f"Strategy updated to {self.strategy}", "success")
            
        except Exception as e:
            logger.error(f"Error reloading with strategy: {e}")
            self.app.show_notification(f"Strategy update failed: {e}", "error")
    
    async def _play_single_note(self, note: Any, duration: float) -> None:
        """Play a single note using the flute system
        
        Args:
            note: The note to play
            duration: Duration to hold the note
        """
        # Performance monitoring
        start_time = time.time()
        expected_duration = duration
        if hasattr(note, 'time_factor') and note.time_factor > 0:
            expected_duration = note.time_factor * duration
            
        try:
            # Minimal logging to avoid UI lag during fast playback
            if hasattr(note, 'notation') and logger.isEnabledFor(logging.DEBUG):
                if note.physical_height is None:
                    logger.debug(f"Playing rest note for {duration:.2f}s")
                else:
                    logger.debug(f"Playing note {note.notation}: keys={note.key_combination}, duration={duration:.2f}s")
            
            # Use the flute's play_physical_note method with pre-defined wrapper
            def play_note_sync():
                """Synchronous wrapper for AutoFlute.play_physical_note"""
                return self.flute.play_physical_note(note, duration)
            
            # Run the synchronous flute method with minimal async overhead
            try:
                # Check if we should stop before starting the note
                if not self.is_playing:
                    return
                
                # Use run_in_executor for better performance than ThreadPoolExecutor
                result = await asyncio.get_event_loop().run_in_executor(None, play_note_sync)
                if not result:
                    logger.debug("Playback stopped by user")
            except Exception as e:
                logger.warning(f"Note playback error: {e}")
                # Fallback sleep with correct timing
                fallback_duration = duration
                if hasattr(note, 'time_factor') and note.time_factor > 0:
                    fallback_duration = note.time_factor * duration
                await asyncio.sleep(fallback_duration)
                
        except Exception as e:
            logger.error(f"Error playing single note: {e}")
            # Fallback to just waiting
            await asyncio.sleep(duration)
        finally:
            # Record performance data for monitoring
            actual_duration = time.time() - start_time
            # Only log significant deviations to avoid spam
            deviation = actual_duration - expected_duration
            if abs(deviation) > 0.01:  # 10ms threshold
                logger.debug(f"Note timing deviation: expected={expected_duration:.3f}s, actual={actual_duration:.3f}s, diff={deviation*1000:.1f}ms")