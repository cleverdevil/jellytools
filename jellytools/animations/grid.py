"""
Grid animation for the library card generator.
This is the original animation from the initial version.
"""
import math
import pygame
import logging
from typing import List

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterGridAnimation(BaseAnimation):
    """The original poster grid animation"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize grid animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Create a grid larger than the screen
        if not posters:
            self.poster_width = 100  # Default if no posters
            self.poster_height = 150
        else:
            self.poster_width = max(max(p.get_width() for p in posters), 1)
            self.poster_height = max(max(p.get_height() for p in posters), 1)
        
        # Create a grid with many columns and rows that ensures full screen coverage
        target_cols = 25  # More columns for better coverage
        
        # Calculate rows based on columns and total posters
        self.cols = target_cols
        self.rows = math.ceil(len(posters) / self.cols)
        
        # Ensure the grid is significantly larger than the screen
        multiplier = 2.5  # Make grid at least 2.5x screen size in both dimensions
        
        # Calculate minimum grid dimensions needed
        min_grid_width = WIDTH * multiplier
        min_grid_height = HEIGHT * multiplier
        
        # Adjust grid size if needed
        while self.cols * self.poster_width < min_grid_width:
            self.cols += 5
            self.rows = math.ceil(len(posters) / self.cols)
        
        while self.rows * self.poster_height < min_grid_height:
            self.rows += 5
        
        # Final grid dimensions
        self.grid_width = self.cols * self.poster_width
        self.grid_height = self.rows * self.poster_height
        
        # Animation properties
        self.x = (WIDTH - self.grid_width) / 2
        self.y = (HEIGHT - self.grid_height) / 2
        self.angle = 0
        self.scale = 1.2  # Start slightly zoomed in to avoid edges
        self.opacity = 255
        
        # Final position (centered)
        self.final_x = (WIDTH - self.grid_width) / 2
        self.final_y = (HEIGHT - self.grid_height) / 2
        
        # Animation constants
        self.TRANSITION_MID_TIME = 3.0
        self.FINAL_PHASE_START = 3.0
        self.TEXT_START_TIME = 4.5
    
    def update(self, elapsed_time: float):
        """
        Update the grid position and properties based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        self.time = elapsed_time
        
        # Unified animation flow with three overlapping phases - scaled to 6 seconds
        # Phase 1: Initial animation (0-3s) - starts zoomed out, rotates, gradually zooms in
        # Phase 2: Rotation normalization (1.5-4.5s) - smoothly returns to 0-degree angle
        # Phase 3: Final centering and dimming (3-6s) - centers grid, applies dimming
        
        # Calculate phase progress values with smoother transitions
        phase1_progress = min(1.0, elapsed_time / 3.0)  # 0-3 seconds
        phase1_eased = self.ease_in_out_quad(phase1_progress)
        
        # Calculate phase progress with smooth transitions - compressed timeline
        phase2_progress = self.smooth_transition(elapsed_time, 1.5, 4.5)  # 1.5-4.5 seconds
        phase3_progress = self.smooth_transition(elapsed_time, 3.0, 6.0)  # 3-6 seconds
        
        # Calculate movement factor - gradual reduction with no sudden changes
        movement_factor = 1.0 - self.smooth_transition(elapsed_time, 1.5, 4.5) * 0.9
        
        # Increase frequency slightly to maintain visual interest in shorter time
        base_amplitude_x = WIDTH * 0.2
        base_amplitude_y = HEIGHT * 0.2
        base_frequency_x = 0.13  # Faster for shorter animation
        base_frequency_y = 0.11
        
        # Apply movement factor
        amplitude_x = base_amplitude_x * movement_factor
        amplitude_y = base_amplitude_y * movement_factor
        
        # Figure-eight pattern with smoother motion
        base_x = (
            WIDTH / 2
            - self.grid_width / 2
            + amplitude_x * math.sin(elapsed_time * base_frequency_x)
        )
        base_y = (
            HEIGHT / 2
            - self.grid_height / 2
            + amplitude_y * math.sin(elapsed_time * base_frequency_y * 2)
        )
        
        # Add gentler circular motion
        circle_amp = WIDTH * 0.08 * movement_factor
        base_x += circle_amp * math.cos(elapsed_time * 0.18)  # Adjusted for faster animation
        base_y += circle_amp * math.sin(elapsed_time * 0.15)
        
        # Target position (center of screen)
        target_x = WIDTH / 2 - self.grid_width / 2
        target_y = HEIGHT / 2 - self.grid_height / 2
        
        # Apply centering with smooth transition
        self.x = base_x * (1 - phase3_progress) + target_x * phase3_progress
        self.y = base_y * (1 - phase3_progress) + target_y * phase3_progress
        
        # Rotation - smoother transition with reduced max angle
        max_angle = 12.0
        
        # Calculate base angle with smoother oscillation - adjusted frequency
        base_angle = max_angle * math.sin(elapsed_time * 0.3)  # Faster oscillation for shorter time
        
        # Apply rotation reduction with smooth transition
        self.angle = base_angle * (1 - phase2_progress)
        
        # Zoom effect - smoothly interpolate between different zoom levels
        zoom_start = 1.0  # Start zoomed out
        zoom_mid = 2.0  # Mid-animation zoom
        zoom_end = 3.5  # Final zoom
        
        # Smoother zoom transition
        if elapsed_time < 3.0:
            # Phase 1: Zoom from out to in
            self.scale = zoom_start + (zoom_mid - zoom_start) * phase1_eased
        else:
            # Phase 3: Continue zoom to final level with smooth interpolation
            self.scale = zoom_mid + (zoom_end - zoom_mid) * phase3_progress
        
        # Add very subtle breathing effect - reduced amplitude for more stability
        zoom_breath = 0.02 * math.sin(elapsed_time * 0.4) * (1 - phase3_progress)
        self.scale += zoom_breath
        
        # Opacity - maintain full opacity until phase 3
        self.opacity = 255 - (255 - 51) * phase3_progress  # Fade to 20% opacity
    
    def draw(self, surface: pygame.Surface):
        """
        Draw the grid of posters to the given surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Create a surface for the entire grid
        grid_width = int(self.grid_width)
        grid_height = int(self.grid_height)
        
        if grid_width <= 0 or grid_height <= 0:
            return  # Skip rendering if dimensions are invalid
        
        grid_surface = pygame.Surface((grid_width, grid_height), pygame.SRCALPHA)
        
        # Draw posters onto the grid
        total_cells = self.rows * self.cols
        
        for cell_idx in range(total_cells):
            # Get poster index, cycling through available posters if we need more
            poster_idx = cell_idx % len(self.posters)
            poster = self.posters[poster_idx]
            
            # Calculate grid position
            row = cell_idx // self.cols
            col = cell_idx % self.cols
            
            x = col * self.poster_width
            y = row * self.poster_height
            
            # Center each poster in its cell
            x_centered = x + (self.poster_width - poster.get_width()) // 2
            y_centered = y + (self.poster_height - poster.get_height()) // 2
            
            # Draw the poster
            grid_surface.blit(poster, (x_centered, y_centered))
        
        # Scale the grid
        scaled_width = max(1, int(self.grid_width * self.scale))
        scaled_height = max(1, int(self.grid_height * self.scale))
        
        try:
            scaled_grid = pygame.transform.smoothscale(
                grid_surface, (scaled_width, scaled_height)
            )
            
            # Simple rotation - no fancy effects for better performance
            if self.angle != 0:
                rotated_grid = pygame.transform.rotate(scaled_grid, self.angle)
            else:
                rotated_grid = scaled_grid
            
            # Set opacity
            if self.opacity < 255:
                # Use a simpler alpha setting method
                rotated_grid.set_alpha(int(self.opacity))
            
            # Get the rotated dimensions and position
            rot_rect = rotated_grid.get_rect()
            rot_rect.center = (
                WIDTH // 2 + (self.x + self.grid_width // 2 - WIDTH // 2) * self.scale,
                HEIGHT // 2
                + (self.y + self.grid_height // 2 - HEIGHT // 2) * self.scale,
            )
            
            # Draw the rotated and scaled grid
            surface.blit(rotated_grid, rot_rect)
            
        except (ValueError, pygame.error) as e:
            logger.error(f"Error rendering grid: {e}")
            return
            
    def render_text(self, elapsed_time: float, surface: pygame.Surface):
        """
        Override the base method to use animation-specific timing.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
            surface (pygame.Surface): Surface to draw on
        """
        # Text zoom animation
        if elapsed_time > self.TEXT_START_TIME:
            from jellytools.core.config import get_config
            config = get_config()
            text = self.library_name.upper() if config.CAPITALIZE_TEXT else self.library_name
            
            # Calculate zoom progress
            text_time = elapsed_time - self.TEXT_START_TIME
            text_duration = 1.5  # Complete in 1.5 seconds
            text_progress = min(1.0, text_time / text_duration)
            
            # Use a combination of easing functions for smooth zoom
            if text_progress < 0.5:
                # Ease-in quad for first half
                text_eased = 2 * text_progress * text_progress
            else:
                # Ease-out quad for second half
                text_eased = 1 - math.pow(-2 * text_progress + 2, 2) / 2
            
            # Calculate the final text size that fills 80% of the screen
            text_surface = self.font.render(text, True, (255, 255, 255))
            final_width = text_surface.get_width()
            final_height = text_surface.get_height()
            
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
            
            # Position text in center of screen
            text_x = WIDTH // 2 - text_surface.get_width() // 2
            text_y = HEIGHT // 2 - text_surface.get_height() // 2
            
            # Draw semi-transparent overlay that fades in more quickly
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay_alpha = int(80 * text_eased)
            overlay.fill((0, 0, 0, overlay_alpha))
            surface.blit(overlay, (0, 0))
            
            # Draw the text
            surface.blit(text_surface, (text_x, text_y))
