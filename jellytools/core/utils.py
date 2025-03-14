"""
Utility functions for the library card generator.
"""

import os
import sys
import logging
import pathlib
import pygame
import subprocess
from typing import List, Optional

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

    @staticmethod
    def load_posters(library_name: str) -> List[pygame.Surface]:
        """
        Load images from the posters directory for a specific library.

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
        posters = []
        posters_dir = pathlib.Path(config.POSTER_DIRECTORY) / library_name
        if not posters_dir.exists():
            logger.error(f"Error: posters directory {posters_dir} not found.")
            pygame.quit()
            sys.exit(1)

        logger.info(f"Loading poster images from {posters_dir}...")
        poster_files = []
        for filename in os.listdir(posters_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                poster_files.append(filename)

        # Process all available poster files
        for filename in poster_files:
            try:
                img_path = posters_dir / filename
                img = pygame.image.load(img_path).convert_alpha()

                # Scale images to maintain aspect ratio - adjusted for 2.5K resolution
                aspect_ratio = img.get_width() / img.get_height()
                new_height = 210  # Reduced from 280 for memory efficiency
                new_width = int(new_height * aspect_ratio)

                # Use smoothscale for better quality
                img = pygame.transform.smoothscale(img, (new_width, new_height))
                posters.append(img)
            except pygame.error as e:
                logger.error(f"Error loading image {filename}: {e}")

        # Check if we loaded any posters at all
        if not posters:
            logger.error(
                f"Error: No valid poster images found in '{posters_dir}' directory."
            )
            pygame.quit()
            sys.exit(1)

        # Reduce the duplicate count to prevent memory issues
        # If we don't have at least 300 posters, duplicate existing ones to reach that number
        while len(posters) < 300:
            posters.extend(posters[: min(len(posters), 300 - len(posters))])

        logger.info(f"Successfully loaded {len(posters)} poster images.")
        return posters
