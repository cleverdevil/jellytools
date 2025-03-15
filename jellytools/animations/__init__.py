"""Animation modules for library card generation."""

from jellytools.animations.base import AnimationManager, BaseAnimation
from jellytools.animations.grid import PosterGridAnimation
from jellytools.animations.spiral import PosterSpinAnimation
from jellytools.animations.waterfall import PosterWaterfallAnimation

__all__ = [
    "AnimationManager",
    "BaseAnimation",
    "PosterGridAnimation",
    "PosterSpinAnimation",
    "PosterWaterfallAnimation"
]
