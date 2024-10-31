bl_info = {
    "name": "Lattice Manager",
    "author": "Zach Wells",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

import bpy
from .lattice_manager_v01 import (
    LatticeManagerProperties,
    ManagedObject,
    LatticeData,
    OBJECT_PT_LatticeManager,
    OBJECT_OT_LatticeManageSelected,
    OBJECT_OT_LatticeUnmanageAll,
    OBJECT_OT_LatticeAddToAll,
    OBJECT_OT_LatticeAddToSelected,
    OBJECT_OT_ToggleLatticeVisibility,
    OBJECT_OT_SelectObjectsWithModifier,
    OBJECT_OT_DeselectObjectsWithModifier,
    OBJECT_OT_ApplyLatticeModifier,
    OBJECT_OT_DeleteLatticeModifier,
)

# Ensure ManagedObject includes lattice_modifiers property
class ManagedObject(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty()
    lattice_modifiers: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)

classes = (
    LatticeData,
    LatticeManagerProperties,
    ManagedObject,
    OBJECT_PT_LatticeManager,
    OBJECT_OT_LatticeManageSelected,
    OBJECT_OT_LatticeUnmanageAll,
    OBJECT_OT_LatticeAddToAll,
    OBJECT_OT_LatticeAddToSelected,
    OBJECT_OT_ToggleLatticeVisibility,
    OBJECT_OT_SelectObjectsWithModifier,
    OBJECT_OT_DeselectObjectsWithModifier,
    OBJECT_OT_ApplyLatticeModifier,
    OBJECT_OT_DeleteLatticeModifier,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lattice_manager_props = bpy.props.PointerProperty(type=LatticeManagerProperties)
    bpy.types.Scene.managed_objects = bpy.props.CollectionProperty(type=ManagedObject)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lattice_manager_props
    del bpy.types.Scene.managed_objects