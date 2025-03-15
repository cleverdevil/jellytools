"""
Vortex animation for the library card generator.
Posters swirl from the edges of the screen toward the center then expand outward into a grid.
"""
import math
import random
import pygame
import logging
from typing import List, Dict, Any

from jellytools.animations.base import BaseAnimation, WIDTH, HEIGHT

logger = logging.getLogger(__name__)


class PosterVortexAnimation(BaseAnimation):
    """Animation that creates a swirling vortex of posters that expands into a grid"""
    
    def __init__(self, library_name: str, posters: List[pygame.Surface]):
        """
        Initialize vortex animation.
        
        Args:
            library_name (str): Name of the library to display
            posters (List[pygame.Surface]): List of poster images to animate
        """
        super().__init__(library_name, posters)
        
        # Animation timing constants
        self.INTRO_TIME = 0.5        # Time for initial rapid entrance (0-0.5s)
        self.VORTEX_TIME = 2.0       # Time for posters to swirl inward (0.5-2.5s)
        self.EXPAND_TIME = 2.0       # Time for vortex to expand to grid (2.5-4.5s)
        self.FADE_START = 4.5        # When to start fading (4.5s)
        self.TEXT_START_TIME = 4.5   # When to show text (4.5s)
        
        # Calculate grid parameters for final layout
        self.grid_params = self._calculate_grid_params(posters)
        
        # Initialize poster data
        self.posters_data = self._initialize_posters(posters)
        
        # Debug
        logger.info(f"Initialized vortex animation with {len(self.posters_data)} posters")
    
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
        spacing = 25  # Space between posters
        cell_width = int(poster_width * scale_factor) + spacing
        cell_height = int(poster_height * scale_factor) + spacing
        
        # Calculate grid dimensions - use golden ratio for aesthetics
        golden_ratio = 1.618
        base_cols = 9  # Base number of columns
        
        cols = base_cols
        rows = int(base_cols / golden_ratio) + 2  # Add extra rows for coverage
        
        # Calculate total grid dimensions
        grid_width = cols * cell_width
        grid_height = rows * cell_height
        
        # Center the grid
        grid_origin_x = (WIDTH - grid_width) / 2
        grid_origin_y = (HEIGHT - grid_height) / 2
        
        logger.info(f"Vortex final grid: {cols}x{rows}, origin: ({grid_origin_x}, {grid_origin_y})")
        
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
        
        # Create spiral pattern for posters
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
            
            # Calculate vortex center position
            vortex_center_x = WIDTH / 2
            vortex_center_y = HEIGHT / 2
            
            # Use golden angle for natural looking distribution
            golden_angle = math.pi * (3 - math.sqrt(5))  # ~137.5 degrees
            angle = i * golden_angle
            
            # Calculate multiple intermediate positions for more dynamic motion
            # 1. Starting position - evenly distributed around the screen edges
            edge_distance = random.uniform(1.1, 1.3)
            radius = max(WIDTH, HEIGHT) * edge_distance / 2
            
            # Randomize starting position on screen edge
            edge_choice = random.randint(0, 3)  # 0=top, 1=right, 2=bottom, 3=left
            
            if edge_choice == 0:  # Top
                start_x = random.uniform(0, WIDTH)
                start_y = -50 - random.uniform(0, 100)
            elif edge_choice == 1:  # Right
                start_x = WIDTH + 50 + random.uniform(0, 100)
                start_y = random.uniform(0, HEIGHT)
            elif edge_choice == 2:  # Bottom
                start_x = random.uniform(0, WIDTH)
                start_y = HEIGHT + 50 + random.uniform(0, 100)
            else:  # Left
                start_x = -50 - random.uniform(0, 100)
                start_y = random.uniform(0, HEIGHT)
                
            # 2. First intermediate position - moving toward screen center
            # Position somewhere between edge and center
            t1 = random.uniform(0.3, 0.5)  # Position 30-50% of the way to center
            intermediate1_x = start_x + (vortex_center_x - start_x) * t1
            intermediate1_y = start_y + (vortex_center_y - start_y) * t1
            
            # Add some random deviation for more natural movement
            deviation = 100
            intermediate1_x += random.uniform(-deviation, deviation)
            intermediate1_y += random.uniform(-deviation, deviation)
            
            # 3. Second intermediate position - joining the vortex
            # Distribute in circular ring around center
            ring_radius = 150 + random.uniform(-30, 30)  # Randomize a bit
            intermediate2_x = vortex_center_x + ring_radius * math.cos(angle)
            intermediate2_y = vortex_center_y + ring_radius * math.sin(angle)
            
            # 4. Tight vortex position
            # Position in tight spiral formation
            spiral_index = i % 20  # Group in 20s for layering
            spiral_radius = 30 + spiral_index * 4  # Tighter spiral
            vortex_x = vortex_center_x + spiral_radius * math.cos(angle)
            vortex_y = vortex_center_y + spiral_radius * math.sin(angle)
            
            # Scale factors for animation
            start_scale = random.uniform(0.3, 0.6)       # More visible start size
            intermediate1_scale = random.uniform(0.5, 0.8)  # Growing as it moves
            intermediate2_scale = random.uniform(0.6, 0.9)  # Further growth
            vortex_scale = random.uniform(0.7, 0.9)      # Medium at vortex center
            final_scale = self.grid_params['scale_factor']  # Full size in grid
            
            # Create poster data
            poster_data = {
                'poster': poster,
                'start_x': start_x,
                'start_y': start_y,
                'intermediate1_x': intermediate1_x,
                'intermediate1_y': intermediate1_y,
                'intermediate2_x': intermediate2_x,
                'intermediate2_y': intermediate2_y,
                'vortex_x': vortex_x,
                'vortex_y': vortex_y,
                'final_x': final_x,
                'final_y': final_y,
                'current_x': start_x,
                'current_y': start_y,
                'start_scale': start_scale,
                'intermediate1_scale': intermediate1_scale,
                'intermediate2_scale': intermediate2_scale,
                'vortex_scale': vortex_scale,
                'final_scale': final_scale,
                'current_scale': start_scale,
                'angle': angle,               # Initial angle in the spiral
                'radius': spiral_radius,      # Radius in the spiral
                'start_rotation': random.uniform(-180, 180),  # Initial rotation
                'current_rotation': random.uniform(-180, 180),
                'opacity': 255,
                'entry_delay': random.uniform(0, self.INTRO_TIME * 0.8),  # Staggered entry
                'index': i,
                'row': row,  # Ensure row is always defined
                'col': col,  # Ensure col is always defined
                'phase': 'intro',  # Phases: intro -> path1 -> path2 -> vortex -> expanding -> grid
                'has_started': False  # Flag to track if poster animation has started
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
            # Skip if poster hasn't started yet
            if elapsed_time < poster['entry_delay']:
                continue
                
            # Mark this poster as started
            poster['has_started'] = True
                
            # Phase 1: Rapid entrance from edges
            if elapsed_time <= self.INTRO_TIME + poster['entry_delay']:
                poster['phase'] = 'intro'
                
                # Calculate intro progress
                intro_progress = (elapsed_time - poster['entry_delay']) / self.INTRO_TIME
                intro_progress = min(1.0, intro_progress)
                
                # Use ease-out for quick initial movement
                eased_progress = self._ease_out_cubic(intro_progress)
                
                # Update position - from start to first intermediate position
                poster['current_x'] = poster['start_x'] + (poster['intermediate1_x'] - poster['start_x']) * eased_progress
                poster['current_y'] = poster['start_y'] + (poster['intermediate1_y'] - poster['start_y']) * eased_progress
                
                # Update scale
                poster['current_scale'] = poster['start_scale'] + (poster['intermediate1_scale'] - poster['start_scale']) * eased_progress
                
                # Update rotation - start spinning
                poster['current_rotation'] = poster['start_rotation'] + 360 * intro_progress
            
            # Phase 2: Move toward vortex formation (first path segment)
            elif elapsed_time <= self.INTRO_TIME + self.VORTEX_TIME * 0.4:
                poster['phase'] = 'path1'
                
                # Calculate path progress
                path_time = self.VORTEX_TIME * 0.4
                path_progress = (elapsed_time - self.INTRO_TIME - poster['entry_delay']) / path_time
                path_progress = min(1.0, path_progress)
                
                # Use smooth easing for natural movement
                eased_progress = self._ease_in_out_cubic(path_progress)
                
                # Update position - from first intermediate to second intermediate
                poster['current_x'] = poster['intermediate1_x'] + (poster['intermediate2_x'] - poster['intermediate1_x']) * eased_progress
                poster['current_y'] = poster['intermediate1_y'] + (poster['intermediate2_y'] - poster['intermediate1_y']) * eased_progress
                
                # Update scale - grow slightly
                poster['current_scale'] = poster['intermediate1_scale'] + (poster['intermediate2_scale'] - poster['intermediate1_scale']) * eased_progress
                
                # Update rotation - continue spinning but slowing
                spin_speed = 360 * (1 - eased_progress * 0.3)
                poster['current_rotation'] += spin_speed * 0.05
            
            # Phase 3: Form the tight vortex (second path segment)
            elif elapsed_time <= self.INTRO_TIME + self.VORTEX_TIME:
                poster['phase'] = 'path2'
                
                # Calculate vortex progress
                vortex_time = self.VORTEX_TIME * 0.6
                vortex_progress = (elapsed_time - self.INTRO_TIME - self.VORTEX_TIME * 0.4 - poster['entry_delay']) / vortex_time
                vortex_progress = min(1.0, vortex_progress)
                
                # Use elastic easing for more dynamic motion
                eased_progress = self._elastic_ease_in_out(vortex_progress)
                
                # Update position - from second intermediate to tight vortex position
                poster['current_x'] = poster['intermediate2_x'] + (poster['vortex_x'] - poster['intermediate2_x']) * eased_progress
                poster['current_y'] = poster['intermediate2_y'] + (poster['vortex_y'] - poster['intermediate2_y']) * eased_progress
                
                # Update scale
                poster['current_scale'] = poster['intermediate2_scale'] + (poster['vortex_scale'] - poster['intermediate2_scale']) * eased_progress
                
                # Update rotation - dramatic spinning as entering vortex
                spin_factor = math.sin(vortex_progress * math.pi) * 20  # Peak in the middle, slow at start/end
                poster['current_rotation'] += spin_factor
            
            # Phase 4: Expand from vortex to grid
            elif elapsed_time <= self.INTRO_TIME + self.VORTEX_TIME + self.EXPAND_TIME:
                poster['phase'] = 'expanding'
                
                # Calculate expansion progress
                expand_progress = (elapsed_time - self.INTRO_TIME - self.VORTEX_TIME) / self.EXPAND_TIME
                expand_progress = min(1.0, expand_progress)
                
                # Use bounce effect for expansion
                eased_progress = self._bounce_out(expand_progress)
                
                # Update position - from vortex to final position
                poster['current_x'] = poster['vortex_x'] + (poster['final_x'] - poster['vortex_x']) * eased_progress
                poster['current_y'] = poster['vortex_y'] + (poster['final_y'] - poster['vortex_y']) * eased_progress
                
                # Update scale - grow to final size
                poster['current_scale'] = poster['vortex_scale'] + (poster['final_scale'] - poster['vortex_scale']) * eased_progress
                
                # Update rotation - gradually stop spinning
                final_rotation = 0
                spin_reduction = 1 - eased_progress
                spin_amount = 360 * spin_reduction
                poster['current_rotation'] = spin_amount * math.sin(poster['angle'] + elapsed_time)
            
            # Final phase: Grid with subtle motion
            else:
                poster['phase'] = 'grid'
                
                # Final position with subtle movement
                wobble_factor = 3
                time_scale = 1.5
                
                poster['current_x'] = poster['final_x'] + wobble_factor * math.sin(time_scale * elapsed_time + poster['index'] * 0.2)
                poster['current_y'] = poster['final_y'] + wobble_factor * math.cos(time_scale * elapsed_time + poster['index'] * 0.3)
                
                # Final scale with subtle pulsing
                pulse = 0.03 * math.sin(time_scale * elapsed_time + poster['index'] * 0.1)
                poster['current_scale'] = poster['final_scale'] + pulse
                
                # No rotation in final state
                poster['current_rotation'] = 0
            
            # Apply fade effect for text overlay
            if elapsed_time > self.FADE_START:
                fade_progress = (elapsed_time - self.FADE_START) / (self.duration - self.FADE_START)
                fade_progress = min(1.0, fade_progress)
                poster['opacity'] = 255 - (255 - 51) * fade_progress  # Fade to 20% opacity
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """
        Cubic ease-in-out function for smooth acceleration/deceleration.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - math.pow(-2 * t + 2, 3) / 2
    
    def _ease_out_cubic(self, t: float) -> float:
        """
        Cubic ease-out function for smooth deceleration.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        return 1 - math.pow(1 - t, 3)
    
    def _elastic_ease_in_out(self, t: float) -> float:
        """
        Elastic ease-in-out function for dynamic bouncy effect.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
        if t == 0 or t == 1:
            return t
            
        if t < 0.5:
            return -(math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2
        else:
            return (math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2 + 1
    
    def _bounce_out(self, t: float) -> float:
        """
        Bounce-out easing function for expansion phase.
        
        Args:
            t (float): Progress from 0.0 to 1.0
            
        Returns:
            float: Eased progress value
        """
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
    
    def draw(self, surface: pygame.Surface):
        """
        Draw current animation frame to the surface.
        
        Args:
            surface (pygame.Surface): Surface to draw on
        """
        # Fill background with black
        surface.fill((0, 0, 0))
        
        # Sort posters for proper layering based on their phase
        def sorting_key(p):
            # During intro and path phases, sort by distance from center
            if p['phase'] in ['intro', 'path1', 'path2']:
                center_x, center_y = WIDTH / 2, HEIGHT / 2
                distance = math.sqrt((p['current_x'] - center_x)**2 + (p['current_y'] - center_y)**2)
                # Scale factors for different phases
                if p['phase'] == 'intro':
                    # More distant objects first during intro
                    return distance
                elif p['phase'] == 'path1':
                    # Mix of distance and index
                    return distance * 0.8 + p['index'] * 0.2
                else:  # path2
                    # More index-based as they form vortex
                    return distance * 0.3 + p['index'] * 0.7
            elif p['phase'] == 'expanding':
                # In expanding phase, sort by distance from center and index
                center_x, center_y = WIDTH / 2, HEIGHT / 2
                distance = math.sqrt((p['current_x'] - center_x)**2 + (p['current_y'] - center_y)**2)
                return distance * 0.5 + p['index'] * 0.5
            else:  # grid phase
                # In grid phase, sort by row and column for consistent layering
                if 'row' in p and 'col' in p:
                    return p['row'] * 1000 + p['col']
                else:
                    # Fallback if row/col not available
                    return p.get('index', 0)
        
        # Apply sorting
        sorted_posters = sorted(self.posters_data, key=sorting_key)
        
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
            
            # Add motion blur effect for fast-moving posters
            if poster['phase'] in ['intro', 'path1']:
                # Calculate motion vector
                if poster['phase'] == 'intro':
                    from_x, from_y = poster['start_x'], poster['start_y']
                    to_x, to_y = poster['intermediate1_x'], poster['intermediate1_y']
                else:
                    from_x, from_y = poster['intermediate1_x'], poster['intermediate1_y']
                    to_x, to_y = poster['intermediate2_x'], poster['intermediate2_y']
                
                # Direction of motion
                dx = to_x - from_x
                dy = to_y - from_y
                
                # Only add blur if there's significant motion
                motion_magnitude = math.sqrt(dx*dx + dy*dy)
                if motion_magnitude > 50:
                    # Create motion blur with fading trails (up to 5 copies)
                    num_trails = 5
                    for i in range(num_trails):
                        # Calculate trail position (each progressively further back)
                        trail_factor = (i + 1) / (num_trails + 1)  # 1/6, 2/6, 3/6, 4/6, 5/6
                        trail_x = int(poster['current_x'] - dx * trail_factor * 0.2)
                        trail_y = int(poster['current_y'] - dy * trail_factor * 0.2)
                        
                        # Create fading trail image
                        trail_alpha = 100 - i * 20  # 100, 80, 60, 40, 20
                        try:
                            trail_img = rotated_img.copy()
                            trail_img.set_alpha(trail_alpha)
                            
                            # Draw trail
                            trail_rect = trail_img.get_rect()
                            trail_rect.center = (trail_x, trail_y)
                            surface.blit(trail_img, trail_rect)
                        except pygame.error:
                            pass
            
            # Draw the poster
            surface.blit(rotated_img, rect)
