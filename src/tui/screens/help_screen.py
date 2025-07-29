"""Help Screen - The Codex - for Cosmic Flute TUI"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Markdown, TabbedContent, TabPane
from textual.binding import Binding

from ..components.header import AppHeader
from ..components.footer import AppFooter
from ...utils.logger import get_logger

logger = get_logger(__name__)


class HelpScreen(Screen):
    """Help Screen - The Codex
    
    Comprehensive help and documentation screen with markdown content.
    """
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+h", "back", "Back", show=False),
        Binding("q", "back", "Back", show=False),
    ]
    
    def __init__(self, **kwargs):
        """Initialize the help screen"""
        super().__init__(**kwargs)
    
    def compose(self) -> ComposeResult:
        """Compose the help screen layout"""
        yield AppHeader(show_subtitle=False)
        
        with Vertical(id="help-container"):
            with Horizontal(id="help-title-bar"):
                yield Markdown("# 📚 The Codex - Cosmic Flute Documentation")
            
            with TabbedContent(id="help-tabs"):
                # Getting Started Tab  
                with TabPane("🚀 Getting Started", id="getting-started-tab"):
                    yield Markdown(self._get_getting_started_content())
                
                # Keybindings Tab
                with TabPane("⌨️ Keybindings", id="keybindings-tab"):
                    yield Markdown(self._get_keybindings_content())
                
                # Features Tab
                with TabPane("✨ Features", id="features-tab"):
                    yield Markdown(self._get_features_content())
                
                # Jianpu Guide Tab
                with TabPane("🎵 Jianpu Guide", id="jianpu-tab"):
                    yield Markdown(self._get_jianpu_content())
                
                # About Tab
                with TabPane("ℹ️ About", id="about-tab"):
                    yield Markdown(self._get_about_content())
        
        yield AppFooter([("Esc/Q", "Back to Library")])
    
    def _get_getting_started_content(self) -> str:
        """Get the getting started help content"""
        return """
# 🚀 Getting Started with Cosmic Flute

Welcome to the **Cosmic Flute TUI** - your gateway to the musical cosmos of Animal Well!

## First Steps

1. **Browse Songs**: Navigate the song library using arrow keys or search
2. **Select & Play**: Press Enter on any song to open the player
3. **Import New Songs**: Use the Import screen to add your own compositions
4. **Get Help**: Press F1 or ? for help anytime

## Navigation Basics

- **Arrow Keys**: Navigate through lists and tables
- **Enter**: Select items or confirm actions
- **Escape**: Go back to previous screen
- **Tab**: Move between interface elements
- **Space**: Play/pause in the player

## Quick Tour

### 🌉 The Bridge (Main Screen)
Your central hub for browsing the song library. Features:
- Real-time search as you type
- Song details panel showing metadata
- Direct access to import and help

### 🏛️ The Observatory (Song Player)
Immersive playing experience with:
- Auto-scrolling musical notation
- Visual flute fingering guide
- Playback controls and settings
- Strategy selection for difficult passages

### 🌌 The Wormhole (Import Portal)
Advanced import capabilities:
- File import from YAML/JSON
- AI-powered image recognition for Jianpu notation
- Batch processing support

## Tips for New Users

💡 **Start Simple**: Try playing easier songs first to get familiar with the controls

💡 **Use Search**: Type to quickly find songs by name or description

💡 **Experiment with Strategies**: Different mapping strategies work better for different songs

💡 **Practice Mode**: Use the player's manual navigation to practice difficult sections

Ready to explore the cosmos? Return to The Bridge and select your first song!
        """
    
    def _get_keybindings_content(self) -> str:
        """Get the keybindings help content"""
        return """
# ⌨️ Keybinding Reference

## Global Keybindings
*Available throughout the application*

| Key | Action | Description |
|-----|--------|-------------|
| `F1` or `?` | Help | Open this help screen |
| `Ctrl+Q` | Quit | Exit the application |
| `Ctrl+C` | Quit | Alternative exit method |
| `Escape` | Back | Return to previous screen |
| `Ctrl+R` | Refresh | Refresh current screen data |

## The Bridge (Main Screen)

| Key | Action | Description |
|-----|--------|-------------|
| `↑` `↓` | Navigate | Move through song list |
| `Enter` | Play Song | Open selected song in player |
| `I` | Import | Open the import screen |
| `/` | Search | Focus the search input |
| `Escape` | Clear Search | Clear current search query |
| `Ctrl+H` | Help | Open help screen |

## The Observatory (Song Player)

| Key | Action | Description |
|-----|--------|-------------|
| `Space` | Play/Pause | Toggle playback |
| `←` `→` | Navigate | Move between notes |
| `Home` | First Note | Jump to beginning |
| `End` | Last Note | Jump to end |
| `R` | Restart | Restart from beginning |
| `Escape` | Back | Return to song library |

## The Wormhole (Import Screen)

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+I` | Import File | Focus file import tab |
| `Ctrl+O` | Import Image | Focus image import tab |
| `Ctrl+R` | Refresh Status | Update AI service status |
| `Escape` | Back | Return to main screen |

## Navigation Tips

🎯 **Tab Navigation**: Use Tab to move between form fields and buttons

🎯 **Arrow Keys**: Navigate lists, tables, and tabs

🎯 **Type to Search**: In lists, start typing to filter items

🎯 **Context Sensitive**: Some keys change function based on current focus

🎯 **Visual Feedback**: Active elements are highlighted with cosmic colors
        """
    
    def _get_features_content(self) -> str:
        """Get the features help content"""
        return """
# ✨ Cosmic Flute Features

## Core Features

### 🎵 Song Library Management
- **Browse Collection**: View all available songs with metadata
- **Real-time Search**: Instant filtering as you type
- **Song Details**: Preview notation, BPM, difficulty, and description
- **Sortable Columns**: Click headers to sort by different criteria

### 🎹 Advanced Song Player
- **Visual Notation**: See Jianpu notation with current note highlighting
- **Flute Fingering**: Visual guide showing exact key combinations
- **Auto-scrolling**: Follow along as the song plays
- **Manual Navigation**: Practice specific sections at your own pace
- **Playback Controls**: Play, pause, restart, and tempo adjustment

### 🎯 Smart Mapping Strategies
- **Optimal**: Automatically finds the best key mapping
- **High/Low Priority**: Prefer higher or lower octaves
- **Auto Selection**: Intelligently chooses the best strategy
- **Manual Override**: Set custom pitch offsets

### 📥 Multi-Format Import
- **File Import**: Support for YAML and JSON song files
- **Image Recognition**: AI-powered Jianpu notation extraction
- **Batch Processing**: Import multiple files or images at once
- **Format Validation**: Automatic checking of song data integrity

## Advanced Features

### 🤖 AI Integration
- **Multiple Providers**: Support for Google Gemini and Doubao
- **Smart Recognition**: Advanced OCR for handwritten notation
- **Auto-correction**: Intelligent fixing of common notation errors
- **Confidence Scoring**: Quality assessment of recognition results

### 🎨 Cosmic Theme
- **Dark Space Aesthetic**: Easy on the eyes for long practice sessions
- **Color-coded Elements**: Intuitive visual feedback system
- **Responsive Layout**: Adapts to different terminal sizes
- **Accessibility**: High contrast for better readability

### ⚡ Performance Optimizations
- **Lazy Loading**: Fast startup with on-demand content loading
- **Efficient Rendering**: Smooth scrolling and responsive interface
- **Memory Management**: Optimized for large song collections
- **Background Processing**: Non-blocking import operations

### 🔧 Customization Options
- **Configurable Settings**: Adjust BPM, ready time, and other preferences
- **Multiple Strategies**: Choose the mapping approach that works best
- **Import Sources**: Flexible input from files, images, or manual entry
- **Output Formats**: Export songs in various formats

## Unique Capabilities

🌟 **Real-time Visualization**: See exactly what keys to press as you play

🌟 **Practice Mode**: Navigate through songs manually to learn difficult sections

🌟 **Smart Transposition**: Automatically adjust songs to playable ranges

🌟 **Batch Operations**: Process multiple songs or images efficiently

🌟 **Cross-platform**: Works on any system with Python and a terminal

The Cosmic Flute TUI combines the power of modern terminal interfaces with the charm of retro gaming aesthetics. Whether you're a casual player or a serious musician, these features help you master the Animal Well flute with style and efficiency.
        """
    
    def _get_jianpu_content(self) -> str:
        """Get the Jianpu notation guide content"""
        return """
# 🎵 Jianpu Notation Guide

## What is Jianpu?

**Jianpu (简谱)** is a numbered musical notation system widely used in Chinese music education. Instead of traditional staff notation, it uses numbers 1-7 to represent the seven notes of a major scale.

## Basic Notation

### Scale Degrees
```
1 = Do (C)    |  5 = Sol (G)
2 = Re (D)    |  6 = La (A)  
3 = Mi (E)    |  7 = Ti (B)
4 = Fa (F)    |  0 = Rest
```

### Octave Indicators
- **High Octave**: `h1, h2, h3...` (one octave up)
- **Low Octave**: `l1, l2, l3...` (one octave down)  
- **Normal**: `1, 2, 3...` (middle octave)

## Advanced Notation

### Note Groups
- **Parentheses**: `(1 2 3)` = Group of shorter notes
- **Ties**: `1-` = Extend previous note duration
- **Dotted Notes**: `1d` = Dotted note (1.5x duration)

### Accidentals
- **Sharp**: `1#` = Raised by semitone
- **Flat**: `1b` = Lowered by semitone

## Animal Well Mapping

The flute in Animal Well uses 8-directional input:

```
    ↖  ↑  ↗
     \\ │ /
  ← ── ● ── →
     / │ \\
    ↙  ↓  ↘
```

### Typical Mappings
- **1 (Do)**: `↓` (Down)
- **2 (Re)**: `↙` (Down-Left)  
- **3 (Mi)**: `←` (Left)
- **4 (Fa)**: `↖` (Up-Left)
- **5 (Sol)**: `↑` (Up)
- **6 (La)**: `↗` (Up-Right)
- **7 (Ti)**: `→` (Right)

*Note: Exact mappings may vary based on strategy and transposition*

## Song File Format

Songs are stored in YAML format:

```yaml
name: "Song Title"
bpm: 120
offset: 0.0
description: "Song description"
jianpu:
  - "1 2 3 4 | 5 6 7 1"
  - "5 5 6 5 | 4 3 2 1"
  - "(1 2) (3 4) 5 0"
```

### File Structure
- **name**: Display name of the song
- **bpm**: Beats per minute (tempo)
- **offset**: Pitch adjustment in semitones
- **description**: Optional song description
- **jianpu**: Array of notation strings (one per bar)

### Bar Notation
- **Pipe `|`**: Bar separator (optional, for readability)
- **Spaces**: Separate individual notes
- **Parentheses**: Group notes for shorter durations
- **Numbers**: Scale degrees (1-7)
- **Zero**: Rest/silence

## Import Tips

### From Images
1. Ensure clear, high-contrast images
2. Jianpu should be horizontally aligned
3. Avoid handwriting if possible
4. Multiple pages are automatically merged

### From Files
1. Use UTF-8 encoding for international characters
2. Validate YAML syntax before importing
3. Test with simple songs first
4. Check offset values for proper pitch

## Practice Suggestions

🎼 **Start Simple**: Begin with basic 1-2-3-4-5 patterns

🎼 **Use Groupings**: Practice note groups `(1 2 3)` as single units

🎼 **Master Octaves**: Get comfortable with `l` and `h` prefixes

🎼 **Learn Rhythms**: Understand how groupings affect timing

🎼 **Transpose**: Experiment with different offset values

The Jianpu system makes music accessible to everyone, regardless of traditional music training. With practice, you'll be reading and playing complex pieces with ease!
        """
    
    def _get_about_content(self) -> str:
        """Get the about/credits content"""
        return """
# ℹ️ About Cosmic Flute

## Project Information

**Cosmic Flute** is a Terminal User Interface (TUI) for the Animal Well Flute automation tool. It transforms the command-line experience into an immersive, visually stunning interface that makes musical practice both functional and beautiful.

### Version Information
- **Application**: Animal Well Flute - Cosmic Edition
- **TUI Framework**: Textual (Python)
- **Theme**: Cosmic/Space-inspired dark theme
- **License**: Open Source

## Features Overview

🎵 **Complete Song Management**
- Browse, search, and organize your song collection
- Import from multiple formats (YAML, JSON, images)
- AI-powered notation recognition

🎹 **Interactive Player**  
- Visual notation with real-time highlighting
- Flute fingering diagrams and key combinations
- Multiple mapping strategies for optimal playability

🌌 **Cosmic Design**
- Space-themed visual design with stellar colors
- Intuitive navigation and keyboard shortcuts
- Responsive layout that adapts to your terminal

🤖 **AI Integration**
- Support for multiple AI providers (Gemini, Doubao)
- Intelligent image-to-notation conversion
- Batch processing capabilities

## Technology Stack

### Core Dependencies
- **Python 3.8+**: Core runtime environment
- **Textual**: Modern TUI framework for rich interfaces
- **Rich**: Advanced terminal rendering and styling
- **PyYAML**: Configuration and song file parsing
- **Pynput**: Game input automation
- **Pydantic**: Data validation and settings management

### AI/ML Dependencies
- **Google Generative AI**: Gemini API integration
- **Pillow**: Image processing for OCR
- **Requests**: HTTP client for API calls

### Development Tools
- **Pytest**: Testing framework
- **Black**: Code formatting
- **MyPy**: Type checking

## Design Philosophy

The Cosmic Flute TUI follows several key design principles:

### 🎯 **User-Centric Design**
Every interface element is designed with the user experience in mind. Complex operations are simplified through intuitive workflows and clear visual feedback.

### 🌌 **Aesthetic Excellence**
The cosmic theme isn't just decorative - it creates a focused, calming environment that enhances the musical practice experience.

### ⚡ **Performance First**
Despite rich visuals, the interface remains responsive and efficient, even with large song collections.

### 🔧 **Extensibility**
Modular architecture allows for easy addition of new features, import formats, and customization options.

## Contributing

Cosmic Flute is an open-source project that welcomes contributions:

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new capabilities
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve help content and guides
- **Song Collections**: Share your Jianpu arrangements

## Acknowledgments

### Inspiration
- **Animal Well**: The beautiful indie game that inspired this tool
- **Textual**: The amazing Python TUI framework
- **Traditional Jianpu**: Centuries of Chinese musical notation

### Special Thanks
- The open-source community for foundational tools
- Beta testers who provided valuable feedback
- Musicians who shared their Jianpu arrangements
- The Animal Well community for their enthusiasm

## Support

Need help or have questions?

- **Documentation**: Press F1 anywhere in the application
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions with other users

---

*"In the cosmic dance of music and technology, every note finds its perfect place among the stars."*

🎵 Happy playing, cosmic musicians! 🌟
        """
    
    def action_back(self) -> None:
        """Go back to the previous screen"""
        logger.info("Returning from help screen")
        self.app.pop_screen()