"""
Waterfall animation for the library card generator.
Posters cascade from the top of the screen into a structured grid.
"""
import math
import pygame
import random
import logging
from typing import List, Dict

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterWaterfallAnimation(BaseAnimation):
    """An animation where posters fall from the top of the screen in a cascade and form a grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize waterfall animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Set animation constants
        self.FALLING_DURATION = 4.0  # Duration of falling animation
        self.FADE_START = 4.0  # When the fade effect starts
        self.TEXT_START_TIME = 4.5  # When to show text
        
        # Initialize poster positions
        self.init_poster_positions()
    
    def init_poster_positions(self):
        """Initialize the starting positions and parameters for each poster"""
        self.poster_data = []
        
        # Get the maximum dimensions of posters to create uniform grid cells
        if self.posters:
            max_poster_width = max(p.get_width() for p in self.posters)
            max_poster_height = max(p.get_height() for p in self.posters)
        else:
            max_poster_width = 100
            max_poster_height = 150
        
        # Add some spacing between grid cells
        cell_spacing = 10
        cell_width = max_poster_width + cell_spacing
        cell_height = max_poster_height + cell_spacing
        
        # Calculate how many posters we can fit in a grid
        grid_columns = math.floor(WIDTH / cell_width)
        grid_rows = math.floor(HEIGHT / cell_height)
        
        # We want our grid to be centered, so calculate the starting position
        grid_width = grid_columns * cell_width
        grid_height = grid_rows * cell_height
        grid_start_x = (WIDTH - grid_width) / 2 + cell_spacing / 2
        grid_start_y = (HEIGHT - grid_height) / 2 + cell_spacing / 2
        
        # Limit the number of posters to what fits in the grid
        max_posters = min(grid_rows * grid_columns, len(self.posters))
        
        # Populate the grid with posters
        for i in range(max_posters):
            poster = self.posters[i % len(self.posters)]
            
            # Calculate grid position
            grid_col = i % grid_columns
            grid_row = i // grid_columns
            
            # Final x position (centered in grid cell)
            final_x = grid_start_x + (grid_col * cell_width) + (cell_width - poster.get_width()) / 2
            
            # Final y position (centered in grid cell)
            final_y = grid_start_y + (grid_row * cell_height) + (cell_height - poster.get_height()) / 2
            
            # Starting position - above the screen, with some horizontal variation
            start_x = final_x + random.uniform(-50, 50)  # Small horizontal offset
            start_y = -poster.get_height() - random.uniform(0, HEIGHT * 1.5)  # Staggered starting heights
            
            # Add some randomness to falling parameters
            delay = grid_col * 0.03 + grid_row * 0.1  # Delay based on grid position
            rotation = random.uniform(-15, 15)  # Initial rotation
            rotation_speed = random.uniform(-3, 3)  # How fast it spins while falling
            
            self.poster_data.append({
                'poster': poster,
                'start_x': start_x,
                'start_y': start_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x,  # Initialize current position
                'current_y': start_y,  # Initialize current position
                'delay': delay,
                'rotation': rotation,
                'rotation_speed': rotation_speed,
                'opacity': 255,
                'has_landed': False,
                'fall_duration': random.uniform(2.0, 3.0)  # Randomized falling time
            })
    
    def update(self, elapsed_time: float):
        """
        Update positions of all posters based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        # For each poster, update its position
        for data in self.poster_data:
            # Ignore if we haven't reached the start delay
            if elapsed_time < data['delay']:
                continue
                
            # Calculate time since this poster started moving
            poster_time = elapsed_time - data['delay']
            
            # Check if poster has landed
            if data['has_landed']:
                # Poster has landed, just apply fade effect if needed
                if elapsed_time > self.FADE_START:
                    fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                    # Fade to 20% opacity
                    data['opacity'] = 255 - (255 - 51) * fade_progress
            else:
                # Poster is still falling
                fall_progress = min(1.0, poster_time / data['fall_duration'])
                
                # Use ease-out for natural falling
                eased_progress = self.ease_out_cubic(fall_progress)
                
                # Calculate current position with easing
                data['current_x'] = data['start_x'] + (data['final_x'] - data['start_x']) * eased_progress
                data['current_y'] = data['start_y'] + (data['final_y'] - data['start_y']) * eased_progress
                
                # Update rotation - spins more at beginning, slows at end
                data['rotation'] += data['rotation_speed'] * (1 - eased_progress)
                
                # If we've reached the end of the fall, mark as landed
                if fall_progress >= 1.0:
                    data['has_landed'] = True
                    data['rotation'] = 0  # Set rotation to 0 when landed for a clean grid
    
    def draw(self, surface: pygame.Surface):
        """
        Draw all posters to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        surface.fill((0, 0, 0))  # Black background
        
        # Sort posters by y position and landed status for proper layering
        # This ensures posters that are higher up or still falling render behind those that have landed
        sorted_posters = sorted(self.poster_data, key=lambda x: (x.get('has_landed', False), x.get('current_y', -1000)))
        
        for data in sorted_posters:
            # Get the poster
            poster = data['poster']
            
            # Create a copy for rotation and alpha
            working_poster = poster.copy()
            
            # Set opacity
            if data['opacity'] < 255:
                working_poster.set_alpha(int(data['opacity']))
            
            # Rotate if needed
            if data['rotation'] != 0:
                working_poster = pygame.transform.rotate(working_poster, data['rotation'])
            
            # Calculate position (centered on original width/height)
            rect = working_poster.get_rect()
            rect.centerx = data['current_x']
            rect.centery = data['current_y']
            
            # Draw to screen
            surface.blit(working_poster, rect)
