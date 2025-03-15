"""
Explode animation for the library card generator.
Posters start compressed in the center of the screen, then explode outward into a grid.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterExplodeAnimation(BaseAnimation):
    """Animation that creates an explosion effect with posters from center to grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize explode animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.COMPRESS_TIME = 1.0     # Time for compressed center phase (0-1.0s)
        self.EXPLODE_TIME = 2.5      # Time for explosion phase (1.0-3.5s)
        self.SETTLE_TIME = 1.0       # Time for settling phase (3.5-4.5s)
        self.FADE_START = 4.5        # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5   # When to show text (4.5s)
        
        # Calculate grid parameters for final layout
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized explode animation with {len(self.posters_data)} posters")
    
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
        scale_factor = 2.0
        
        # Calculate cell dimensions with spacing
        spacing = 20  # Space between posters
        cell_width = int(poster_width * scale_factor) + spacing
        cell_height = int(poster_height * scale_factor) + spacing
        
        # Create a square-ish grid that extends beyond screen edges
        # Use golden ratio for more aesthetic grid
        aspect_ratio = WIDTH / HEIGHT
        base_cols = 10  # Base number of columns
        
        cols = base_cols
        rows = math.ceil(base_cols / aspect_ratio)
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Explode final grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
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
        
        # Calculate center point of screen
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        # Create poster data with explode pattern
        for i, poster in enumerate(available_posters):
            # Calculate grid position for final placement
            row = i // self.grid_params['cols']
            col = i % self.grid_params['cols']
            
            # Calculate final grid position
            final_x = (self.grid_params['grid_origin_x'] + 
                       col * self.grid_params['cell_width'] + 
                       self.grid_params['cell_width'] / 2)
            
            final_y = (self.grid_params['grid_origin_y'] + 
                       row * self.grid_params['cell_height'] + 
                       self.grid_params['cell_height'] / 2)
            
            # Calculate vector from center to final position (used for explosion direction)
            vector_x = final_x - center_x
            vector_y = final_y - center_y
            vector_length = math.sqrt(vector_x**2 + vector_y**2)
            
            # Normalize vector
            if vector_length > 0:
                vector_x /= vector_length
                vector_y /= vector_length
            
            # Calculate compressed position (slightly offset from center)
            # Add small random offsets to prevent all posters being exactly at center
            compressed_offset_x = random.uniform(-20, 20)
            compressed_offset_y = random.uniform(-20, 20)
            
            compressed_x = center_x + compressed_offset_x
            compressed_y = center_y + compressed_offset_y
            
            # Calculate "overshoot" position for explosion
            # Posters will fly past their final position and then come back
            overshoot_factor = 1.3 + random.uniform(0, 0.3)  # Random overshoot distance
            overshoot_x = center_x + vector_x * vector_length * overshoot_factor
            overshoot_y = center_y + vector_y * vector_length * overshoot_factor
            
            # Scale factors for animation
            compressed_scale = 0.2 + random.uniform(0, 0.1)  # Small during compression
            overshoot_scale = self.grid_params['scale_factor'] * 1.1  # Slightly larger at overshoot
            final_scale = self.grid_params['scale_factor']  # Normal in final grid
            
            # Rotation animation parameters
            initial_rotation = random.uniform(-30, 30)
            spin_factor = random.choice([-1, 1]) * random.uniform(0.8, 1.2)  # Direction and speed of spin
            
            # Create poster data
            poster_data = {
                'poster': poster,
                'center_x': center_x,
                'center_y': center_y,
                'compressed_x': compressed_x,
                'compressed_y': compressed_y,
                'overshoot_x': overshoot_x,
                'overshoot_y': overshoot_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': compressed_x,
                'current_y': compressed_y,
                'vector_x': vector_x,
                'vector_y': vector_y,
                'vector_length': vector_length,
                'compressed_scale': compressed_scale,
                'overshoot_scale': overshoot_scale,
                'final_scale': final_scale,
                'current_scale': compressed_scale,
                'initial_rotation': initial_rotation,
                'current_rotation': initial_rotation,
                'spin_factor': spin_factor,
                'row': row,
                'col': col,
                'opacity': 255,
                'phase': 'compressed',  # Phases: compressed -> exploding -> settling -> settled
                'explode_delay': random.uniform(0, 0.3)  # Random delay for explosion
            }
            
            posters_data.append(poster_data)
        
        return posters_data
    
    def _ease_out_quart(self, t: float) -> float:
        """
        Quartic ease-out function.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        return 1 - math.pow(1 - t, 4)
    
    def _elastic_ease_out(self, t: float) -> float:
        """
        Elastic ease-out function for bouncy effect.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        if t == 0 or t == 1:
            return t
            
        c4 = (2 * math.pi) / 3
        return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        for poster in self.posters_data:
            # Phase 1: Compressed center with subtle pulsing
            if elapsed_time <= self.COMPRESS_TIME:
                poster['phase'] = 'compressed'
                
                # Calculate pulse effect
                pulse_factor = 0.1 * math.sin(elapsed_time * 10)
                pulse_scale = poster['compressed_scale'] * (1 + pulse_factor)
                
                # Update position and scale with pulse
                poster['current_x'] = poster['compressed_x']
                poster['current_y'] = poster['compressed_y']
                poster['current_scale'] = pulse_scale
                
                # Update rotation - slow rotation during compression
                poster['current_rotation'] = poster['initial_rotation'] + elapsed_time * 30 * poster['spin_factor']
            
            # Phase 2: Explosion outward
            elif elapsed_time <= self.COMPRESS_TIME + self.EXPLODE_TIME:
                # Only start exploding after the delay
                if elapsed_time < self.COMPRESS_TIME + poster['explode_delay']:
                    continue
                    
                poster['phase'] = 'exploding'
                
                # Calculate explosion progress
                explosion_time = self.EXPLODE_TIME - poster['explode_delay']
                explosion_progress = (elapsed_time - self.COMPRESS_TIME - poster['explode_delay']) / explosion_time
                explosion_progress = min(1.0, explosion_progress)
                
                # Use easing function for more dynamic explosion
                eased_progress = self._ease_out_quart(explosion_progress)
                
                # Update position - from compressed to overshoot position
                poster['current_x'] = poster['compressed_x'] + (poster['overshoot_x'] - poster['compressed_x']) * eased_progress
                poster['current_y'] = poster['compressed_y'] + (poster['overshoot_y'] - poster['compressed_y']) * eased_progress
                
                # Update scale - grow during explosion
                poster['current_scale'] = poster['compressed_scale'] + (poster['overshoot_scale'] - poster['compressed_scale']) * eased_progress
                
                # Update rotation - fast spinning during explosion
                spin_speed = 360 * (1 - eased_progress)  # Slow down as it reaches overshoot position
                poster['current_rotation'] += spin_speed * poster['spin_factor'] * 0.03
            
            # Phase 3: Settling from overshoot to final position
            elif elapsed_time <= self.COMPRESS_TIME + self.EXPLODE_TIME + self.SETTLE_TIME:
                poster['phase'] = 'settling'
                
                # Calculate settling progress
                settle_progress = (elapsed_time - self.COMPRESS_TIME - self.EXPLODE_TIME) / self.SETTLE_TIME
                settle_progress = min(1.0, settle_progress)
                
                # Use elastic easing for bouncy settling effect
                eased_progress = self._elastic_ease_out(settle_progress)
                
                # Update position - from overshoot to final position
                poster['current_x'] = poster['overshoot_x'] + (poster['final_x'] - poster['overshoot_x']) * eased_progress
                poster['current_y'] = poster['overshoot_y'] + (poster['final_y'] - poster['overshoot_y']) * eased_progress
                
                # Update scale - normalize from overshoot to final
                poster['current_scale'] = poster['overshoot_scale'] + (poster['final_scale'] - poster['overshoot_scale']) * eased_progress
                
                # Update rotation - gradually stop spinning and align to zero
                rot_progress = self._ease_in_out_quad(settle_progress)
                target_rotation = 0
                current_rot = poster['current_rotation'] % 360  # Normalize to 0-360
                
                # Choose shortest path to zero rotation
                if current_rot > 180:
                    current_rot -= 360
                
                poster['current_rotation'] = current_rot * (1 - rot_progress)
            
            # Phase 4: Final grid with subtle motion
            else:
                poster['phase'] = 'settled'
                
                # Add subtle motion in final state
                wobble_x = math.sin(elapsed_time * 2 + poster['row'] * 0.5) * 2
                wobble_y = math.cos(elapsed_time * 1.5 + poster['col'] * 0.5) * 2
                
                poster['current_x'] = poster['final_x'] + wobble_x
                poster['current_y'] = poster['final_y'] + wobble_y
                
                # Subtle scale pulsing
                pulse = 0.03 * math.sin(elapsed_time * 1.2 + (poster['row'] + poster['col']) * 0.2)
                poster['current_scale'] = poster['final_scale'] + pulse
                
                # No rotation in final state
                poster['current_rotation'] = 0
            
            # Apply fade effect for text overlay
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _ease_in_out_quad(self, t: float) -> float:
        """
        Quadratic ease-in-out function.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - math.pow(-2 * t + 2, 2) / 2
    
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation frame to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Fill background with black
        surface.fill((0, 0, 0))
        
        # Sort posters for proper layering
        # During compression and explosion, sort by distance from center
        # For settling and final phase, sort by row/column
        def sorting_key(p):
            if p['phase'] in ['compressed', 'exploding']:
                # Calculate distance from center
                dx = p['current_x'] - WIDTH / 2
                dy = p['current_y'] - HEIGHT / 2
                distance = math.sqrt(dx*dx + dy*dy)
                # Reversed distance (farther objects drawn first)
                return -distance
            else:
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
