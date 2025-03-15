"""
Shockwave animation for the library card generator.
Posters gather in the center, pulse outward with increasing strength,
and finally burst out to their grid positions with one final shockwave.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any, Tuple

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterShockwaveAnimation(BaseAnimation):
    """Animation that creates a pulsing shockwave effect from center to grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize shockwave animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.GATHER_TIME = 1.0        # Time for posters to gather at center (0-1.0s)
        self.PULSE_TIME = 3.0         # Time for pulse effects (1.0-4.0s)
        self.SETTLE_TIME = 0.5        # Time for settling to grid (4.0-4.5s)
        self.FADE_START = 4.5         # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5    # When to show text (4.5s)
        
        # Pulse parameters
        self.PULSE_COUNT = 4          # Number of pulses before final burst
        
        # Calculate grid parameters for final layout
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized shockwave animation with {len(self.posters_data)} posters")
    
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
        spacing = 20  # Space between posters
        cell_width = int(poster_width * scale_factor) + spacing
        cell_height = int(poster_height * scale_factor) + spacing
        
        # Create a grid layout
        aspect_ratio = WIDTH / HEIGHT
        base_cols = 9  # Base number of columns
        
        cols = base_cols
        rows = int(base_cols / aspect_ratio) + 2  # Add extra rows for coverage
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Shockwave final grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
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
        
        # Calculate center point of screen
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        # Calculate total cells in the grid
        total_cells = self.grid_params['cols'] * self.grid_params['rows']
        
        # Ensure we have enough posters to fill all cells
        available_posters = posters * (math.ceil(total_cells / max(1, len(posters))))
        available_posters = available_posters[:total_cells]
        
        # For each poster, calculate initial, center, and final positions
        for i, poster in enumerate(available_posters):
            # Calculate grid position for final placement
            grid_row = i // self.grid_params['cols']
            grid_col = i % self.grid_params['cols']
            
            # Calculate final position in grid
            final_x = (self.grid_params['grid_origin_x'] + 
                      grid_col * self.grid_params['cell_width'] + 
                      self.grid_params['cell_width'] / 2)
            
            final_y = (self.grid_params['grid_origin_y'] + 
                      grid_row * self.grid_params['cell_height'] + 
                      self.grid_params['cell_height'] / 2)
            
            # Calculate vector from center to final position (for direction)
            vector_x = final_x - center_x
            vector_y = final_y - center_y
            
            # Calculate distance from center to final position
            distance = math.sqrt(vector_x**2 + vector_y**2)
            
            # Normalize vector (unit direction)
            if distance > 0:
                direction_x = vector_x / distance
                direction_y = vector_y / distance
            else:
                direction_x = 0
                direction_y = 0
                
            # Calculate angle from center (for consistent group movements)
            angle = math.atan2(vector_y, vector_x)
            
            # Initial position - start from outside the screen in the opposite direction
            # This creates a "swooping in" effect toward the center
            start_factor = 1.5  # How far outside the screen to start
            start_x = center_x - direction_x * WIDTH * start_factor
            start_y = center_y - direction_y * HEIGHT * start_factor
            
            # Vary starting positions a bit for more natural look
            start_x += random.uniform(-100, 100)
            start_y += random.uniform(-100, 100)
            
            # Create poster data
            poster_data = {
                'poster': poster,
                'start_x': start_x,
                'start_y': start_y,
                'center_x': center_x,
                'center_y': center_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x,
                'current_y': start_y,
                'vector_x': vector_x,
                'vector_y': vector_y,
                'direction_x': direction_x,
                'direction_y': direction_y,
                'distance': distance,
                'angle': angle,
                'start_scale': random.uniform(0.3, 0.6),
                'center_scale': 0.7,  # Slightly smaller when clustered in center
                'final_scale': self.grid_params['scale_factor'],
                'current_scale': random.uniform(0.3, 0.6),
                'start_rotation': random.uniform(-180, 180),
                'current_rotation': random.uniform(-180, 180),
                'opacity': 255,
                'entry_delay': random.uniform(0, self.GATHER_TIME * 0.5),  # Staggered entry
                'index': i,
                'grid_row': grid_row,
                'grid_col': grid_col,
                'phase': 'entry',  # entry -> center -> pulse -> grid
                'has_started': False,
                'pulse_offset': random.uniform(0, 0.1),  # Small offset for natural pulsing
                'pulse_factor': 0.0,  # Current pulse amount (0.0-1.0)
                # Initialize transition values for settling phase
                'burst_x': center_x,  # Default to center in case we skip phases
                'burst_y': center_y,
                'burst_scale': 0.7,
            }
            
            posters_data.append(poster_data)
        
        return posters_data
    
    def _pulse_function(self, elapsed_time: float, pulse_index: int, distance: float) -> Tuple[float, float]:
        """
        Calculate pulse effect displacement and scale based on time and distance.
        
        Args:
            elapsed_time (float): Current time in pulse phase
            pulse_index (int): Which pulse this is (0 to PULSE_COUNT-1)
            distance (float): Base distance from center to final position
            
        Returns:
            Tuple[float, float]: (displacement_factor, scale_factor)
        """
        # Calculate pulse period
        pulse_period = self.PULSE_TIME / (self.PULSE_COUNT + 1)  # +1 for final burst
        
        # Calculate pulse timing
        pulse_start = pulse_index * pulse_period
        pulse_end = pulse_start + pulse_period * 0.4  # Pulse takes 40% of period
        recovery_end = pulse_start + pulse_period  # Recovery takes remaining 60%
        
        # Normalize pulse strength (pulses get progressively stronger)
        pulse_strength = 0.2 + 0.8 * (pulse_index / self.PULSE_COUNT)
        
        # No effect if we're not in this pulse's time window
        if elapsed_time < pulse_start or elapsed_time > recovery_end:
            return 0.0, 0.0
            
        # Calculate progress within this pulse
        if elapsed_time <= pulse_end:
            # Acceleration phase (outward)
            progress = (elapsed_time - pulse_start) / (pulse_end - pulse_start)
            # Use ease-out for smooth acceleration
            eased_progress = self._ease_out_cubic(progress)
            
            # Displacement grows with pulse progress
            displacement_factor = pulse_strength * eased_progress
            
            # Scale effect (grow slightly during pulse)
            scale_factor = 0.1 * pulse_strength * eased_progress
            
        else:
            # Recovery phase (return to center)
            progress = (elapsed_time - pulse_end) / (recovery_end - pulse_end)
            # Use ease-in for smooth deceleration
            eased_progress = self._ease_in_cubic(progress)
            
            # Displacement shrinks during recovery
            displacement_factor = pulse_strength * (1.0 - eased_progress)
            
            # Scale effect diminishes
            scale_factor = 0.1 * pulse_strength * (1.0 - eased_progress)
        
        return displacement_factor, scale_factor
    
    def _final_burst(self, elapsed_time: float) -> float:
        """
        Calculate the final burst effect progress.
        
        Args:
            elapsed_time (float): Current time in pulse phase
            
        Returns:
            float: Final burst progress (0.0-1.0)
        """
        pulse_period = self.PULSE_TIME / (self.PULSE_COUNT + 1)
        final_burst_start = self.PULSE_TIME - pulse_period
        
        # Not in final burst phase yet
        if elapsed_time < final_burst_start:
            return 0.0
            
        # Calculate progress of final burst
        progress = (elapsed_time - final_burst_start) / pulse_period
        
        # Ensure it doesn't exceed 1.0
        progress = min(1.0, progress)
        
        # Use ease-out for smooth acceleration
        return self._ease_out_back(progress)
    
    def update(self, elapsed_time: float):
        """
        Update animation state based on elapsed time.
        
        Args:
            elapsed_time (float): Time in seconds since the animation started
        """
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        for poster in self.posters_data:
            # Skip if not yet started due to delay
            if elapsed_time < poster['entry_delay']:
                continue
                
            # Mark poster as started
            poster['has_started'] = True
            
            # Phase 1: Entry - posters move toward center
            if elapsed_time <= self.GATHER_TIME:
                poster['phase'] = 'entry'
                
                # Calculate progress
                entry_time = elapsed_time - poster['entry_delay']
                entry_duration = self.GATHER_TIME - poster['entry_delay']
                entry_progress = min(1.0, entry_time / max(0.1, entry_duration))
                
                # Use ease-out for smooth arrival
                eased_progress = self._ease_out_cubic(entry_progress)
                
                # Move from starting position to center
                poster['current_x'] = poster['start_x'] + (poster['center_x'] - poster['start_x']) * eased_progress
                poster['current_y'] = poster['start_y'] + (poster['center_y'] - poster['start_y']) * eased_progress
                
                # Scale up as posters gather
                poster['current_scale'] = poster['start_scale'] + (poster['center_scale'] - poster['start_scale']) * eased_progress
                
                # Gradually align rotation
                target_rotation = 0
                poster['current_rotation'] = poster['start_rotation'] * (1 - eased_progress)
            
            # Phase 2: Pulses - posters pulse outward in waves
            elif elapsed_time <= self.GATHER_TIME + self.PULSE_TIME:
                poster['phase'] = 'pulse'
                
                # Calculate time in pulse phase
                pulse_time = elapsed_time - self.GATHER_TIME
                
                # Calculate final burst progress
                final_burst_progress = self._final_burst(pulse_time)
                
                if final_burst_progress > 0:
                    # Final burst - transition to grid
                    poster['current_x'] = poster['center_x'] + poster['vector_x'] * final_burst_progress
                    poster['current_y'] = poster['center_y'] + poster['vector_y'] * final_burst_progress
                    
                    # Scale up during final burst
                    scale_progress = self._ease_out_cubic(final_burst_progress)
                    poster['current_scale'] = poster['center_scale'] + (poster['final_scale'] - poster['center_scale']) * scale_progress
                    
                    # Store pulse factor for visualization
                    poster['pulse_factor'] = final_burst_progress
                else:
                    # Regular pulses
                    # Reset to center position first
                    poster['current_x'] = poster['center_x']
                    poster['current_y'] = poster['center_y']
                    poster['current_scale'] = poster['center_scale']
                    
                    # Calculate cumulative pulse effect
                    total_displacement = 0
                    total_scale = 0
                    active_pulse = False
                    
                    # Apply each pulse effect
                    for pulse_idx in range(self.PULSE_COUNT):
                        # Add slight offset for more natural movement
                        adjusted_time = pulse_time + poster['pulse_offset'] * 0.1
                        
                        # Get effect for this pulse
                        displacement, scale = self._pulse_function(
                            adjusted_time, pulse_idx, poster['distance'])
                        
                        if displacement > 0 or scale > 0:
                            active_pulse = True
                        
                        # Accumulate effects
                        total_displacement += displacement
                        total_scale += scale
                    
                    # Apply accumulated pulse effects
                    if active_pulse:
                        # Apply displacement in direction to final position
                        pulse_x = poster['direction_x'] * poster['distance'] * total_displacement
                        pulse_y = poster['direction_y'] * poster['distance'] * total_displacement
                        
                        poster['current_x'] += pulse_x
                        poster['current_y'] += pulse_y
                        
                        # Apply scale effect
                        poster['current_scale'] += total_scale
                        
                        # Store pulse factor for visualization
                        poster['pulse_factor'] = total_displacement
                    else:
                        poster['pulse_factor'] = 0
                
                # Add slight rotation during pulses for more dynamic feel
                if poster['pulse_factor'] > 0:
                    poster['current_rotation'] = 10 * math.sin(pulse_time * 5 + poster['index'] * 0.2) * poster['pulse_factor']
                else:
                    poster['current_rotation'] = 0
            
            # Phase 3: Settle - smooth transition to final grid
            elif elapsed_time <= self.GATHER_TIME + self.PULSE_TIME + self.SETTLE_TIME:
                poster['phase'] = 'settle'
                
                # Calculate progress
                settle_progress = (elapsed_time - self.GATHER_TIME - self.PULSE_TIME) / self.SETTLE_TIME
                settle_progress = min(1.0, settle_progress)
                
                # Use bounce effect for settling
                eased_progress = self._bounce_out(settle_progress)
                
                # Store position at the start of settle phase if not already set
                if 'burst_x' not in poster:
                    # Store the position from the end of the pulse phase
                    poster['burst_x'] = poster['current_x']
                    poster['burst_y'] = poster['current_y']
                    poster['burst_scale'] = poster['current_scale']
                
                # Move from burst position to final grid position
                poster['current_x'] = poster['burst_x'] + (poster['final_x'] - poster['burst_x']) * eased_progress
                poster['current_y'] = poster['burst_y'] + (poster['final_y'] - poster['burst_y']) * eased_progress
                
                # Scale to final size
                poster['current_scale'] = poster['burst_scale'] + (poster['final_scale'] - poster['burst_scale']) * eased_progress
                
                # Reduce rotation
                poster['current_rotation'] = poster['current_rotation'] * (1 - eased_progress)
                
                # Reset pulse factor
                poster['pulse_factor'] = 0
            
            # Phase 4: Final grid with subtle motion
            else:
                poster['phase'] = 'grid'
                
                # Add subtle motion in grid
                wobble_factor = 2
                time_scale = 1.5
                
                poster['current_x'] = poster['final_x'] + wobble_factor * math.sin(time_scale * elapsed_time + poster['index'] * 0.2)
                poster['current_y'] = poster['final_y'] + wobble_factor * math.cos(time_scale * elapsed_time + poster['index'] * 0.3)
                
                # Subtle scale pulsing
                pulse = 0.02 * math.sin(time_scale * elapsed_time + poster['index'] * 0.1)
                poster['current_scale'] = poster['final_scale'] + pulse
                
                # No rotation in final state
                poster['current_rotation'] = 0
                
                # Reset pulse factor
                poster['pulse_factor'] = 0
            
            # Apply fade effect for text overlay
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out function for smooth deceleration."""
        return 1 - math.pow(1 - t, 3)
    
    def _ease_in_cubic(self, t: float) -> float:
        """Cubic ease-in function for smooth acceleration."""
        return t * t * t
    
    def _bounce_out(self, t: float) -> float:
        """Bounce-out easing function for settling effect."""
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    
    def _ease_out_back(self, t: float) -> float:
        """Back ease-out function with slight overshoot for dynamic feel."""
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
        
        # Calculate center
        center_x = WIDTH / 2
        center_y = HEIGHT / 2
        
        # Sort posters for proper layering
        def sorting_key(p):
            if not p.get('has_started', False):
                return (-1000, 0, 0)  # Don't render
                
            if p['phase'] == 'entry':
                # Sort by distance from center during entry
                dx = p['current_x'] - center_x
                dy = p['current_y'] - center_y
                distance = math.sqrt(dx**2 + dy**2)
                return (1, distance, p['index'])
            elif p['phase'] == 'pulse':
                # During pulse, items further from center draw first
                dx = p['current_x'] - center_x
                dy = p['current_y'] - center_y
                distance = math.sqrt(dx**2 + dy**2)
                # Invert distance so items further from center render first
                return (2, -distance, p['index'])
            else:  # settle and grid phases
                # Sort by row and column during grid phase
                return (3, p['grid_row'], p['grid_col'])
        
        sorted_posters = sorted(self.posters_data, key=sorting_key)
        
        # Check if any posters are in pulse phase
        pulse_phase_active = False
        max_pulse_factor = 0
        
        for poster in self.posters_data:
            if poster.get('has_started', False) and poster.get('phase') == 'pulse':
                pulse_phase_active = True
                max_pulse_factor = max(max_pulse_factor, poster.get('pulse_factor', 0))
        
        # Draw pulse effect visualization before posters
        if pulse_phase_active and max_pulse_factor > 0:
            # Create pulse visualization surface with proper alpha
            pulse_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            
            # Calculate pulse radius based on maximum pulse factor
            pulse_radius = max(1, int(min(WIDTH, HEIGHT) * 0.5 * max_pulse_factor))
            
            # Instead of drawing rings with outlines, create a radial gradient effect
            # Draw filled circles from largest to smallest with decreasing opacity
            num_circles = 5
            for i in range(num_circles, 0, -1):
                # Calculate radius for this circle
                circle_radius = int(pulse_radius * (i / num_circles))
                
                # Calculate color with alpha
                # Use higher alpha for inner circles, lower for outer circles
                alpha = int(30 * (i / num_circles) * max_pulse_factor)  # Much lower alpha, max of 30
                color = (200, 220, 255, alpha)  # Light blue glow with lower alpha
                
                # Draw filled circle instead of outline
                pygame.draw.circle(pulse_surface, color, (center_x, center_y), circle_radius)
            
            # Apply the pulse visualization
            surface.blit(pulse_surface, (0, 0))
        
        # Draw each poster
        for poster in sorted_posters:
            # Skip posters that haven't started animation yet
            if not poster.get('has_started', False):
                continue
                
            # Get the original poster
            img = poster['poster']
            
            # Scale the poster
            try:
                width = max(1, int(img.get_width() * poster['current_scale']))
                height = max(1, int(img.get_height() * poster['current_scale']))
                
                # Convert to alpha mode before scaling to preserve transparency
                if img.get_alpha() is None:
                    alpha_img = img.convert_alpha()
                else:
                    alpha_img = img.copy()
                
                scaled_img = pygame.transform.smoothscale(alpha_img, (width, height))
            except pygame.error:
                # Fallback - make a copy with alpha if possible
                try:
                    scaled_img = img.copy()
                    if scaled_img.get_alpha() is None:
                        scaled_img = scaled_img.convert_alpha()
                except:
                    scaled_img = img
            
            # Rotate if needed
            if abs(poster['current_rotation']) > 0.5:
                try:
                    # Create a copy with per-pixel alpha to preserve transparency during rotation
                    if scaled_img.get_alpha() is None:
                        alpha_img = scaled_img.convert_alpha()
                    else:
                        alpha_img = scaled_img.copy()
                    
                    # Rotate with preserved transparency
                    rotated_img = pygame.transform.rotate(alpha_img, poster['current_rotation'])
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
            
            # Apply glow effect during pulse phase
            if poster.get('phase') == 'pulse' and poster.get('pulse_factor', 0) > 0.1:
                try:
                    # Get dimensions of the current image
                    img_width, img_height = rotated_img.get_width(), rotated_img.get_height()
                    
                    # Create a glowing copy with proper alpha
                    glow_size = 10
                    glow_img = pygame.Surface((
                        img_width + glow_size*2,
                        img_height + glow_size*2
                    ), pygame.SRCALPHA)
                    
                    # Draw a soft glow around the poster using filled shapes instead of outlines
                    glow_alpha = int(100 * poster['pulse_factor'])
                    
                    # Use a series of filled rectangles with rounded corners and decreasing alpha
                    # to create a soft glow effect that respects transparency
                    for i in range(glow_size, 0, -2):
                        alpha = glow_alpha * (i / glow_size)
                        # Create a rounded rectangle by filling it
                        pygame.draw.rect(
                            glow_img, 
                            (200, 220, 255, int(alpha)),
                            (
                                glow_size - i//2,
                                glow_size - i//2,
                                img_width + i,
                                img_height + i
                            ),
                            0,  # Fill the shape instead of drawing an outline
                            border_radius=8
                        )
                    
                    # Draw the actual poster in the center of the glow with full alpha
                    glow_img.blit(rotated_img, (glow_size, glow_size))
                    rotated_img = glow_img
                except pygame.error:
                    pass
            
            # Calculate position (centered)
            rect = rotated_img.get_rect()
            rect.center = (int(poster['current_x']), int(poster['current_y']))
            
            # Draw to surface
            surface.blit(rotated_img, rect)
