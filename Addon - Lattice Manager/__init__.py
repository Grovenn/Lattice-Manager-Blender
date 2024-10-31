import bpy

bl_info = {
    "name": "Lattice Manager",
    "author": "Zach Wells",
    "description": "",
    "blender": (4, 10, 0),
    "location": "View3D",
    "warning": "",
    "category": "Generic"
}

classes = (
)

register, unregister = bpy.utils.register_classes_factory(classes)
