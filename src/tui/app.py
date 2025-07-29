"""Main TUI Application for Animal Well Flute - Cosmic Edition"""

from pathlib import Path
from typing import Optional
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen

from ..config import get_app_config
from ..services import SongServiceBase
from ..utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class CosmicFluteApp(App[None]):
    """Main TUI Application - Cosmic Flute Edition
    
    This is the central application class that manages all screens and provides
    the cosmic-themed user interface for the Animal Well Flute tool.
    """
    
    # Application metadata
    TITLE = "Cosmic Flute - Animal Well Edition"
    SUB_TITLE = "Navigate the musical cosmos with elegance"
    
    # CSS and theming
    CSS_PATH = Path(__file__).parent / "tui.css"
    
    # Global keybindings
    BINDINGS = [
        Binding("ctrl+c,ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+h", "toggle_help", "Help", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("ctrl+r", "refresh", "Refresh", show=False),
        Binding("f1", "help", "Help"),
    ]
    
    # Reactive attributes
    current_screen_name: reactive[str] = reactive("main", init=False)
    
    def __init__(self, *args, **kwargs):
        """Initialize the Cosmic Flute TUI Application"""
        super().__init__(*args, **kwargs)
        
        # Get configuration
        self.config = get_app_config()
        setup_logging(self.config.log_level)
        
        # Initialize services
        self.song_service = SongServiceBase(setup_logging_level=False)
        logger.info("CosmicFluteApp initialized")
        
        # Screen stack for navigation
        self._nav_stack = []
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        logger.info("CosmicFluteApp mounted, loading main screen")
        self.push_screen("main")
    
    def get_default_screen(self) -> Screen[None]:
        """Get the default screen (main screen)"""
        from .screens.main_screen import MainScreen
        return MainScreen(self.song_service)
    
    def action_quit(self) -> None:
        """Quit the application"""
        logger.info("User initiated quit")
        self.exit()
    
    def action_back(self) -> None:
        """Go back to previous screen"""
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()
            previous_screen = self._nav_stack[-1]
            logger.info(f"Navigating back to {previous_screen}")
            self.pop_screen()
        else:
            logger.debug("Already at root screen, cannot go back")
    
    def action_help(self) -> None:
        """Show help screen"""
        logger.info("Opening help screen")
        self.push_screen("help")
    
    def action_refresh(self) -> None:
        """Refresh current screen"""
        logger.info("Refreshing current screen")
        if hasattr(self.screen, 'refresh_data'):
            self.screen.refresh_data()
    
    def push_screen(self, screen_name: str, **kwargs) -> None:
        """Push a new screen onto the stack
        
        Args:
            screen_name: Name of the screen to push
            **kwargs: Additional arguments to pass to the screen
        """
        self._nav_stack.append(screen_name)
        self.current_screen_name = screen_name
        
        # Import screens dynamically to avoid circular imports
        if screen_name == "main":
            from .screens.main_screen import MainScreen
            screen = MainScreen(self.song_service, **kwargs)
        elif screen_name == "player":
            from .screens.song_player_screen import SongPlayerScreen
            screen = SongPlayerScreen(self.song_service, **kwargs)
        elif screen_name == "import":
            from .screens.import_screen import ImportScreen
            screen = ImportScreen(self.song_service, **kwargs)
        elif screen_name == "help":
            from .screens.help_screen import HelpScreen
            screen = HelpScreen(**kwargs)
        else:
            logger.error(f"Unknown screen: {screen_name}")
            return
        
        logger.info(f"Pushing screen: {screen_name}")
        super().push_screen(screen)
    
    def pop_screen(self) -> None:
        """Pop the current screen from the stack"""
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()
            self.current_screen_name = self._nav_stack[-1]
            logger.info(f"Popping screen, now at: {self.current_screen_name}")
        
        super().pop_screen()
    
    def navigate_to_player(self, song_name: str) -> None:
        """Navigate to the song player screen
        
        Args:
            song_name: Name of the song to play
        """
        logger.info(f"Navigating to player for song: {song_name}")
        self.push_screen("player", song_name=song_name)
    
    def navigate_to_import(self) -> None:
        """Navigate to the import screen"""
        logger.info("Navigating to import screen")
        self.push_screen("import")
    
    def navigate_to_main(self) -> None:
        """Navigate to the main screen"""
        logger.info("Navigating to main screen")
        # Clear the stack and go to main
        self._nav_stack = ["main"]
        self.current_screen_name = "main"
        
        # Pop all screens until we're at the main screen
        while len(self.screen_stack) > 1:
            super().pop_screen()
    
    def show_notification(self, message: str, severity: str = "information") -> None:
        """Show a notification message
        
        Args:
            message: The message to show
            severity: Severity level (information, warning, error)
        """
        # Map severity to appropriate styling
        severity_mapping = {
            "information": "info",
            "warning": "warning", 
            "error": "error",
            "success": "information"
        }
        
        textual_severity = severity_mapping.get(severity, "information")
        self.notify(message, severity=textual_severity)
        logger.info(f"Notification ({severity}): {message}")
    
    def exit_with_message(self, message: str, return_code: int = 0) -> None:
        """Exit the application with a message
        
        Args:
            message: Message to display before exiting
            return_code: Exit code (0 for success, non-zero for error)
        """
        logger.info(f"Exiting with message: {message} (code: {return_code})")
        self.show_notification(message)
        # Give a moment for the notification to be visible
        self.call_later(lambda: self.exit(return_code=return_code), delay=1.0)


# Convenience function for launching the TUI
def run_tui() -> int:
    """Run the Cosmic Flute TUI Application
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        app = CosmicFluteApp()
        return_code = app.run()
        logger.info(f"TUI application exited with code: {return_code}")
        return return_code or 0
    except KeyboardInterrupt:
        logger.info("TUI application interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"TUI application crashed: {e}")
        return 1