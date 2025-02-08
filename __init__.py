bl_info = {
    "name": "Dust Speck",
    "blender": (4, 1, 1),
    "category": "3D View",
    "location": "View3D > Menu > View > Sidebar",
    "description": "Procedural planet generation tool",
    "author": "Jean-Louis Voiseux",
    "version": (1, 0, 2),
}

from . import script

def register():
    script.register()

def unregister():
    script.unregister()

if __name__ == "__main__":
    register()