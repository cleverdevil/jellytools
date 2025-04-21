"""
Utility functions for the library card generator.
"""

import os
import sys
import logging
import pathlib
import pygame
import subprocess
from typing import List, Dict, Any

from jellytools.animations.base import WIDTH, HEIGHT
from jellytools.core.config import get_config

logger = logging.getLogger(__name__)


class Utils:
    @staticmethod
    def check_dependencies() -> bool:
        """
        Check if required command-line tools are installed.

        Returns:
            bool: True if all dependencies are installed, False otherwise
        """
        dependencies_ok = True

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("FFmpeg is installed.")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error(
                "ERROR: FFmpeg is not installed or not in PATH. Please install FFmpeg."
            )
            dependencies_ok = False

        return dependencies_ok
        

    # Define standard poster dimensions as constants
    POSTER_HEIGHT = 210  # Reduced from 280 for memory efficiency
    MIN_POSTER_COUNT = 300  # Minimum number of posters required for animations

    @staticmethod
    def load_posters(library_name: str) -> List[pygame.Surface]:
        """
        Load images from the posters directory for a specific library.
        Uses memory-efficient approach to handle large libraries.

        Args:
            library_name (str): Name of the library to load posters for

        Returns:
            List[pygame.Surface]: List of loaded poster images
        """
        # Initialize pygame if not already initialized
        if not pygame.get_init():
            pygame.init()

        # Make sure we have a video mode set before loading images
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((WIDTH, HEIGHT))

        config = get_config()

        # Determine path to posters directory for this library
        posters_dir = pathlib.Path(config.POSTER_DIRECTORY) / library_name
        if not posters_dir.exists():
            logger.error(f"Error: posters directory {posters_dir} not found.")
            pygame.quit()
            sys.exit(1)

        logger.info(f"Loading poster images from {posters_dir}...")
        
        # First collect all valid poster files
        poster_files = [
            filename for filename in os.listdir(posters_dir)
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
        ]
        
        if not poster_files:
            logger.error(f"Error: No valid poster images found in '{posters_dir}' directory.")
            pygame.quit()
            sys.exit(1)

        # Process available poster files
        posters = []
        for filename in poster_files:
            try:
                img_path = posters_dir / filename
                img = pygame.image.load(img_path).convert_alpha()

                # Scale images to maintain aspect ratio - adjusted for 2.5K resolution
                aspect_ratio = img.get_width() / img.get_height()
                new_width = int(Utils.POSTER_HEIGHT * aspect_ratio)

                # Use smoothscale for better quality
                img = pygame.transform.smoothscale(img, (new_width, Utils.POSTER_HEIGHT))
                posters.append(img)
            except pygame.error as e:
                logger.error(f"Error loading image {filename}: {e}")

        if not posters:
            logger.error(f"Error: Failed to load any valid poster images.")
            pygame.quit()
            sys.exit(1)
            
        # Create an index generator that cycles through the available posters
        # This avoids duplicating the actual poster data in memory
        def poster_cycle_generator(posters, min_count):
            """Generate poster indices, cycling through available posters."""
            original_count = len(posters)
            idx = 0
            while idx < min_count:
                yield idx % original_count
                idx += 1
                
        # Only if we have fewer than MIN_POSTER_COUNT posters, create an index list
        # that cycles through the available posters to reach the minimum
        if len(posters) < Utils.MIN_POSTER_COUNT:
            logger.info(f"Using {len(posters)} unique posters with recycling to fill animation")
            # Create a list of poster indices that cycles through available posters
            poster_indices = list(poster_cycle_generator(posters, Utils.MIN_POSTER_COUNT))
            
            # Create a reference list that points to existing posters
            posters = [posters[i] for i in poster_indices]
        
        logger.info(f"Successfully loaded {len(posters)} poster images.")
        return posters




