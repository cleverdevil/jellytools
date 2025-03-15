"""
Kaleidoscope animation for the library card generator.
Posters form a rotating kaleidoscope pattern that transforms into a symmetrical grid.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterKaleidoscopeAnimation(BaseAnimation):
    """Animation that creates a kaleidoscope effect with posters before forming a grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize kaleidoscope animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.KALEIDOSCOPE_TIME = 3.0    # Time for kaleidoscope phase (0-3.0s)
        self.TRANSFORM_TIME = 1.5       # Time for transformation to grid (3.0-4.5s)
        self.FADE_START = 4.5           # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5      # When to show text (4.5s)
        
        # Calculate grid parameters for final layout
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized kaleidoscope animation with {len(self.posters_data)} posters")
    
    def _calculate_grid_params(self, posters: List[pygame.Surface]) -> Dict[str, Any]:
        """
        Calculate grid parameters for final layout.
        
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
        
        # Scale factor for final grid
        scale_factor = 1.8
        
        # Calculate cell dimensions with spacing
        spacing = 10  # Tighter spacing for kaleidoscope look
        cell_width = int(poster_width * scale_factor) + spacing
        cell_height = int(poster_height * scale_factor) + spacing
        
        # For a symmetrical grid, make rows and columns equal or close to equal
        # Aim for a square grid for kaleidoscope aesthetic
        side_length = math.ceil(math.sqrt(len(posters))) + 2  # Add extra for coverage
        rows = side_length
        cols = side_length
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Kaleidoscope final grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
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
        total_cells = self.grid_params['rows'] * self.grid_params['cols']
        
        # Calculate center point of screen
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        # Ensure we have enough posters to fill all cells
        available_posters = posters * (math.ceil(total_cells / max(1, len(posters))))
        available_posters = available_posters[:total_cells]
        
        # Create multilayered rings for kaleidoscope effect
        num_rings = 5  # Number of rings in kaleidoscope
        posters_per_ring = [5, 8, 12, 18, 24]  # Posters in each ring, increasing outward
        
        poster_index = 0
        
        # Create poster data for each ring in the kaleidoscope
        for ring_idx in range(num_rings):
            ring_radius = 50 + ring_idx * 60  # Increasing radius for each ring
            num_posters = posters_per_ring[ring_idx]
            
            # Calculate kaleidoscope angle increment
            angle_increment = 2 * math.pi / num_posters
            
            # Calculate rotation speed (inner rings rotate faster)
            rotation_speed = 0.8 - (ring_idx * 0.1)  # Decreasing speed for outer rings
            # Alternate rotation direction for successive rings
            rotation_direction = 1 if ring_idx % 2 == 0 else -1
            
            for i in range(num_posters):
                # Skip if we've used all available posters
                if poster_index >= len(available_posters):
                    break
                    
                poster = available_posters[poster_index]
                poster_index += 1
                
                # Calculate initial angle for this poster
                initial_angle = i * angle_increment
                
                # Calculate kaleidoscope position
                kaleido_x = center_x + ring_radius * math.cos(initial_angle)
                kaleido_y = center_y + ring_radius * math.sin(initial_angle)
                
                # Determine final grid position
                row = poster_index // self.grid_params['cols']
                col = poster_index % self.grid_params['cols']
                
                # Ensure row and col are within bounds
                row = min(row, self.grid_params['rows'] - 1)
                col = min(col, self.grid_params['cols'] - 1)
                
                # Calculate final position in grid
                final_x = (self.grid_params['grid_origin_x'] + 
                          col * self.grid_params['cell_width'] + 
                          self.grid_params['cell_width'] / 2)
                
                final_y = (self.grid_params['grid_origin_y'] + 
                          row * self.grid_params['cell_height'] + 
                          self.grid_params['cell_height'] / 2)
                
                # Scale values
                kaleido_scale = 0.8 + (ring_idx * 0.1)  # Larger scale for outer rings
                final_scale = self.grid_params['scale_factor']
                
                # Store poster data
                poster_data = {
                    'poster': poster,
                    'initial_angle': initial_angle,
                    'ring_radius': ring_radius,
                    'ring_idx': ring_idx,
                    'rotation_speed': rotation_speed * rotation_direction,
                    'kaleido_x': kaleido_x,
                    'kaleido_y': kaleido_y,
                    'final_x': final_x,
                    'final_y': final_y,
                    'current_x': kaleido_x,
                    'current_y': kaleido_y,
                    'kaleido_scale': kaleido_scale,
                    'final_scale': final_scale,
                    'current_scale': kaleido_scale,
                    'rotation': random.uniform(-30, 30),
                    'current_rotation': random.uniform(-30, 30),
                    'opacity': 255,
                    'row': row,
                    'col': col,
                    'index': poster_index,
                    'phase': 'kaleidoscope'  # kaleidoscope -> transforming -> grid
                }
                
                posters_data.append(poster_data)
        
        # If we have more grid cells than posters in the kaleidoscope,
        # add additional posters directly to grid positions
        remaining_cells = total_cells - poster_index
        
        if remaining_cells > 0:
            logger.info(f"Adding {remaining_cells} additional posters for grid completion")
            
            for i in range(remaining_cells):
                if poster_index >= len(available_posters):
                    break
                    
                poster = available_posters[poster_index]
                poster_index += 1
                
                # Calculate grid position
                row = poster_index // self.grid_params['cols']
                col = poster_index % self.grid_params['cols']
                
                # Ensure row and col are within bounds
                row = min(row, self.grid_params['rows'] - 1)
                col = min(col, self.grid_params['cols'] - 1)
                
                # Calculate final position in grid
                final_x = (self.grid_params['grid_origin_x'] + 
                          col * self.grid_params['cell_width'] + 
                          self.grid_params['cell_width'] / 2)
                
                final_y = (self.grid_params['grid_origin_y'] + 
                          row * self.grid_params['cell_height'] + 
                          self.grid_params['cell_height'] / 2)
                
                # Calculate kaleidoscope position (random position off-screen)
                angle = random.uniform(0, 2 * math.pi)
                distance = max(WIDTH, HEIGHT) * 1.2  # Outside screen
                kaleido_x = center_x + distance * math.cos(angle)
                kaleido_y = center_y + distance * math.sin(angle)
                
                # Store poster data
                poster_data = {
                    'poster': poster,
                    'initial_angle': angle,
                    'ring_radius': distance,
                    'ring_idx': num_rings,  # Beyond last ring
                    'rotation_speed': 0.5 * random.choice([-1, 1]),
                    'kaleido_x': kaleido_x,
                    'kaleido_y': kaleido_y,
                    'final_x': final_x,
                    'final_y': final_y,
                    'current_x': kaleido_x,
                    'current_y': kaleido_y,
                    'kaleido_scale': 0.7,
                    'final_scale': self.grid_params['scale_factor'],
                    'current_scale': 0.7,
                    'rotation': random.uniform(-30, 30),
                    'current_rotation': random.uniform(-30, 30),
                    'opacity': 255,
                    'row': row,
                    'col': col,
                    'index': poster_index,
                    'phase': 'kaleidoscope'  # kaleidoscope -> transforming -> grid
                }
                
                posters_data.append(poster_data)
        
        return posters_data
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        # Calculate center point of screen
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        for poster in self.posters_data:
            # Phase 1: Kaleidoscope rotation
            if elapsed_time <= self.KALEIDOSCOPE_TIME:
                poster['phase'] = 'kaleidoscope'
                
                # Update angle based on rotation speed
                updated_angle = poster['initial_angle'] + (elapsed_time * poster['rotation_speed'] * 2 * math.pi)
                
                # Calculate current position in kaleidoscope
                updated_radius = poster['ring_radius'] + math.sin(elapsed_time * 2) * 15  # Add pulsing effect
                poster['current_x'] = center_x + updated_radius * math.cos(updated_angle)
                poster['current_y'] = center_y + updated_radius * math.sin(updated_angle)
                
                # Add scale pulsing effect
                scale_pulse = 0.05 * math.sin(elapsed_time * 3 + poster['ring_idx'] * 0.5)
                poster['current_scale'] = poster['kaleido_scale'] + scale_pulse
                
                # Add rotation effect - rotating in kaleidoscope
                poster['current_rotation'] = poster['rotation'] + elapsed_time * 30 * poster['rotation_speed']
            
            # Phase 2: Transform from kaleidoscope to grid
            elif elapsed_time <= self.KALEIDOSCOPE_TIME + self.TRANSFORM_TIME:
                poster['phase'] = 'transforming'
                
                # Calculate transformation progress
                transform_progress = (elapsed_time - self.KALEIDOSCOPE_TIME) / self.TRANSFORM_TIME
                transform_progress = min(1.0, transform_progress)
                
                # Use easing function for smooth transition
                eased_progress = self._ease_out_cubic(transform_progress)
                
                # Calculate current kaleidoscope position (continuing rotation)
                kaleido_angle = poster['initial_angle'] + (self.KALEIDOSCOPE_TIME * poster['rotation_speed'] * 2 * math.pi)
                kaleido_x = center_x + poster['ring_radius'] * math.cos(kaleido_angle)
                kaleido_y = center_y + poster['ring_radius'] * math.sin(kaleido_angle)
                
                # Interpolate between kaleidoscope and grid positions
                poster['current_x'] = kaleido_x + (poster['final_x'] - kaleido_x) * eased_progress
                poster['current_y'] = kaleido_y + (poster['final_y'] - kaleido_y) * eased_progress
                
                # Update scale
                poster['current_scale'] = poster['kaleido_scale'] + (poster['final_scale'] - poster['kaleido_scale']) * eased_progress
                
                # Update rotation - gradually reduce to zero
                kaleido_rotation = poster['rotation'] + self.KALEIDOSCOPE_TIME * 30 * poster['rotation_speed']
                poster['current_rotation'] = kaleido_rotation * (1 - eased_progress)
            
            # Phase 3: Final grid with subtle motion
            else:
                poster['phase'] = 'grid'
                
                # Add subtle oscillation for grid
                time_factor = elapsed_time * 1.5
                row_factor = poster['row'] * 0.2
                col_factor = poster['col'] * 0.1
                
                # Calculate wobble effect
                wobble_x = math.sin(time_factor + row_factor) * 2
                wobble_y = math.cos(time_factor + col_factor) * 2
                
                poster['current_x'] = poster['final_x'] + wobble_x
                poster['current_y'] = poster['final_y'] + wobble_y
                
                # Subtle scale pulsing
                pulse = 0.02 * math.sin(time_factor + row_factor + col_factor)
                poster['current_scale'] = poster['final_scale'] + pulse
                
                # No rotation in final state
                poster['current_rotation'] = 0
            
            # Apply fade effect for text overlay
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _ease_out_cubic(self, t: float) -> float:
        """
        Cubic ease-out function.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        return 1 - math.pow(1 - t, 3)
    
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation frame to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Fill background with black
        surface.fill((0, 0, 0))
        
        # Sort posters for proper layering:
        # - In kaleidoscope phase, sort by ring index (inner rings drawn on top)
        # - In transformation phase, sort by distance from center
        # - In grid phase, sort by row and column
        def sorting_key(p):
            if p['phase'] == 'kaleidoscope':
                # Inner rings (lower index) on top
                return -p['ring_idx']
            elif p['phase'] == 'transforming':
                # Calculate distance from center
                dx = p['current_x'] - WIDTH / 2
                dy = p['current_y'] - HEIGHT / 2
                distance = math.sqrt(dx*dx + dy*dy)
                # Further posters drawn first, closer posters drawn on top
                return distance
            else:  # grid phase
                # Sort by row then column
                return p['row'] * 1000 + p['col']
        
        sorted_posters = sorted(self.posters_data, key=sorting_key)
        
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
