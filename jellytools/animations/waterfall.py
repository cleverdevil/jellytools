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
            
        # Account for the final scale (1.75x) for grid calculations
        final_scale = 1.75
        scaled_width = max_poster_width * final_scale
        scaled_height = max_poster_height * final_scale
        
        # Add significant spacing between grid cells to prevent overlap
        cell_spacing = 30
        cell_width = scaled_width + cell_spacing
        cell_height = scaled_height + cell_spacing
        
        # Create a grid that extends beyond screen edges to ensure no gaps
        # We want to cover the entire screen plus some margin
        margin = cell_width  # Add one cell width as margin on each side
        
        # Calculate how many columns and rows we need to cover the entire screen plus margins
        grid_columns = math.ceil((WIDTH + 2 * margin) / cell_width) + 2  # Add extra columns for coverage
        grid_rows = math.ceil((HEIGHT + 2 * margin) / cell_height) + 2   # Add extra rows for coverage
        
        # Calculate the total grid dimensions
        grid_width = grid_columns * cell_width
        grid_height = grid_rows * cell_height
        
        # Position the grid so it's centered but extends beyond all screen edges
        grid_start_x = (WIDTH - grid_width) / 2
        grid_start_y = (HEIGHT - grid_height) / 2
        
        # Use as many posters as will fit in the grid, repeating if necessary
        total_cells = grid_rows * grid_columns
        
        # Ensure we have enough posters by repeating the posters list if needed
        available_posters = self.posters * (math.ceil(total_cells / max(1, len(self.posters))))
        max_posters = min(total_cells, len(available_posters))
        
        logger.info(f"Creating a waterfall grid with {grid_rows}x{grid_columns} = {total_cells} cells")
        logger.info(f"Using {max_posters} posters (repeating if needed)")
        
        # Populate the grid with posters
        for i in range(max_posters):
            poster = available_posters[i]
            
            # Calculate grid position
            grid_col = i % grid_columns
            grid_row = i // grid_columns
            
            # Calculate the center of the grid cell
            cell_center_x = grid_start_x + (grid_col * cell_width) + (cell_width / 2)
            cell_center_y = grid_start_y + (grid_row * cell_height) + (cell_height / 2)
            
            # Final x position (centered in grid cell)
            final_x = cell_center_x
            
            # Final y position (centered in grid cell)
            final_y = cell_center_y
            
            # Starting position - above the screen with more variation for staggered effect
            # Different starting positions based on grid position for a cascading effect
            horizontal_variation = random.uniform(-100, 100)  # Larger horizontal variation
            
            # More staggered heights based on grid position for timing variety
            vertical_offset = HEIGHT * 2.0 * (grid_row / max(1, grid_rows))
            
            start_x = final_x + horizontal_variation
            start_y = -poster.get_height() - random.uniform(100, 500) - vertical_offset
            
            # Add randomness to falling parameters with more variation
            # More complex delay calculation based on grid position for wave-like effect
            col_factor = 0.02 + 0.01 * random.random()  # 0.02-0.03 delay per column
            row_factor = 0.08 + 0.04 * random.random()  # 0.08-0.12 delay per row
            random_delay = random.uniform(0, 0.5)       # Additional random delay
            
            # Calculate delay - adds wave-like pattern to the falling posters
            delay = (grid_col * col_factor) + (grid_row * row_factor) + random_delay
            
            # More dramatic rotation
            rotation = random.uniform(-25, 25)  # Initial rotation (-25 to 25 degrees)
            rotation_speed = random.uniform(-5, 5)  # How fast it spins while falling
            
            # Scale factor for posters - start at normal size, grow to 1.75x
            self.poster_data.append({
                'poster': poster,
                'start_x': start_x,
                'start_y': start_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x,  # Initialize current position
                'current_y': start_y,  # Initialize current position
                'delay': delay,
                'rotation': rotation,  # Initial rotation
                'final_rotation': 0,   # Target rotation when landed
                'current_rotation': rotation,  # Current rotation (will be animated)
                'rotation_speed': rotation_speed,
                'opacity': 255,
                'has_landed': False,
                'fall_duration': random.uniform(1.8, 3.5),  # More varied falling times
                'start_scale': random.uniform(0.9, 1.1),    # Slight variation in starting size
                'final_scale': random.uniform(1.7, 1.8),    # Slight variation in final size
                'current_scale': random.uniform(0.9, 1.1)   # Current scale
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
                    # Poster has landed, animate rotation to 0 and scale up
                # Duration for the landing animation
                landing_duration = 0.5  # half a second
                landing_time = poster_time - data['fall_duration']
                
                # Calculate landing animation progress (0 to 1)
                landing_progress = min(1.0, landing_time / landing_duration)
                landing_eased = self.ease_out_cubic(landing_progress)
                
                # Smoothly rotate to 0 degrees
                data['current_rotation'] = data['rotation'] + (data['final_rotation'] - data['rotation']) * landing_eased
                
                # Scale up smoothly
                data['current_scale'] = data['start_scale'] + (data['final_scale'] - data['start_scale']) * landing_eased
                
                # Apply fade effect if needed
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
                data['current_rotation'] = data['rotation']  # Update current rotation while falling
                
                # If we've reached the end of the fall, mark as landed
                if fall_progress >= 1.0:
                    data['has_landed'] = True
                    # Don't immediately snap rotation to 0, it will be animated in the landed state
    
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
            
            # Scale the poster
            if data['current_scale'] != 1.0:
                original_size = working_poster.get_size()
                new_width = int(original_size[0] * data['current_scale'])
                new_height = int(original_size[1] * data['current_scale'])
                working_poster = pygame.transform.smoothscale(working_poster, (new_width, new_height))
            
            # Rotate if needed
            if data['current_rotation'] != 0:
                working_poster = pygame.transform.rotate(working_poster, data['current_rotation'])
            
            # Calculate position (centered on original width/height)
            rect = working_poster.get_rect()
            rect.centerx = data['current_x']
            rect.centery = data['current_y']
            
            # Draw to screen
            surface.blit(working_poster, rect)
