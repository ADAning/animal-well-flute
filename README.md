# Animal Well Flute

A command-line utility to convert Jianpu (numbered musical notation) into directional inputs for the flute in the game *Animal Well*. This tool allows players to easily translate their favorite melodies into playable in-game flute songs.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
  - [List Available Songs](#list-available-songs)
  - [Play a Song](#play-a-song)
  - [Convert a Song File](#convert-a-song-file)
- [Song File Format](#song-file-format)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Jianpu to Direction Conversion**: Automatically converts songs written in Jianpu into the game's 8-directional input sequence.
- **Song Library**: Manage a local library of songs defined in simple `.yaml` files.
- **CLI Player**: "Plays" songs in the terminal, displaying the sequence of directional inputs with timing.
- **Extensible**: Easily add new songs by creating new `.yaml` files.

### Coming Soon

- [ ] **Jianpu Auto Importer**: This feature parses an image of a numbered jianpu, converting it into the project's standard .yaml song format. Typically, only minor modifications are needed to make the song playable.
- [ ] **Expanded Song Library**: More pre-converted songs will be added to the library. Community contributions for new songs are highly encouraged!

## How It Works

The flute in *Animal Well* is played using 8 directions on a controller, corresponding to the 8 notes of a C Major scale. This tool works by mapping the provided Jianpu notation to these in-game directions.

1.  **Parse**: It reads the `jianpu` list from a `.yaml` song file.
2.  **Convert**: It translates each Jianpu symbol (e.g., `5`, `h1`, `(3,2)`) into its corresponding directional input, applying any necessary transposition based on the chosen strategy.
3.  **Play**: It displays the final directional sequence in the command line, providing a clear guide for in-game performance.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ADAning/animal-well-flute.git
    cd animal-well-flute
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Usage

The tool is operated via `cli.py`.

### List Available Songs

To see all the songs currently in your `songs/` directory:

```bash
python cli.py list
```

### Play a Song

To "play" a song from your library, use the `play` command followed by the song's name (without the `.yaml` extension).

```bash
python cli.py play big_fish
```

This will output the directional sequence to your terminal.

#### Advanced: Choosing a Conversion Strategy

Some songs may contain notes that are outside the flute's default playable range. The `--strategy` flag allows you to control how the tool handles these cases by transposing the song.

```bash
python cli.py play <song_name> --strategy <strategy_name> [parameter]
```

**Available Strategies:**

- **`optimal` (Default):** Automatically calculates the best pitch shift (transposition) to fit the maximum number of notes into the flute's range.
- **`high`**: Prefers to transpose the song to a higher pitch.
- **`low`**: Prefers to transpose the song to a lower pitch.
- **`auto [high|low|optimal]`**: Automatically selects the best strategy among `high`, `low`, and `optimal`. You can provide an optional preference (e.g., `auto high`).
- **`manual <offset / song>`**: Manually specify a pitch shift in semitones. The `<offset>` can be a positive or negative number (e.g., `1.5`, `-2.0`). Or specify the offset in the song.
- **`none`**: Applies no transposition (`manual 0.0`).

**Example:**

If a song sounds too high, you can try playing it with a lower transposition:

```bash
python cli.py play your_song --strategy low
```

Or, manually transpose it down by two semitones:

```bash
python cli.py play your_song --strategy manual -2.0
```

If you wish to use the default offset in a specific song (if any):

```bash
python cli.py play your_song --strategy manual song
```

### Convert a Song File

If you have a song file that is not in the `songs/` directory, you can convert it directly using the `convert` command.

```bash
python cli.py convert /path/to/your/song.yaml
```

## Song File Format

Songs are defined in `.yaml` files using a format based on numbered musical notation (Jianpu).

**Keys:**

- `name` (string): The name of the song.
- `bpm` (integer): The tempo of the song in beats per minute.
- `jianpu` (list of strings): The core of the song, written in a specialized Jianpu format. Each string in the list typically represents a bar of music.
- `offset` (float, optional): A default transposition in semitones for the song.
- `description` (string, optional): A brief description or note about the song.

**Jianpu Format Details:**

The `jianpu` format uses numbers `1-7` to represent notes. Special characters and notations are used for rhythm, octaves, and rests:

- **Octaves**: `h` for high (e.g., `h1`), `l` for low (e.g., `l6`).
- **Rhythm**: Parentheses `()` are used for shorter notes, and `d` might indicate a dotted note (e.g., `5d`).
- **Rests**: `0` represents a rest.
- **Chords/Groups**: Notes within parentheses like `(3,2)` can represent quick successive notes or chords.

**Example (`songs/a_dream.yaml`):**

```yaml
name: A Dream
bpm: 100
jianpu:
  - 0 0 (0,3) (3,4)
  - 5 (3) 5d (0,5)
  - 5 (3,2) 2 (1,1)
  - (h1,7) (6,7) (6,5) (5,3)
  - (6,5) (3,5) 0 (0,5)
  - (5,4) (3,4) 4 (0,4)
  - (3,2) (2,1) 1 (l6,1)
  - (2,2) (2,3) (2,3) (2,l6) 2 0
offset: 0.5
description: 梦一场
```

## Project Structure

```
animal-well-flute/
├── cli.py              # Main CLI entry point
├── requirements.txt    # Project dependencies
├── songs/              # Directory for song .yaml files
│   ├── example_song.yaml
│   └── ...
├── src/                # Source code
│   ├── core/           # Core logic (parsing, conversion, playing)
│   ├── data/           # Data models and song management
│   └── utils/          # Utility functions (e.g., logging)
└── tests/              # Unit tests
```

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new feature branch (`git checkout -b feature/your-feature-name`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/your-feature-name`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
