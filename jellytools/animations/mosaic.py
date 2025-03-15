"""
Mosaic animation for the library card generator.
Posters zoom in from random positions to form a dynamic mosaic pattern.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterMosaicAnimation(BaseAnimation):
    """Animation that forms a mosaic pattern with random starting positions and zoom effects"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize mosaic animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.MOSAIC_FORMATION_TIME = 3.5  # Time to form mosaic (0-3.5s)
        self.STABLE_MOSAIC_TIME = 1.0     # Time to keep mosaic stable (3.5-4.5s)
        self.FADE_START = 4.5             # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5        # When to show text
        
        # Calculate grid parameters
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized mosaic animation with {len(self.posters_data)} posters")
    
    def _calculate_grid_params(self, posters: List[pygame.Surface]) -> Dict[str, Any]:
        """
        Calculate mosaic grid parameters.
        
        Args:
            posters (List[pygame.Surface]): List of poster images
            
        Returns:
            Dict[str, Any]: Grid parameters
        """
        # Get average poster dimensions
        if not posters:
            poster_width = 100
            poster_height = 150
        else:
            poster_width = max(max(p.get_width() for p in posters), 1)
            poster_height = max(max(p.get_height() for p in posters), 1)
        
        # Scale factor for mosaic (slightly larger than other animations)
        scale_factor = 1.8
        
        # Calculate cell dimensions with spacing
        spacing = 15  # Tighter spacing for mosaic look
        cell_width = int(poster_width * scale_factor) + spacing
        cell_height = int(poster_height * scale_factor) + spacing
        
        # Create a mosaic grid - more columns than rows for widescreen look
        aspect_ratio = WIDTH / HEIGHT
        base_cols = 12  # Base number of columns
        
        cols = base_cols
        rows = int(base_cols / aspect_ratio) + 3  # Add extra rows to ensure coverage
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Mosaic grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
        return {
            'poster_width': poster_width,
            'poster_height': poster_height,
            'cell_width': cell_width,
            'cell_height': cell_height,
            'cols': cols,
            'rows': rows,
            'grid_width': grid_width,
            'grid_height': grid_height,
            'grid_origin_x': grid_origin_x,
            'grid_origin_y': grid_origin_y,
            'scale_factor': scale_factor
        }
    
    def _initialize_posters(self, posters: List[pygame.Surface]) -> List[Dict[str, Any]]:
        """
        Initialize poster data for the animation.
        
        Args:
            posters (List[pygame.Surface]): List of poster images
            
        Returns:
            List[Dict[str, Any]]: List of poster data dictionaries
        """
        posters_data = []
        
        if not posters:
            return posters_data
        
        # Calculate total cells in the grid
        total_cells = self.grid_params['cols'] * self.grid_params['rows']
        
        # Ensure we have enough posters to fill all cells
        available_posters = posters * (math.ceil(total_cells / max(1, len(posters))))
        available_posters = available_posters[:total_cells]
        
        # Shuffle posters for random distribution
        random.shuffle(available_posters)
        
        # Create a mosaic pattern
        for i, poster in enumerate(available_posters):
            # Calculate grid position for final placement
            row = i // self.grid_params['cols']
            col = i % self.grid_params['cols']
            
            # Calculate final cell center positions
            final_x = (self.grid_params['grid_origin_x'] + 
                       col * self.grid_params['cell_width'] + 
                       self.grid_params['cell_width'] / 2)
            
            final_y = (self.grid_params['grid_origin_y'] + 
                       row * self.grid_params['cell_height'] + 
                       self.grid_params['cell_height'] / 2)
            
            # Random starting position outside the screen
            start_zone = random.randint(0, 3)  # 0: top, 1: right, 2: bottom, 3: left
            
            if start_zone == 0:  # Top
                start_x = random.uniform(-100, WIDTH + 100)
                start_y = random.uniform(-300, -50)
            elif start_zone == 1:  # Right
                start_x = random.uniform(WIDTH + 50, WIDTH + 300)
                start_y = random.uniform(-100, HEIGHT + 100)
            elif start_zone == 2:  # Bottom
                start_x = random.uniform(-100, WIDTH + 100)
                start_y = random.uniform(HEIGHT + 50, HEIGHT + 300)
            else:  # Left
                start_x = random.uniform(-300, -50)
                start_y = random.uniform(-100, HEIGHT + 100)
            
            # Random starting scale (smaller)
            start_scale = random.uniform(0.2, 0.5)
            
            # Randomize the arrival timing for more dynamic effect
            # Earlier rows arrive sooner for a wave-like formation
            time_offset = 0.5 * (row / self.grid_params['rows']) + random.uniform(0, 0.5)
            
            # Each poster has a different animation speed
            anim_duration = self.MOSAIC_FORMATION_TIME - time_offset
            
            # Store poster data
            poster_data = {
                'poster': poster,
                'start_x': start_x,
                'start_y': start_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x,
                'current_y': start_y,
                'start_scale': start_scale,
                'final_scale': self.grid_params['scale_factor'],
                'current_scale': start_scale,
                'rotation': random.uniform(-20, 20),
                'current_rotation': random.uniform(-20, 20),
                'opacity': 255,
                'time_offset': time_offset,
                'anim_duration': anim_duration,
                'row': row,
                'col': col
            }
            
            posters_data.append(poster_data)
        
        return posters_data
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        for poster in self.posters_data:
            # Only start animation after time offset
            if elapsed_time < poster['time_offset']:
                continue
                
            # Calculate animation progress
            anim_time = elapsed_time - poster['time_offset']
            
            if anim_time <= poster['anim_duration']:
                # Still forming mosaic
                progress = anim_time / poster['anim_duration']
                
                # Use elastic easing for more dynamic effect
                eased_progress = self._elastic_ease_out(progress)
                
                # Update position
                poster['current_x'] = poster['start_x'] + (poster['final_x'] - poster['start_x']) * eased_progress
                poster['current_y'] = poster['start_y'] + (poster['final_y'] - poster['start_y']) * eased_progress
                
                # Update scale
                poster['current_scale'] = poster['start_scale'] + (poster['final_scale'] - poster['start_scale']) * eased_progress
                
                # Update rotation - gradually reduce to zero
                poster['current_rotation'] = poster['rotation'] * (1 - eased_progress)
            else:
                # Mosaic formed - add subtle breathing effect
                breathing = math.sin((elapsed_time - poster['anim_duration']) * 2) * 0.03
                
                # Final position with slight movement
                poster['current_x'] = poster['final_x'] + math.sin(elapsed_time * 1.5 + poster['row'] * 0.2) * 2
                poster['current_y'] = poster['final_y'] + math.cos(elapsed_time * 1.2 + poster['col'] * 0.2) * 2
                
                # Final scale with breathing
                poster['current_scale'] = poster['final_scale'] + breathing
                
                # No rotation in final state
                poster['current_rotation'] = 0
            
            # Apply fade effect
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _elastic_ease_out(self, t: float) -> float:
        """
        Elastic ease-out function for dynamic bouncy effect.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        if t == 0 or t == 1:
            return t
            
        p = 0.3  # Period parameter
        s = p / 4
        
        return math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1
    
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation frame to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Fill background with black
        surface.fill((0, 0, 0))
        
        # Sort posters by current scale for proper layering
        # Smaller (further away) posters should be drawn first
        sorted_posters = sorted(self.posters_data, key=lambda p: p['current_scale'])
        
        # Draw each poster
        for poster in sorted_posters:
            # Get the original poster
            img = poster['poster']
            
            # Scale the poster
            try:
                width = max(1, int(img.get_width() * poster['current_scale']))
                height = max(1, int(img.get_height() * poster['current_scale']))
                scaled_img = pygame.transform.smoothscale(img, (width, height))
            except pygame.error:
                scaled_img = img
            
            # Rotate if needed
            if abs(poster['current_rotation']) > 0.5:
                try:
                    rotated_img = pygame.transform.rotate(scaled_img, poster['current_rotation'])
                except pygame.error:
                    rotated_img = scaled_img
            else:
                rotated_img = scaled_img
            
            # Apply opacity
            if poster['opacity'] < 255:
                try:
                    alpha_img = rotated_img.copy()
                    alpha_img.set_alpha(int(poster['opacity']))
                    rotated_img = alpha_img
                except pygame.error:
                    pass
            
            # Calculate position (centered)
            rect = rotated_img.get_rect()
            rect.center = (int(poster['current_x']), int(poster['current_y']))
            
            # Draw to surface
            surface.blit(rotated_img, rect)
