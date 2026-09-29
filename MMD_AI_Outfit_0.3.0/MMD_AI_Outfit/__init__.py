bl_info = {
    "name": "MMD AI Outfit",
    "author": "MMD AI Outfit Project",
    "version": (0, 3, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > MMD AI Outfit",
    "description": "Build MMD Character Profiles and measure body shape",
    "category": "MMD",
}

from .ui.panel import register, unregister
