# Animation utilities for Asimov

import math
from typing import Any, Dict, Tuple

# Linear interpolation
def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between start and end by t (0-1)."""
    return start + t * (end - start)

def smooth_step(t: float) -> float:
    """Smoothstep easing function (cubic Hermite interpolation)."""
    return t * t * (3 - 2 * t)

def ease_in_out(t: float) -> float:
    """Ease-in-out cubic interpolation."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2

def rotate_vertex(x: float, y: float, angle_deg: float) -> Tuple[float, float]:
    """Rotate a 2D point around origin by angle in degrees."""
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return (
        x * cos_t - y * sin_t,
        x * sin_t + y * cos_t
    )

def bounce_animation_update(
    state: Dict[str, Any],
    quad_size: float = 0.5,
) -> Dict[str, float]:
    """
    Update bounce animation state.
    
    State dict should contain:
    - x, y, z, angle: current position/angle
    - vel_x, vel_y, vel_z, vel_angle: velocities
    - x_range, y_range, z_range, angle_range: bounds
    
    Returns updated position dict with x, y, z, angle.
    """
    x_min = state['x_range'][0] + quad_size
    x_max = state['x_range'][1] - quad_size
    y_min = state['y_range'][0] + quad_size
    y_max = state['y_range'][1] - quad_size
    
    next_x = state['x'] + state.get('vel_x', 0)
    next_y = state['y'] + state.get('vel_y', 0)
    next_angle = state['angle'] + state.get('vel_angle', 0)
    
    if next_x <= x_min:
        state['vel_x'] = abs(state.get('vel_x', 0))
    elif next_x >= x_max:
        state['vel_x'] = -abs(state.get('vel_x', 0))
    
    if next_y <= y_min:
        state['vel_y'] = abs(state.get('vel_y', 0))
    elif next_y >= y_max:
        state['vel_y'] = -abs(state.get('vel_y', 0))
    
    angle_range = state.get('angle_range', (-180, 180))
    if next_angle <= angle_range[0]:
        state['vel_angle'] = abs(state.get('vel_angle', 0))
    elif next_angle >= angle_range[1]:
        state['vel_angle'] = -abs(state.get('vel_angle', 0))
    
    state['x'] += state.get('vel_x', 0)
    state['y'] += state.get('vel_y', 0)
    state['z'] += state.get('vel_z', 0)
    state['angle'] += state.get('vel_angle', 0)
    
    return {
        'x': state['x'],
        'y': state['y'],
        'z': state['z'],
        'angle': state['angle'],
    }

def create_bounce_state(
    x_range: Tuple[float, float] = (-0.9, 0.9),
    y_range: Tuple[float, float] = (-0.9, 0.9),
    z_range: Tuple[float, float] = (-0.3, 0.0),
    angle_range: Tuple[float, float] = (-15, 15),
    vel_x: float = 0.005,
    vel_y: float = 0.005,
    vel_z: float = 0.0,
    vel_angle: float = 0.1,
) -> Dict[str, Any]:
    """Create initial bounce animation state."""
    return {
        'x': 0.0,
        'y': 0.0,
        'z': 0.0,
        'angle': 0.0,
        'vel_x': vel_x,
        'vel_y': vel_y,
        'vel_z': vel_z,
        'vel_angle': vel_angle,
        'x_range': x_range,
        'y_range': y_range,
        'z_range': z_range,
        'angle_range': angle_range,
    }
