"""
Configuration handling for the jellytools package.
"""

import os
import logging
import importlib.util
from typing import Any, List, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JellytoolsConfig:
    """Configuration data structure for jellytools."""

    # Jellyfin is the primary server
    JELLYFIN_URL: Optional[str] = None
    JELLYFIN_API_KEY: Optional[str] = None
    JELLYFIN_LIBRARIES: List[str] = None

    # Plex is used for syncing posters and collections
    PLEX_URL: Optional[str] = None
    PLEX_TOKEN: Optional[str] = None
    PLEX_LIBRARIES: List[str] = None

    # General configuration
    POSTER_DIRECTORY: str = "posters"
    FONT_PATH: str = None
    CAPITALIZE_TEXT: bool = True

    # Animation configuration (defaults)
    DEFAULT_ANIMATION_TYPE: str = "grid"
    DEFAULT_OUTPUT_DIR: str = "output"

    # Per-library animation configuration
    # This should be a dictionary mapping library names to configuration objects
    # Each library can have the following keys:
    #   - animation_type: The type of animation to use for this library (string)
    #   - animation_types: A list of animation types to generate (list of strings)
    #   - additional parameters can be added later
    LIBRARY_ANIMATIONS: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default lists and dictionaries if None."""
        if self.PLEX_LIBRARIES is None:
            self.PLEX_LIBRARIES = []
        if self.JELLYFIN_LIBRARIES is None:
            self.JELLYFIN_LIBRARIES = []
        if self.LIBRARY_ANIMATIONS is None:
            self.LIBRARY_ANIMATIONS = {}

    def get_animation_config(self, library_name: str) -> Dict[str, Any]:
        """
        Get animation configuration for a specific library.

        Args:
            library_name (str): Name of the library

        Returns:
            Dict[str, Any]: Animation configuration for the library
        """
        # Return the library-specific config if it exists, otherwise an empty dict
        return self.LIBRARY_ANIMATIONS.get(library_name, {})
        
    def get_library_animation_type(self, library_name: str) -> str:
        """
        Get the animation type configured for a specific library.
        
        Args:
            library_name (str): Name of the library
            
        Returns:
            str: Animation type for the library, or the default animation type if not specified
        """
        library_config = self.get_animation_config(library_name)
        return library_config.get("animation_type", self.DEFAULT_ANIMATION_TYPE)
        
    def get_library_animation_types(self, library_name: str) -> List[str]:
        """
        Get the list of animation types configured for a specific library.
        
        Args:
            library_name (str): Name of the library
            
        Returns:
            List[str]: List of animation types for the library. 
                      If not specified, returns a list with just the default animation type.
        """
        library_config = self.get_animation_config(library_name)
        
        # First check for the animation_types list
        animation_types = library_config.get("animation_types")
        if animation_types:
            return animation_types
            
        # Fall back to animation_type if it exists
        animation_type = library_config.get("animation_type")
        if animation_type:
            return [animation_type]
            
        # Use default animation type if nothing is specified
        return [self.DEFAULT_ANIMATION_TYPE]


# Global config instance
_config = None


def load_config(config_path: Optional[str] = None) -> JellytoolsConfig:
    """
    Load configuration from the specified path or search for 'config.py'.

    Args:
        config_path (Optional[str]): Path to the configuration file

    Returns:
        JellytoolsConfig: Configuration object
    """
    global _config

    # Create a default config
    config = JellytoolsConfig()

    # If a config path was specified, try to load it
    if config_path:
        if not os.path.isfile(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            return config

        try:
            # Load the specified config file
            spec = importlib.util.spec_from_file_location("user_config", config_path)
            user_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(user_config)

            # Update config with values from the loaded config
            update_config_from_module(config, user_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
    else:
        # Search for config.py in current directory and parent directories
        current_dir = os.getcwd()
        max_levels = 3  # Limit how far up we'll search

        for _ in range(max_levels):
            potential_config = os.path.join(current_dir, "config.py")
            if os.path.isfile(potential_config):
                try:
                    spec = importlib.util.spec_from_file_location(
                        "user_config", potential_config
                    )
                    user_config = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(user_config)

                    # Update config with values from the loaded config
                    update_config_from_module(config, user_config)
                    logger.info(f"Loaded configuration from {potential_config}")
                    break
                except Exception as e:
                    logger.error(
                        f"Error loading configuration from {potential_config}: {e}"
                    )

            # Move up one directory
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break  # We've reached the root directory
            current_dir = parent_dir

    # Store the config globally
    _config = config
    return config


def update_config_from_module(config: JellytoolsConfig, module: Any) -> None:
    """
    Update configuration object with values from a module.

    Args:
        config (JellytoolsConfig): Configuration object to update
        module (Any): Module containing configuration values
    """
    for key in dir(module):
        # Skip special attributes and functions
        if key.startswith("__") or callable(getattr(module, key)):
            continue

        # Only update if the config has this attribute
        if hasattr(config, key):
            setattr(config, key, getattr(module, key))


def get_config() -> JellytoolsConfig:
    """
    Get the current configuration, loading it if necessary.

    Returns:
        JellytoolsConfig: Configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def create_default_config_file(path: str) -> bool:
    """
    Create a default configuration file at the specified path.

    Args:
        path (str): Path to create the configuration file at

    Returns:
        bool: True if successful, False otherwise
    """
    default_config = """# Jellytools configuration file

# Jellyfin server configuration (primary)
JELLYFIN_URL = "http://localhost:8096"
JELLYFIN_API_KEY = ""
JELLYFIN_LIBRARIES = ["Movies", "TV Shows"]

# Plex server configuration (used for syncing)
PLEX_URL = "http://localhost:32400"
PLEX_TOKEN = ""
PLEX_LIBRARIES = ["Movies", "TV Shows"]

# General configuration
POSTER_DIRECTORY = "posters"
FONT_PATH = "./font.ttf"
CAPITALIZE_TEXT = True

# Animation configuration
DEFAULT_ANIMATION_TYPE = "grid"
DEFAULT_OUTPUT_DIR = "output"

# Per-library animation configuration
# Define custom animation styles for each library
# Example:
LIBRARY_ANIMATIONS = {
    "Movies": {
        "animation_type": "mosaic"  # Single animation type
    },
    "TV Shows": {
        "animation_types": ["waterfall", "spiral"]  # Multiple animation types
    },
    "Music": {
        "animation_types": ["grid", "mosaic", "spiral"]  # Generate all three
    }
}
"""

    try:
        with open(path, "w") as f:
            f.write(default_config)
        logger.info(f"Created default configuration file at {path}")
        return True
    except Exception as e:
        logger.error(f"Error creating default configuration file: {e}")
        return False
