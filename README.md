# Jellytools

A Python package for enhancing Jellyfin Media Servers.

## Features

- Generate animated library cards from media posters
- Multiple animation styles: grid, waterfall, mosaic, and spiral
- Synchronize collections and artwork from Plex to Jellyfin
- Command-line interface for easy use
- Export to high-quality MP4 video format

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/jellytools.git
cd jellytools

# Install the package
pip install -e .
```

### Dependencies

- Python 3.7+
- FFmpeg (for video generation)
- Required Python packages (automatically installed):
  - pygame
  - opencv-python
  - plexapi
  - requests
  - click

## Quick Start

1. Initialize a configuration file:

```bash
jellytools init
```

2. Edit the generated `config.py` file with your Jellyfin/Plex server details

3. Generate library card animations:

```bash
jellytools generate
```

## Configuration

The configuration file (`config.py`) contains the following settings:

```python
# Jellyfin server configuration (primary)
JELLYFIN_URL = "http://localhost:8096"
JELLYFIN_API_KEY = "your-jellyfin-api-key"
JELLYFIN_LIBRARIES = ["Movies", "TV Shows"]

# Plex server configuration (used for syncing)
PLEX_URL = "http://localhost:32400"
PLEX_TOKEN = "your-plex-token"
PLEX_LIBRARIES = ["Movies", "TV Shows"]

# General configuration
POSTER_DIRECTORY = "posters"
FONT_PATH = "./font.ttf"
CAPITALIZE_TEXT = True

# Animation configuration
DEFAULT_ANIMATION_TYPE = "grid"
DEFAULT_OUTPUT_DIR = "output"

# Per-library animation configuration
LIBRARY_ANIMATIONS = {
    "Movies": {
        "animation_type": "mosaic"  # Single animation type
    },
    "TV Shows": {
        "animation_types": ["waterfall", "spiral"]  # Multiple animation types
    }
}
```

## Usage

### List Available Libraries

```bash
jellytools libraries
```

### Show Animation Configuration

```bash
jellytools animations
```

This command displays:
- The default animation type
- All available animation types
- The animation configurations for each library
- Which libraries are using multiple animation types

### Generate Library Cards

```bash
# Basic usage (using default animation or per-library configuration)
jellytools generate

# Specify animation type (overrides configuration)
jellytools generate --animation-type spiral

# Customize output
jellytools generate --animation-type waterfall --output-dir my_animations

# Skip steps
jellytools generate --skip-hi-res --skip-download

# Skip thumbnail generation
jellytools generate --skip-thumbnails

# Skip low-resolution video generation
jellytools generate --skip-low-res
```

### Sync Collections and Artwork from Plex to Jellyfin

```bash
# Sync all collections and their artwork from Plex to Jellyfin
jellytools sync

# Only clean existing collections in Jellyfin
jellytools sync --clean-only
```

### Command-line Options

```
General Options:
  -c, --config TEXT               Path to configuration file
  -v, --verbose                   Enable verbose output
  --help                          Show this message and exit

Generate Command Options:
  -a, --animation-type [grid|waterfall|mosaic|spiral]
                                  Animation type to use (overrides config)
  --skip-hi-res                   Skip generating high-resolution MP4
  --skip-low-res                  Skip generating 480p low-resolution MP4
  --skip-download                 Skip downloading posters from servers
  --skip-thumbnails               Skip generating PNG thumbnails of the last frame
  -o, --output-dir OUTPUT_DIR     Output directory for videos

Sync Command Options:
  --skip-images                   Skip syncing images (faster)
  --clean-only                    Only clean existing collections without creating new ones
```

## Animation Types

- **grid**: Displays posters in a moving grid pattern (original animation)
- **waterfall**: Posters cascade from the top of the screen into a structured grid
- **mosaic**: Creates a mosaic pattern that zooms and reveals
- **spiral**: Posters begin in a horizontal line, form a spiral, then transition to a grid

## License

This project is licensed under the MIT License - see the LICENSE file for details.
