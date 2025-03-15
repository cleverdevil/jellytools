"""
Cascade animation for the library card generator.
Posters cascade from side to side, flowing like a waterfall across the screen before settling into a grid.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterCascadeAnimation(BaseAnimation):
    """Animation that creates a cascade of posters flowing across the screen"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize cascade animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.CASCADE_TIME = 4.0       # Time for cascade effect (0-4.0s)
        self.FADE_START = 4.5         # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5    # When to show text (4.5s)
        
        # Calculate grid parameters for final layout
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized cascade animation with {len(self.posters_data)} posters")
    
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
        
        # Calculate columns and rows for grid
        cols = math.ceil(WIDTH / cell_width) + 2  # Add extra columns
        rows = math.ceil(HEIGHT / cell_height) + 1  # Add extra row
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Cascade final grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
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
        
        # Define cascade flow pattern
        flow_direction = 1  # 1 = right, -1 = left
        
        # Create cascade pattern for posters
        for i, poster in enumerate(available_posters):
            # Calculate grid position for final placement
            row = i // self.grid_params['cols']
            col = i % self.grid_params['cols']
            
            # Alternate flow direction for each row
            if row % 2 == 1:
                adjusted_col = self.grid_params['cols'] - 1 - col
                flow_direction = -1
            else:
                adjusted_col = col
                flow_direction = 1
            
            # Calculate final grid position
            final_x = (self.grid_params['grid_origin_x'] + 
                       adjusted_col * self.grid_params['cell_width'] + 
                       self.grid_params['cell_width'] / 2)
            
            final_y = (self.grid_params['grid_origin_y'] + 
                       row * self.grid_params['cell_height'] + 
                       self.grid_params['cell_height'] / 2)
            
            # Calculate cascade starting position
            # For cascade effect, posters start off-screen based on row and column
            start_x = -self.grid_params['cell_width'] if flow_direction > 0 else WIDTH + self.grid_params['cell_width']
            
            # Staggered vertical positioning
            vertical_offset = row * 100  # Spacing between rows
            start_y = -200 + vertical_offset  # Start above screen with offset
            
            # Delay based on position in the cascade
            # First row posters come in first, with staggered entry
            base_delay = row * 0.3  # Base delay by row
            col_delay = abs(adjusted_col - (self.grid_params['cols'] // 2)) * 0.02  # Small delay by column distance from center
            
            # First row has no delay, subsequent rows start with delay
            delay = base_delay + col_delay
            
            # Randomize some parameters for more natural effect
            random_offset_x = random.uniform(-50, 50)
            random_offset_y = random.uniform(-20, 20)
            
            # Scale factors for animation
            start_scale = random.uniform(0.7, 1.1)      # Variable starting scale
            final_scale = self.grid_params['scale_factor']  # Full size in grid
            
            # Create poster data
            poster_data = {
                'poster': poster,
                'start_x': start_x + random_offset_x,
                'start_y': start_y + random_offset_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x + random_offset_x,
                'current_y': start_y + random_offset_y,
                'start_scale': start_scale,
                'final_scale': final_scale,
                'current_scale': start_scale,
                'flow_direction': flow_direction,
                'row': row,
                'col': adjusted_col,
                'start_rotation': random.uniform(-15, 15),
                'current_rotation': random.uniform(-15, 15),
                'opacity': 255,
                'delay': delay,
                'has_started': False,
                'has_landed': False,
                'bounce_offset': 0,
                'path_points': []  # Will store path points for curved trajectory
            }
            
            # Generate curved path for natural cascade motion
            self._generate_path(poster_data)
            
            posters_data.append(poster_data)
        
        return posters_data
    
    def _generate_path(self, poster_data: Dict[str, Any]) -> None:
        """
        Generate a curved path for poster movement using Bezier curves.
        
        Args:
            poster_data (Dict[str, Any]): Poster data dictionary to add path to
        """
        # Define control points for curved path
        start_x, start_y = poster_data['start_x'], poster_data['start_y']
        end_x, end_y = poster_data['final_x'], poster_data['final_y']
        
        # Calculate intermediate points for cascade effect
        # For natural cascade, use control points that create an S-curve
        if poster_data['flow_direction'] > 0:  # Left to right
            # Create an arc that moves down then curves toward final position
            control1_x = start_x + (end_x - start_x) * 0.3
            control1_y = HEIGHT * 0.4 + poster_data['row'] * 40
            
            control2_x = start_x + (end_x - start_x) * 0.7
            control2_y = HEIGHT * 0.6 + poster_data['row'] * 30
        else:  # Right to left
            # Mirror the control points
            control1_x = start_x + (end_x - start_x) * 0.3
            control1_y = HEIGHT * 0.4 + poster_data['row'] * 40
            
            control2_x = start_x + (end_x - start_x) * 0.7
            control2_y = HEIGHT * 0.6 + poster_data['row'] * 30
        
        # Store path points for cubic Bezier curve
        poster_data['path_points'] = [
            (start_x, start_y),
            (control1_x, control1_y),
            (control2_x, control2_y),
            (end_x, end_y)
        ]
    
    def _cubic_bezier(self, p0, p1, p2, p3, t):
        """
        Calculate point on cubic Bezier curve.
        
        Args:
            p0: Start point
            p1, p2: Control points
            p3: End point
            t: Parameter (0 to 1)
            
        Returns:
            Tuple (x, y): Point on curve
        """
        return (
            (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0],
            (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        )
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        for poster in self.posters_data:
            # Skip if not yet time to start this poster's animation
            if elapsed_time < poster['delay']:
                continue
                
            # Mark poster as started
            poster['has_started'] = True
            
            # Calculate time since this poster started moving
            poster_time = elapsed_time - poster['delay']
            
            # Cascade motion (path following)
            if poster_time <= self.CASCADE_TIME:
                # Calculate progress along the path
                path_progress = min(1.0, poster_time / self.CASCADE_TIME)
                
                # Use easing function for natural motion
                eased_progress = self._ease_out_back(path_progress)
                
                # Calculate position along Bezier curve
                p0, p1, p2, p3 = poster['path_points']
                x, y = self._cubic_bezier(p0, p1, p2, p3, eased_progress)
                
                # Update position
                poster['current_x'] = x
                poster['current_y'] = y
                
                # Scale gradually to final size
                poster['current_scale'] = poster['start_scale'] + (poster['final_scale'] - poster['start_scale']) * eased_progress
                
                # Gradually reduce rotation as poster approaches final position
                poster['current_rotation'] = poster['start_rotation'] * (1 - eased_progress)
                
                # Add bouncing effect when approaching final position
                if eased_progress > 0.8:
                    bounce_factor = (eased_progress - 0.8) / 0.2  # 0 to 1 in final 20% of motion
                    poster['bounce_offset'] = 10 * math.sin(bounce_factor * math.pi) * (1 - bounce_factor)
                else:
                    poster['bounce_offset'] = 0
                
                # Mark as landed once it reaches the end
                if path_progress >= 0.95:
                    poster['has_landed'] = True
            else:
                # Final position with subtle motion after cascade
                poster['has_landed'] = True
                
                # Add subtle oscillation for "settling" effect
                time_factor = elapsed_time * 2
                row_factor = poster['row'] * 0.2
                col_factor = poster['col'] * 0.3
                
                poster['current_x'] = poster['final_x'] + math.sin(time_factor + row_factor) * 2
                poster['current_y'] = poster['final_y'] + poster['bounce_offset'] + math.cos(time_factor + col_factor) * 2
                
                # Full scale with subtle pulsing
                pulse = 0.02 * math.sin(time_factor + row_factor + col_factor)
                poster['current_scale'] = poster['final_scale'] + pulse
                
                # No rotation in final state
                poster['current_rotation'] = 0
                
                # Gradually reduce bounce
                if poster['bounce_offset'] != 0:
                    decay_rate = 0.2
                    poster['bounce_offset'] *= (1 - decay_rate)
                    if abs(poster['bounce_offset']) < 0.1:
                        poster['bounce_offset'] = 0
            
            # Apply fade effect
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _ease_out_back(self, t: float) -> float:
        """
        Ease-out-back function for overshoot effect.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        c1 = 1.70158
        c3 = c1 + 1
        
        return 1 + c3 * math.pow(t - 1, 3) + c1 * math.pow(t - 1, 2)
    
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation frame to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Fill background with black
        surface.fill((0, 0, 0))
        
        # Sort posters for proper layering - draw in row order, then by has_landed state
        # This ensures posters that have landed appear in front of those still in motion
        sorted_posters = sorted(
            self.posters_data, 
            key=lambda p: (
                not p['has_started'],    # Draw started posters first
                p['row'],                # Then by row (top to bottom)
                not p['has_landed'],     # Then landed posters in front
                p['col']                 # Then by column
            )
        )
        
        # Draw each poster
        for poster in sorted_posters:
            # Skip if not started yet
            if not poster['has_started']:
                continue
                
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
