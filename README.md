# Jellytools

A Python package for enhancing Jellyfin Media Servers.

## Features

- Generate animated library cards from media posters in high-quality MP4 video format
- Multiple animation styles: grid, waterfall, spiral, mosaic, vortex, cascade, explode, kaleidoscope, and shockwave
- Synchronize collections and artwork from Plex to Jellyfin
- Generate custom JavaScript for Jellyfin to add video backgrounds to library cards

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/cleverdevil/jellytools.git
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

4. Generate JavaScript for the Jellyfin Custom JavaScript Plugin:

```bash
jellytools generate-js
```

## Configuration

The configuration file (`config.py`) contains the following settings:

```python
# Jellyfin server configuration (primary)
JELLYFIN_URL = "http://localhost:8096"
JELLYFIN_API_KEY = "your-jellyfin-api-key"
JELLYFIN_LIBRARIES = ["Movies", "TV Shows", "Collections"]

# Plex server configuration (used for syncing)
PLEX_URL = "http://localhost:32400"
PLEX_TOKEN = "your-plex-token"
PLEX_LIBRARIES = ["Movies", "TV Shows"]

# General configuration
POSTER_DIRECTORY = "posters"
FONT_PATH = "./assets/font.ttf"
CAPITALIZE_TEXT = True

# Animation configuration
DEFAULT_ANIMATION_TYPE = "grid"
DEFAULT_OUTPUT_DIR = "output"

# All animation types
ALL_ANIMATIONS = [
    "grid",
    "spiral",
    "waterfall",
    "cascade",
    "kaleidoscope",
    "explode",
    "vortex",
    "mosaic",
    "shockwave",
]

# Per-library animation configuration
LIBRARY_ANIMATIONS = {
    "Movies": {"animation_types": ALL_ANIMATIONS},
    "TV Shows": {"animation_types": ALL_ANIMATIONS},
    "Collections": {"animation_types": ALL_ANIMATIONS},
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

### Generate JavaScript for Jellyfin

Generate JavaScript for the Jellyfin Custom JavaScript Plugin that adds hover-triggered videos to library cards:

```bash
# Basic usage
jellytools generate-js

# Allow videos to replay each time the element is hovered over
jellytools generate-js --replay

# Keep text labels visible instead of hiding them
jellytools generate-js --show-labels

# Specify output file
jellytools generate-js --output my-override.js
```

The JavaScript will add hidden videos to Jellyfin library cards while maintaining their original appearance. The videos will play when a user hovers over a library card.

### Sync Collections and Artwork from Plex to Jellyfin

```bash
# Sync all collections and their artwork from Plex to Jellyfin
jellytools sync

# Only clean existing collections in Jellyfin
jellytools sync --clean-only

# Skip syncing images (faster)
jellytools sync --skip-images
```

### Command-line Options

```
General Options:
  -c, --config TEXT               Path to configuration file
  -v, --verbose                   Enable verbose output
  --help                          Show this message and exit

Generate Command Options:
  -a, --animation-type [grid|waterfall|spiral|mosaic|vortex|cascade|explode|kaleidoscope|shockwave]
                                  Animation type to use (overrides config)
  --skip-hi-res                   Skip generating high-resolution MP4
  --skip-low-res                  Skip generating 480p low-resolution MP4
  --skip-download                 Skip downloading posters from servers
  --skip-thumbnails               Skip generating PNG thumbnails of the last frame
  -o, --output-dir OUTPUT_DIR     Output directory for videos

Generate JavaScript Options:
  -o, --output TEXT               Output file for the JavaScript (default: jellyfin-override.js)
  --replay/--no-replay            Allow videos to replay each time the element is hovered over (default: false)
  --hide-labels/--show-labels     Hide the text labels for library cards (default: true)

Sync Command Options:
  --skip-images                   Skip syncing images (faster)
  --clean-only                    Only clean existing collections without creating new ones
```

## Animation Types

Jellytools provides a variety of animations for your library cards:

### Grid
A structured grid arrangement of posters with subtle movements.

https://github.com/cleverdevil/jellytools/raw/main/examples/grid.mp4

### Waterfall
Posters cascade from the top of the screen into a structured grid.

https://github.com/cleverdevil/jellytools/raw/main/examples/waterfall.mp4

### Spiral
Posters begin in a horizontal line, form a spiral, then transition to a grid.

https://github.com/cleverdevil/jellytools/raw/main/examples/spiral.mp4

### Mosaic
Creates a mosaic pattern that zooms and reveals.

https://github.com/cleverdevil/jellytools/raw/main/examples/mosaic.mp4

### Vortex
Posters swirl in a vortex pattern before arranging into a grid.

https://github.com/cleverdevil/jellytools/raw/main/examples/vortex.mp4

### Cascade
Posters cascade in from the sides in an alternating pattern.

https://github.com/cleverdevil/jellytools/raw/main/examples/cascade.mp4

### Explode
Posters explode outward from the center before organizing into a grid.

https://github.com/cleverdevil/jellytools/raw/main/examples/explode.mp4

### Kaleidoscope
A mesmerizing kaleidoscope effect with rotating poster patterns.

https://github.com/cleverdevil/jellytools/raw/main/examples/kaleidoscope.mp4

### Shockwave
Posters ripple in a shockwave pattern from the center.

https://github.com/cleverdevil/jellytools/raw/main/examples/shockwave.mp4

## Jellyfin Custom JavaScript Plugin

To use the generated JavaScript with Jellyfin, you need to install the Custom JavaScript plugin:

1. Install the [Jellyfin Custom JavaScript Plugin](https://github.com/johnpc/jellyfin-plugin-custom-javascript)
2. Go to your Jellyfin dashboard
3. Navigate to Plugins > Custom JavaScript
4. Paste the contents of the generated JavaScript file
5. Save the settings
6. Refresh your Jellyfin interface

## Credits

This project was developed by [Jonathan LaCour](https://cleverdevil.io) in collaboration with [Claude Code](https://claude.ai/code).

## License

This project is licensed under the MIT License - see the LICENSE file for details.