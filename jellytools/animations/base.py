"""
Base animation classes and animation manager for the library card generator.
"""

import abc
import logging
import math
import pygame
from typing import List, Dict, Type

# Set default animation parameters
WIDTH, HEIGHT = 2880, 1620  # 2.5K resolution
TOTAL_ANIMATION_TIME = 6.0  # 6 seconds
FPS = 60

logger = logging.getLogger(__name__)


class BaseAnimation(abc.ABC):
    """Base class for all animations"""

    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize the base animation.

        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to use
        """
        self.library_name = library_name
        self.posters = posters
        self.surface = pygame.Surface((WIDTH, HEIGHT))
        self.duration = TOTAL_ANIMATION_TIME

        # Try loading the font
        try:
            from jellytools.core.config import get_config

            config = get_config()
            self.font = pygame.font.Font(config.FONT_PATH, 500)
        except Exception:
            logger.warning("Font file not found. Using default font.")
            self.font = pygame.font.Font(None, 500)

    @abc.abstractmethod
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.

        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        pass

    @abc.abstractmethod
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation state to the given surface.

        Args:
            surface (pygame.Surface): Surface to draw on
        """
        pass

    def render_text(self, elapsed_time: float, surface: pygame.Surface):
        """
        Render library name text with animation.

        Args:
            elapsed_time (float): Time in seconds since the animation started
            surface (pygame.Surface): Surface to draw on
        """
        # Default text implementation - override in subclasses as needed
        TEXT_START_TIME = 4.5
        if elapsed_time > TEXT_START_TIME:
            from jellytools.core.config import get_config

            config = get_config()
            text = (
                self.library_name.upper()
                if config.CAPITALIZE_TEXT
                else self.library_name
            )

            lines = text.split(" ")

            text_time = elapsed_time - TEXT_START_TIME
            text_duration = 1.5  # Complete in 1.5 seconds
            text_progress = min(1.0, text_time / text_duration)

            # Use easing function
            text_eased = self.ease_in_out_quad(text_progress)

            # Draw semi-transparent overlay that fades in
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay_alpha = int(80 * text_eased)
            overlay.fill((0, 0, 0, overlay_alpha))
            surface.blit(overlay, (0, 0))

            # Render text
            for i, line in enumerate(lines):
                text_surface = self.font.render(line, True, (255, 255, 255))

                # Calculate the final text size that fills screen appropriately
                final_width = text_surface.get_width()
                final_height = text_surface.get_height()
                total_height = final_height * len(lines)

                # Apply progressive scaling
                if text_progress < 1.0:
                    # Start very small (1%) and zoom to full size
                    start_scale = 0.01
                    scale_factor = start_scale + (1.0 - start_scale) * text_eased

                    # Apply scale with minimum size constraints
                    scaled_width = max(10, int(final_width * scale_factor))
                    scaled_height = max(10, int(final_height * scale_factor))

                    try:
                        text_surface = pygame.transform.smoothscale(
                            text_surface, (scaled_width, scaled_height)
                        )
                    except (ValueError, pygame.error):
                        pass

                # Position text in middle of screen
                text_x = WIDTH // 2 - text_surface.get_width() // 2

                # Position text based upon the number of lines
                # text_y = HEIGHT // 2 - text_surface.get_height() // 2
                text_y = ((HEIGHT - total_height) // 2) + (i * final_height)

                # Draw the text
                surface.blit(text_surface, (text_x, text_y))

    # Common easing functions
    @staticmethod
    def ease_out_cubic(x: float) -> float:
        """Cubic ease-out function"""
        return 1 - math.pow(1 - x, 3)

    @staticmethod
    def ease_in_out_quad(x: float) -> float:
        """Quadratic ease-in-out function"""
        return 2 * x * x if x < 0.5 else 1 - math.pow(-2 * x + 2, 2) / 2

    @staticmethod
    def smooth_transition(t: float, start: float, end: float) -> float:
        """Sigmoid-like smooth transition function"""
        if t <= start:
            return 0.0
        if t >= end:
            return 1.0
        normalized = (t - start) / (end - start)
        # Use smoothstep function for smoother transitions: 3x^2 - 2x^3
        return normalized * normalized * (3 - 2 * normalized)


class AnimationManager:
    """Manages the creation and rendering of different animation types"""

    def __init__(self):
        """Initialize the animation manager."""
        # Animations will be registered when their modules are imported
        self.animation_types = {}

    def register_animation(self, name: str, animation_class: Type[BaseAnimation]):
        """
        Register an animation type.

        Args:
            name (str): Name of the animation type
            animation_class (Type[BaseAnimation]): Animation class
        """
        self.animation_types[name] = animation_class

    def get_animation_types(self) -> List[str]:
        """
        Return a list of available animation type names.

        Returns:
            List[str]: List of animation type names
        """
        return list(self.animation_types.keys())

    def create_animation(
        self, animation_type: str, library_name: str, posters: List[pygame.Surface]
    ) -> BaseAnimation:
        """
        Create an animation of the specified type.

        Args:
            animation_type (str): Type of animation to create
            library_name (str): Name of the library
            posters (List[pygame.Surface]): List of poster images

        Returns:
            BaseAnimation: Initialized animation object
        """
        if animation_type not in self.animation_types:
            logger.warning(
                f"Animation type '{animation_type}' not found. Using 'grid' as fallback."
            )
            animation_type = "grid"

        animation_class = self.animation_types[animation_type]
        return animation_class(library_name, posters)
