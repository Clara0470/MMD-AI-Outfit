bl_info = {
    "name": "MMD AI Outfit",
    "author": "MMD AI Outfit Project",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > MMD AI Outfit",
    "description": "Register an MMD character and measure its body proportions",
    "category": "MMD",
}

from .ui.panel import register, unregister
