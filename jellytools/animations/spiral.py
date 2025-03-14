"""
Spiral animation for the library card generator.
Posters begin in a horizontal line, form a spiral, then transition to a grid.
"""
import math
import pygame
import random
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterSpinAnimation(BaseAnimation):
    """Animation that forms a spiral from a horizontal line, then transitions to a grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize spiral animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.SPIRAL_FORMATION_TIME = 3.0  # Time to form spiral (0-3s)
        self.GRID_TRANSITION_TIME = 2.0   # Time to transition to grid (3-5s)
        self.FADE_START = 4.5             # When to start fading
        self.TEXT_START_TIME = 4.5        # When to show text
        
        # Calculate grid parameters based on the original grid animation
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized spiral animation with {len(self.posters_data)} posters")
    
    def _calculate_grid_params(self, posters: List[pygame.Surface]) -> Dict[str, Any]:
        """
        Calculate grid parameters similar to the original grid animation.
        
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
        
        # Create a grid that fills more of the viewport
        # Use more of the screen to eliminate gaps
        visible_grid_width = WIDTH * 1.2  # Extend beyond viewport width to remove side gaps
        visible_grid_height = HEIGHT * 1.3  # Extend beyond viewport height to remove top gap
        
        # Calculate how many posters can fit in the visible area
        cols = max(8, int(visible_grid_width / poster_width))
        rows = max(6, int(visible_grid_height / poster_height))
        
        # Calculate total grid size
        grid_width = cols * poster_width
        grid_height = rows * poster_height
        
        # Grid origin (top-left corner position) - center in viewport
        # Shift upward to eliminate top gap
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2 - HEIGHT * 0.05  # Shift up 5% of viewport height
        
        logger.info(f"Grid params: {cols}x{rows} grid, origin at ({grid_origin_x}, {grid_origin_y})")
        
        return {
            'poster_width': poster_width,
            'poster_height': poster_height,
            'cols': cols,
            'rows': rows,
            'grid_width': grid_width,
            'grid_height': grid_height,
            'grid_origin_x': grid_origin_x,
            'grid_origin_y': grid_origin_y
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
        
        # Limit the number of posters to avoid performance issues
        max_posters = min(300, len(posters))
        
        # Triple the initial poster size as requested
        small_scale = 0.75  # Increased from 0.25 (tripled)
        
        # Spacing between posters in the horizontal line
        # Increase spacing to accommodate larger posters
        spacing = 60  # Increased from 20
        
        # Horizontal line will be centered on the screen
        line_width = max_posters * spacing
        line_start_x = (WIDTH - line_width) / 2
        line_y = HEIGHT / 2
        
        # Process each poster
        for i in range(max_posters):
            if i >= len(posters):
                break
                
            poster = posters[i]
            
            # Scale down the poster for the initial line and spiral
            scaled_width = int(poster.get_width() * small_scale)
            scaled_height = int(poster.get_height() * small_scale)
            
            try:
                small_poster = pygame.transform.smoothscale(poster, (scaled_width, scaled_height))
            except pygame.error:
                continue
            
            # Initial position in horizontal line
            line_x = line_start_x + i * spacing
            
            # Calculate grid position
            cell_idx = i
            grid_row = cell_idx // self.grid_params['cols']
            grid_col = cell_idx % self.grid_params['cols']
            
            grid_x = (self.grid_params['grid_origin_x'] + 
                      grid_col * self.grid_params['poster_width'] + 
                      self.grid_params['poster_width'] / 2)
            
            grid_y = (self.grid_params['grid_origin_y'] + 
                      grid_row * self.grid_params['poster_height'] + 
                      self.grid_params['poster_height'] / 2)
            
            # Calculate spiral parameters
            # Each poster will move along a spiral path from the line to its spiral position
            # We'll use the Archimedean spiral formula: r = a + b * theta
            max_spiral_radius = min(WIDTH, HEIGHT) * 0.4
            spiral_a = 10  # Initial radius
            spiral_b = max_spiral_radius / (2 * math.pi * 10)  # Growth rate
            
            # Angle in the spiral (distributed evenly)
            spiral_angle = (i / max_posters) * 2 * math.pi * 8  # 8 full rotations
            
            # Distance from center (spiral radius)
            spiral_radius = spiral_a + spiral_b * spiral_angle
            
            # Position in the spiral
            spiral_x = WIDTH / 2 + spiral_radius * math.cos(spiral_angle)
            spiral_y = HEIGHT / 2 + spiral_radius * math.sin(spiral_angle)
            
            poster_data = {
                'poster': poster,
                'small_poster': small_poster,
                'line_x': line_x,
                'line_y': line_y,
                'spiral_x': spiral_x,
                'spiral_y': spiral_y,
                'spiral_angle': spiral_angle,
                'spiral_radius': spiral_radius,
                'grid_x': grid_x,
                'grid_y': grid_y,
                'current_x': line_x,
                'current_y': line_y,
                'small_scale': small_scale,
                'full_scale': 1.0,  # Final scale for grid view, matching the grid animation
                'current_scale': small_scale,
                'rotation': 0,
                'current_rotation': 0,
                'opacity': 255,
                'phase': 'line',  # Phases: line -> spiral -> grid
                'index': i
            }
            
            posters_data.append(poster_data)
        
        return posters_data
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        # Phase timings
        spiral_end_time = self.SPIRAL_FORMATION_TIME
        grid_end_time = spiral_end_time + self.GRID_TRANSITION_TIME
        
        for poster in self.posters_data:
            # Phase 1: Line to Spiral (0-3s)
            if elapsed_time <= spiral_end_time:
                # Set phase
                poster['phase'] = 'spiral'
                
                # Calculate progress
                spiral_progress = elapsed_time / spiral_end_time
                # Use ease-in-out for smooth start and end
                eased_progress = self.ease_in_out_quad(spiral_progress)
                
                # Move from line position to spiral position
                poster['current_x'] = poster['line_x'] + (poster['spiral_x'] - poster['line_x']) * eased_progress
                poster['current_y'] = poster['line_y'] + (poster['spiral_y'] - poster['line_y']) * eased_progress
                
                # Gradually rotate based on spiral angle
                target_rotation = poster['spiral_angle'] * 180 / math.pi  # Convert to degrees
                poster['current_rotation'] = target_rotation * eased_progress
            
            # Phase 2: Spiral to Grid (3-5s)
            elif elapsed_time <= grid_end_time:
                # Set phase
                poster['phase'] = 'grid'
                
                # Calculate grid transition progress
                grid_progress = (elapsed_time - spiral_end_time) / self.GRID_TRANSITION_TIME
                eased_progress = self.ease_in_out_quad(grid_progress)
                
                # Move from spiral position to grid position
                poster['current_x'] = poster['spiral_x'] + (poster['grid_x'] - poster['spiral_x']) * eased_progress
                poster['current_y'] = poster['spiral_y'] + (poster['grid_y'] - poster['spiral_y']) * eased_progress
                
                # Scale up from small to full size
                poster['current_scale'] = poster['small_scale'] + (poster['full_scale'] - poster['small_scale']) * eased_progress
                
                # Gradually rotate to 0 degrees
                start_rotation = poster['spiral_angle'] * 180 / math.pi
                poster['current_rotation'] = start_rotation * (1 - eased_progress)
                
                # Add subtle oscillation for settling effect in the later part of the transition
                if grid_progress > 0.8:
                    settle_factor = (grid_progress - 0.8) / 0.2
                    damping = 1 - settle_factor
                    oscillation = math.sin(elapsed_time * 20) * 3 * damping
                    poster['current_x'] += oscillation
                    poster['current_y'] += oscillation * 0.5
            
            # Final phase: Settled Grid
            else:
                # Set phase
                poster['phase'] = 'settled'
                
                # Fixed grid position
                poster['current_x'] = poster['grid_x']
                poster['current_y'] = poster['grid_y']
                poster['current_scale'] = poster['full_scale']
                poster['current_rotation'] = 0
            
            # Apply fade effect
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)  # Cap at 1.0
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def draw(self, surface: pygame.Surface):
        """
        Draw animation to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Clear background
        surface.fill((0, 0, 0))
        
        # Sort posters by phase and position for proper layering
        phase_order = {'line': 0, 'spiral': 1, 'grid': 2, 'settled': 3}
        sorted_posters = sorted(self.posters_data, key=lambda p: (phase_order.get(p['phase'], 0), p.get('index', 0)))
        
        # Draw each poster
        for poster in sorted_posters:
            # Determine scale threshold for using small or original poster
            scale_threshold = 0.5
            
            if poster['current_scale'] < scale_threshold:
                # Use pre-scaled small version for efficiency when poster is small
                base_img = poster['small_poster']
                
                # Calculate adjustment factor for small poster
                scale_adjust = poster['current_scale'] / poster['small_scale']
                
                if abs(scale_adjust - 1.0) > 0.01:  # Only rescale if significantly different
                    try:
                        width = max(1, int(base_img.get_width() * scale_adjust))
                        height = max(1, int(base_img.get_height() * scale_adjust))
                        img = pygame.transform.smoothscale(base_img, (width, height))
                    except pygame.error:
                        img = base_img
                else:
                    img = base_img
            else:
                # Use original poster with scaling for better quality when poster is larger
                base_img = poster['poster']
                
                try:
                    width = max(1, int(base_img.get_width() * poster['current_scale']))
                    height = max(1, int(base_img.get_height() * poster['current_scale']))
                    img = pygame.transform.smoothscale(base_img, (width, height))
                except pygame.error:
                    img = base_img
            
            # Apply rotation
            if abs(poster['current_rotation']) > 0.1:  # Only rotate if angle is significant
                try:
                    img = pygame.transform.rotate(img, poster['current_rotation'])
                except pygame.error:
                    pass
            
            # Apply opacity
            if poster['opacity'] < 255:
                # Create a copy to avoid affecting the original
                img = img.copy()
                img.set_alpha(int(poster['opacity']))
            
            # Position at center
            rect = img.get_rect()
            rect.center = (int(poster['current_x']), int(poster['current_y']))
            
            # Draw to surface
            surface.blit(img, rect)
