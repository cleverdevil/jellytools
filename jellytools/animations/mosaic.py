"""
Mosaic animation for the library card generator.
Creates a mosaic pattern that zooms and reveals.
"""
import math
import pygame
import random
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterMosaicAnimation(BaseAnimation):
    """Animation that arranges posters in a mosaic pattern that zooms and reveals"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize mosaic animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation constants
        self.ZOOM_DURATION = 4.0
        self.FADE_START = 4.0
        self.TEXT_START_TIME = 4.5
        
        # Create a mosaic arrangement
        self.setup_mosaic()
    
    def setup_mosaic(self):
        """Create a mosaic arrangement of posters"""
        # Start with an empty list
        self.mosaic_tiles = []
        
        # Determine a reasonable size for the mosaic tiles
        # Use a size that will fit approximately 30-40 posters across the width
        target_width = WIDTH / 35
        
        # Calculate scale factor to resize posters
        if self.posters:
            avg_width = sum(p.get_width() for p in self.posters) / len(self.posters)
            scale_factor = target_width / avg_width
        else:
            scale_factor = 0.2
        
        # Scale all posters to this approximate width
        scaled_posters = []
        for poster in self.posters:
            new_width = int(poster.get_width() * scale_factor)
            new_height = int(poster.get_height() * scale_factor)
            try:
                scaled_poster = pygame.transform.smoothscale(poster, (new_width, new_height))
                scaled_posters.append(scaled_poster)
            except pygame.error:
                continue  # Skip on scaling error
        
        if not scaled_posters:
            return
            
        # Get dimensions for the mosaic grid
        tile_width = scaled_posters[0].get_width()
        tile_height = scaled_posters[0].get_height()
        
        # Calculate how many tiles we need in each dimension
        # Make it larger than the screen to allow for zooming effects
        grid_width = math.ceil(WIDTH * 1.5 / tile_width)
        grid_height = math.ceil(HEIGHT * 1.5 / tile_height)
        
        # Create a centered version of the grid
        startx = (WIDTH - (grid_width * tile_width)) / 2
        starty = (HEIGHT - (grid_height * tile_height)) / 2
        
        # Create the mosaic tiles
        for y in range(grid_height):
            for x in range(grid_width):
                # Choose a poster randomly with preference for less used ones
                poster_idx = random.randint(0, len(scaled_posters) - 1)
                poster = scaled_posters[poster_idx]
                
                # Create a unique delay based on distance from center
                center_x = grid_width / 2
                center_y = grid_height / 2
                distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                # Linear delay based on distance from center
                delay = min(0.8, distance * 0.05)  
                
                self.mosaic_tiles.append({
                    'poster': poster,
                    'x': startx + (x * tile_width),
                    'y': starty + (y * tile_height),
                    'opacity': 0,  # Start invisible
                    'delay': delay,
                    'shown': False
                })
    
    def update(self, elapsed_time: float):
        """
        Update mosaic animation state.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        # Zoom factor that starts at 2.0 (zoomed in) and gradually zooms out to 1.0
        if elapsed_time < self.ZOOM_DURATION:
            zoom_progress = elapsed_time / self.ZOOM_DURATION
            eased_progress = self.ease_out_cubic(zoom_progress)
            self.zoom = 2.0 - eased_progress
        else:
            self.zoom = 1.0
            
        # Calculate center position for zoom
        self.center_x = WIDTH / 2
        self.center_y = HEIGHT / 2
        
        # Update each tile
        for tile in self.mosaic_tiles:
            # Determine if this tile should be visible yet
            if elapsed_time > tile['delay'] and not tile['shown']:
                tile['shown'] = True
                # Fade in quickly
                fade_duration = 0.3
                tile['opacity'] = min(255, (elapsed_time - tile['delay']) * (255 / fade_duration))
            elif tile['shown']:
                # If we're past the fade start time, start fading to 20% opacity
                if elapsed_time > self.FADE_START:
                    fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                    tile['opacity'] = 255 - (255 - 51) * fade_progress
                else:
                    tile['opacity'] = 255  # Full opacity once shown
    
    def draw(self, surface: pygame.Surface):
        """
        Draw the mosaic tiles to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        surface.fill((0, 0, 0))  # Black background
        
        # Define zoom transform
        zoom_origin_x = self.center_x
        zoom_origin_y = self.center_y
        
        # Draw each tile with zoom transform applied
        for tile in self.mosaic_tiles:
            if tile['opacity'] <= 0:
                continue  # Skip if not visible
                
            poster = tile['poster']
            
            # Apply zoom transform
            # Calculate position relative to zoom origin
            rel_x = tile['x'] - zoom_origin_x
            rel_y = tile['y'] - zoom_origin_y
            
            # Apply zoom factor
            zoomed_x = zoom_origin_x + (rel_x * self.zoom)
            zoomed_y = zoom_origin_y + (rel_y * self.zoom)
            
            # Create a copy for opacity
            working_poster = poster.copy()
            if tile['opacity'] < 255:
                working_poster.set_alpha(int(tile['opacity']))
                
            # Draw to screen
            surface.blit(working_poster, (zoomed_x, zoomed_y))
