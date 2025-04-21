# Jellytools

A Python package for enhancing Jellyfin Media Servers.

## Demo

Watch how Jellytools transforms your Jellyfin interface with beautiful animated library cards:

https://github.com/user-attachments/assets/b8130d64-9e72-478f-8c00-27c0aafda385

## Features

- Generate animated library cards from media posters in high-quality MP4 video format
- Multiple animation styles: grid, waterfall, spiral, mosaic, vortex, cascade, explode, kaleidoscope, and shockwave
- Download poster artwork from Jellyfin libraries
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
  - requests
  - click

## Quick Start

1. Create a configuration file by copying the example:

```bash
# Copy the example config
cp config.py.example config.py

# Or initialize a new one
jellytools init
```

2. Edit the `config.py` file with your Jellyfin server details (this file is gitignored for security)

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
# Jellyfin server configuration
JELLYFIN_URL = "http://localhost:8096"
# Authentication options (use either API key or username/password)
JELLYFIN_API_KEY = "your-jellyfin-api-key"
# Alternative authentication
# JELLYFIN_USERNAME = "your-jellyfin-username"
# JELLYFIN_PASSWORD = "your-jellyfin-password"
JELLYFIN_LIBRARIES = ["Movies", "TV Shows", "Collections"]

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

### Download Poster Artwork from Jellyfin

```bash
# Download poster artwork for all configured libraries
jellytools posters fetch

# Clean existing poster artwork before downloading
jellytools posters fetch --clean-first

# Only download artwork for specific libraries
jellytools posters fetch --libraries "Movies,TV Shows"

# Clean and download specific libraries
jellytools posters fetch --clean-first --libraries "Movies,TV Shows"
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
  --skip-existing                 Skip animations that already exist in the output directory
  --libraries                     Comma-separated list of libraries to process
  -o, --output-dir OUTPUT_DIR     Output directory for videos

Generate JavaScript Options:
  -o, --output TEXT               Output file for the JavaScript (default: jellyfin-override.js)
  --replay/--no-replay            Allow videos to replay each time the element is hovered over (default: false)
  --hide-labels/--show-labels     Hide the text labels for library cards (default: true)

Posters Command Options:
  --clean-first                   Remove all existing poster files before downloading
  --libraries                     Comma-separated list of libraries to process
```

## Animation Types

Jellytools provides a variety of animations for your library cards:

### Grid
A structured grid arrangement of posters with subtle movements.

https://github.com/user-attachments/assets/5198c308-1f21-4a88-b382-c0ce3ad4abaa

### Waterfall
Posters cascade from the top of the screen into a structured grid.

https://github.com/user-attachments/assets/e9c32492-ec47-4383-b436-360aae267728

### Spiral
Posters begin in a horizontal line, form a spiral, then transition to a grid.

https://github.com/user-attachments/assets/1f1da585-6e00-4af9-993f-2c8db4ccba09

### Mosaic
Creates a mosaic pattern that zooms and reveals.

https://github.com/user-attachments/assets/814a7e87-f146-43d4-a797-44446e7077ad

### Vortex
Posters swirl in a vortex pattern before arranging into a grid.

https://github.com/user-attachments/assets/6b23c9fb-d2eb-498d-8872-688abe1dfd35

### Cascade
Posters cascade in from the sides in an alternating pattern.

https://github.com/user-attachments/assets/d719bb88-fe16-4ef0-a069-8c7187794643

### Explode
Posters explode outward from the center before organizing into a grid.

https://github.com/user-attachments/assets/dff5be18-c5ab-4825-b473-2e42e19541ea

### Kaleidoscope
A mesmerizing kaleidoscope effect with rotating poster patterns.

https://github.com/user-attachments/assets/d7a1be8b-fb7c-4f00-b1ce-dd58242f9980

### Shockwave
Posters ripple in a shockwave pattern from the center.

https://github.com/user-attachments/assets/2322c281-946f-4715-81ca-7b5dca8c8a31

## Jellyfin Custom JavaScript Plugin

To use the generated JavaScript with Jellyfin, you need to install the Custom JavaScript plugin:

1. Install the [Jellyfin Custom JavaScript Plugin](https://github.com/johnpc/jellyfin-plugin-custom-javascript)
2. Go to your Jellyfin dashboard
3. Navigate to Plugins > Custom JavaScript
4. Paste the contents of the generated JavaScript file
5. Save the settings
6. Refresh your Jellyfin interface

## Credits

This project was developed by [Jonathan LaCour](https://cleverdevil.io).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
