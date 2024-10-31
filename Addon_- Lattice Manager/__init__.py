# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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

classes = (
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