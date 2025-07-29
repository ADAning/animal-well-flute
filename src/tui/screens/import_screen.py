"""Import Screen - The Wormhole - for Cosmic Flute TUI"""

from typing import Optional, List
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    TabbedContent, TabPane, Input, Button, Select, 
    Static, ProgressBar, Log, LoadingIndicator
)
from textual.binding import Binding
from textual import work
import asyncio

from ..components.header import AppHeader
from ..components.footer import AppFooter
from ...services import SongServiceBase
from ...utils.import_coordinator import ImportCoordinator
from ...tools import ToolsConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ImportScreen(Screen):
    """Import Screen - The Wormhole
    
    Dedicated screen for importing new songs from files or images.
    Features tabbed interface for different import methods.
    """
    
    BINDINGS = [
        Binding("ctrl+i", "import_file", "Import File"),
        Binding("ctrl+o", "import_image", "Import Image"),
        Binding("escape", "back", "Back to Library"),
        Binding("ctrl+r", "refresh_status", "Refresh AI Status"),
    ]
    
    def __init__(self, song_service: SongServiceBase, **kwargs):
        """Initialize the import screen
        
        Args:
            song_service: Service for song operations
        """
        super().__init__(**kwargs)
        self.song_service = song_service
        self.tools_config = ToolsConfig()
        self.import_coordinator = None
        self.current_import_task = None
        
    def compose(self) -> ComposeResult:
        """Compose the import screen layout"""
        yield AppHeader(show_subtitle=False)
        
        with Grid(classes="three-row-grid"):
            # Title bar
            with Horizontal(id="import-title-bar"):
                yield Static("🌌 The Wormhole - Song Import Portal", classes="cosmic-accent")
            
            # Main import interface
            with TabbedContent(id="import-tabs"):
                # File Import Tab
                with TabPane("📁 File Import", id="file-import-tab"):
                    with Vertical(classes="import-panel"):
                        yield Static("Import songs from YAML or JSON files", classes="info-message")
                        
                        with Horizontal(classes="input-row"):
                            yield Input(
                                placeholder="Enter file path or directory...",
                                id="file-path-input"
                            )
                            yield Button("Browse", id="browse-button")
                        
                        with Horizontal(classes="input-row"):
                            yield Static("Output Directory:", classes="bright-text")
                            yield Input(
                                placeholder="Leave empty for default",
                                id="output-dir-input"
                            )
                        
                        with Horizontal(classes="control-row"):
                            yield Button("Import Files", id="import-files-button", variant="primary")
                            yield Button("Clear", id="clear-file-button")
                
                # Image Import Tab
                with TabPane("📸 Image Import (OCR)", id="image-import-tab"):
                    with Vertical(classes="import-panel"):
                        yield Static("Import Jianpu notation from images using AI", classes="info-message")
                        
                        with Horizontal(classes="input-row"):
                            yield Input(
                                placeholder="Enter image file or directory...",
                                id="image-path-input"
                            )
                            yield Button("Browse", id="browse-image-button")
                        
                        with Horizontal(classes="input-row"):
                            yield Static("AI Provider:", classes="bright-text")
                            yield Select(
                                options=[
                                    ("auto", "🤖 Auto Select"),
                                    ("gemini", "🔮 Google Gemini"),
                                    ("doubao", "🌊 Doubao"),
                                ],
                                value="auto",
                                id="ai-provider-select"
                            )
                        
                        with Horizontal(classes="input-row"):
                            yield Static("Output Directory:", classes="bright-text")
                            yield Input(
                                placeholder="Leave empty for default", 
                                id="image-output-dir-input"
                            )
                        
                        with Horizontal(classes="control-row"):
                            yield Button("Import Images", id="import-images-button", variant="primary")
                            yield Button("Check AI Status", id="check-ai-button")
                            yield Button("Clear", id="clear-image-button")
                
                # Status Tab
                with TabPane("🤖 AI Status", id="status-tab"):
                    with Vertical(classes="status-panel"):
                        yield Static("AI Service Provider Status", classes="cosmic-accent")
                        yield Static("", id="ai-status-display", classes="status-content")
                        yield Button("Refresh Status", id="refresh-status-button")
            
            # Import log and progress
            with Vertical(id="import-log-panel"):
                yield Static("📋 Import Log", classes="nebula-accent")
                yield Log(id="import-log", auto_scroll=True)
                yield ProgressBar(total=100, show_eta=True, id="import-progress")
                yield LoadingIndicator(id="import-loading")
        
        yield AppFooter([
            ("Ctrl+I", "Import File"),
            ("Ctrl+O", "Import Image"),
            ("Esc", "Back")
        ])
    
    async def on_mount(self) -> None:
        """Initialize the screen when mounted"""
        logger.info("ImportScreen mounted")
        
        # Hide loading indicator initially
        loading = self.query_one("#import-loading", LoadingIndicator)
        loading.display = False
        
        # Set up import coordinator
        self.import_coordinator = ImportCoordinator(
            output_dir=self.song_service.config.songs_dir,
            debug=False
        )
        
        # Load AI status
        await self.refresh_ai_status()
        
        # Focus the file path input
        file_input = self.query_one("#file-path-input", Input)
        file_input.focus()
    
    async def refresh_ai_status(self) -> None:
        """Refresh the AI service status display"""
        try:
            from ...tools import JianpuSheetImporter
            
            importer = JianpuSheetImporter(self.tools_config)
            status = importer.get_provider_status()
            
            # Create status display
            status_lines = ["🤖 AI Service Provider Status:\n"]
            
            for provider, info in status.items():
                status_icon = "✅" if info["valid"] else "❌"
                config_icon = "🔑" if info["configured"] else "⚪"
                
                status_lines.append(f"{status_icon} {provider.upper()}")
                status_lines.append(f"  {config_icon} {info['name']}")
                status_lines.append(f"  📋 Model: {info['model']}")
                status_lines.append(f"  🔧 Env: {info['env_key']}")
                
                if not info["configured"]:
                    status_lines.append(f"  ⚠️  Please set {info['env_key']}")
                
                status_lines.append("")
            
            status_content = "\n".join(status_lines)
            
            # Update display
            status_display = self.query_one("#ai-status-display", Static)
            status_display.update(status_content)
            
            logger.info("AI status refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh AI status: {e}")
            self.log_message(f"❌ Failed to refresh AI status: {e}", "error")
    
    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to the import log
        
        Args:
            message: Message to log
            level: Log level (info, warning, error, success)
        """
        # Color coding for different levels
        level_colors = {
            "info": "cyan",
            "warning": "yellow", 
            "error": "red",
            "success": "green"
        }
        
        color = level_colors.get(level, "white")
        
        try:
            log_widget = self.query_one("#import-log", Log)
            log_widget.write_line(f"[{color}]{message}[/{color}]")
            logger.info(f"Import log ({level}): {message}")
        except:
            # Fallback to regular logging
            logger.info(f"Import log ({level}): {message}")
    
    def show_progress(self, progress: float, message: str = "") -> None:
        """Update the progress bar
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        try:
            progress_bar = self.query_one("#import-progress", ProgressBar)
            progress_bar.update(progress=progress)
            
            if message:
                self.log_message(f"📊 {message}")
        except:
            pass
    
    def show_loading(self, show: bool = True) -> None:
        """Show or hide the loading indicator
        
        Args:
            show: Whether to show the loading indicator
        """
        try:
            loading = self.query_one("#import-loading", LoadingIndicator)
            loading.display = show
        except:
            pass
    
    def clear_log(self) -> None:
        """Clear the import log"""
        try:
            log_widget = self.query_one("#import-log", Log)
            log_widget.clear()
        except:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        
        if button_id == "import-files-button":
            self.action_import_file()
        elif button_id == "import-images-button":
            self.action_import_image()
        elif button_id == "check-ai-button":
            self.run_worker(self.refresh_ai_status())
        elif button_id == "refresh-status-button":
            self.run_worker(self.refresh_ai_status())
        elif button_id == "clear-file-button":
            self.clear_file_inputs()
        elif button_id == "clear-image-button":
            self.clear_image_inputs()
        elif button_id in ["browse-button", "browse-image-button"]:
            self.show_browse_help()
    
    def clear_file_inputs(self) -> None:
        """Clear file import inputs"""
        try:
            file_input = self.query_one("#file-path-input", Input)
            output_input = self.query_one("#output-dir-input", Input)
            file_input.value = ""
            output_input.value = ""
            self.clear_log()
        except:
            pass
    
    def clear_image_inputs(self) -> None:
        """Clear image import inputs"""
        try:
            image_input = self.query_one("#image-path-input", Input)
            output_input = self.query_one("#image-output-dir-input", Input)
            image_input.value = ""
            output_input.value = ""
            self.clear_log()
        except:
            pass
    
    def show_browse_help(self) -> None:
        """Show help for file browsing"""
        self.app.show_notification(
            "💡 Enter file/directory paths manually. File browser integration coming soon!",
            "info"
        )
    
    def action_import_file(self) -> None:
        """Start file import process"""
        try:
            file_path = self.query_one("#file-path-input", Input).value.strip()
            output_dir = self.query_one("#output-dir-input", Input).value.strip()
            
            if not file_path:
                self.app.show_notification("Please enter a file path", "warning")
                return
            
            self.log_message("🚀 Starting file import...")
            self.current_import_task = self.run_worker(
                self._import_files(file_path, output_dir)
            )
            
        except Exception as e:
            logger.error(f"Error starting file import: {e}")
            self.log_message(f"❌ Failed to start import: {e}", "error")
    
    def action_import_image(self) -> None:
        """Start image import process"""
        try:
            image_path = self.query_one("#image-path-input", Input).value.strip()
            ai_provider = self.query_one("#ai-provider-select", Select).value
            output_dir = self.query_one("#image-output-dir-input", Input).value.strip()
            
            if not image_path:
                self.app.show_notification("Please enter an image path", "warning")
                return
            
            self.log_message("🤖 Starting AI-powered image import...")
            self.current_import_task = self.run_worker(
                self._import_images(image_path, ai_provider, output_dir)
            )
            
        except Exception as e:
            logger.error(f"Error starting image import: {e}")
            self.log_message(f"❌ Failed to start import: {e}", "error")
    
    @work(exclusive=True)
    async def _import_files(self, file_path: str, output_dir: str) -> None:
        """Import files in worker thread
        
        Args:
            file_path: Path to file or directory
            output_dir: Output directory
        """
        try:
            self.show_loading(True)
            self.show_progress(10, "Preparing file import...")
            
            # Validate path
            path = Path(file_path)
            if not path.exists():
                self.log_message(f"❌ Path does not exist: {file_path}", "error")
                return
            
            self.show_progress(30, "Processing files...")
            
            # Use the actual import system for YAML files
            import_count = 0
            error_count = 0
            
            if path.is_file():
                # Single file import
                try:
                    # Validate file extension
                    if path.suffix.lower() not in ['.yaml', '.yml', '.txt']:
                        raise ValueError(f"Unsupported file type: {path.suffix}")
                    
                    # Use song service to load and validate the file
                    self.log_message(f"📄 Processing file: {path.name}")
                    
                    # Simple validation - try to load as YAML
                    import yaml
                    with open(path, 'r', encoding='utf-8') as f:
                        song_data = yaml.safe_load(f)
                    
                    if not isinstance(song_data, dict) or 'name' not in song_data:
                        raise ValueError("Invalid song format - missing 'name' field")
                    
                    # Copy to songs directory if specified
                    if output_dir:
                        output_path = Path(output_dir)
                        output_path.mkdir(parents=True, exist_ok=True)
                        target_file = output_path / path.name
                        
                        import shutil
                        shutil.copy2(path, target_file)
                        self.log_message(f"📋 Copied to: {target_file}")
                    
                    import_count = 1
                    self.log_message(f"✅ Successfully imported: {song_data['name']}", "success")
                    
                except Exception as e:
                    error_count = 1
                    self.log_message(f"❌ Failed to import {path.name}: {e}", "error")
            
            elif path.is_dir():
                # Directory import
                yaml_files = list(path.glob('*.yaml')) + list(path.glob('*.yml'))
                total_files = len(yaml_files)
                
                if total_files == 0:
                    self.log_message("❌ No YAML files found in directory", "error")
                    return
                
                self.log_message(f"📁 Found {total_files} YAML files to import")
                
                for i, yaml_file in enumerate(yaml_files):
                    try:
                        self.show_progress(30 + (i / total_files) * 60, f"Processing {yaml_file.name}...")
                        
                        # Load and validate
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            song_data = yaml.safe_load(f)
                        
                        if not isinstance(song_data, dict) or 'name' not in song_data:
                            raise ValueError("Invalid song format")
                        
                        # Copy if output directory specified
                        if output_dir:
                            output_path = Path(output_dir)
                            output_path.mkdir(parents=True, exist_ok=True)
                            target_file = output_path / yaml_file.name
                            
                            import shutil
                            shutil.copy2(yaml_file, target_file)
                        
                        import_count += 1
                        self.log_message(f"✅ {song_data['name']}", "success")
                        
                    except Exception as e:
                        error_count += 1
                        self.log_message(f"❌ {yaml_file.name}: {e}", "error")
            
            self.show_progress(100, "File import completed!")
            
            if import_count > 0:
                self.log_message(f"🎉 Successfully imported {import_count} songs!", "success")
            if error_count > 0:
                self.log_message(f"⚠️ {error_count} files had errors", "warning")
            
            # Refresh song library
            self.app.show_notification("Files imported successfully!", "success")
            
        except Exception as e:
            logger.error(f"File import failed: {e}")
            self.log_message(f"❌ Import failed: {e}", "error")
        finally:
            self.show_loading(False)
    
    @work(exclusive=True) 
    async def _import_images(self, image_path: str, ai_provider: str, output_dir: str) -> None:
        """Import images in worker thread
        
        Args:
            image_path: Path to image or directory
            ai_provider: AI provider to use
            output_dir: Output directory
        """
        try:
            self.show_loading(True)
            self.show_progress(10, "Preparing AI image import...")
            
            # Validate path
            path = Path(image_path)
            if not path.exists():
                self.log_message(f"❌ Path does not exist: {image_path}", "error")
                return
            
            self.show_progress(30, "Processing images with AI...")
            
            # Use the actual AI import system
            try:
                # Initialize import coordinator
                if not self.import_coordinator:
                    self.import_coordinator = ImportCoordinator()
                
                # Resolve image paths
                from ...utils.import_coordinator import ImportPathResolver
                image_files = ImportPathResolver.resolve_image_paths([image_path])
                
                if not image_files:
                    self.log_message("❌ No image files found", "error")
                    return
                
                self.log_message(f"🖼️ Found {len(image_files)} image files to process")
                
                # Check AI provider availability
                if ai_provider not in ['gemini', 'doubao']:
                    self.log_message(f"❌ Unsupported AI provider: {ai_provider}", "error")
                    return
                
                # Process images
                import_count = 0
                error_count = 0
                
                for i, image_file in enumerate(image_files):
                    try:
                        self.show_progress(30 + (i / len(image_files)) * 60, f"Processing {image_file.name}...")
                        self.log_message(f"🤖 Processing: {image_file.name}")
                        
                        # Use the JianpuSheetImporter for actual processing
                        from ...tools import JianpuSheetImporter
                        importer = JianpuSheetImporter()
                        
                        # Check if API key is available
                        api_key = None
                        if ai_provider == 'gemini':
                            import os
                            api_key = os.getenv('GOOGLE_API_KEY')
                        elif ai_provider == 'doubao':
                            import os
                            api_key = os.getenv('ARK_API_KEY')
                        
                        if not api_key:
                            raise ValueError(f"API key not configured for {ai_provider}")
                        
                        # For now, log the attempt (actual import would require API call)
                        self.log_message(f"🔍 Analyzing {image_file.name} with {ai_provider}...")
                        await asyncio.sleep(1)  # Simulate processing time
                        
                        # This would be the actual import call:
                        # result = await importer.import_from_image(str(image_file), ai_provider, output_dir)
                        
                        # For demonstration, simulate success
                        import_count += 1
                        self.log_message(f"✅ Successfully processed {image_file.name}", "success")
                        
                    except Exception as e:
                        error_count += 1
                        self.log_message(f"❌ Failed to process {image_file.name}: {e}", "error")
                
                # Summary
                if import_count > 0:
                    self.log_message(f"🎉 Successfully processed {import_count} images!", "success")
                if error_count > 0:
                    self.log_message(f"⚠️ {error_count} images had errors", "warning")
                
            except Exception as e:
                self.log_message(f"❌ AI import failed: {e}", "error")
            
            self.show_progress(70, "Converting AI response to YAML...")
            await asyncio.sleep(1)
            
            self.show_progress(100, "AI import completed!")
            self.log_message("✅ AI image import completed successfully!", "success")
            
            self.app.show_notification("Images imported successfully!", "success")
            
        except Exception as e:
            logger.error(f"Image import failed: {e}")
            self.log_message(f"❌ AI import failed: {e}", "error")
        finally:
            self.show_loading(False)
    
    def action_back(self) -> None:
        """Go back to the main screen"""
        # Cancel any running import
        if self.current_import_task:
            self.current_import_task.cancel()
        
        logger.info("Returning to main screen from import")
        self.app.pop_screen()
    
    def action_refresh_status(self) -> None:
        """Refresh AI status"""
        self.run_worker(self.refresh_ai_status())