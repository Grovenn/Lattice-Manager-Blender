import bpy
from mathutils import Vector

bl_info = {
    "name": "Lattice Manager",
    "blender": (4, 1, 0),
    "category": "Object",
}


# Properties for managing objects
class LatticeManagerProperties(bpy.types.PropertyGroup):
    is_managing: bpy.props.BoolProperty(default=False)
    use_existing_lattice: bpy.props.BoolProperty(
        name="Use Existing Lattice",
        description="Use an existing lattice object for the modifier",
        default=False,
    )
    lattice_object: bpy.props.PointerProperty(
        name="Lattice Object",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'LATTICE',
    )
    lattice_count: bpy.props.IntProperty(
        name="Lattice Count",
        default=0,
        description="Tracks the number of lattices created by the addon",
    )


# Collection Property to Store Managed Objects
class ManagedObject(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty()


# Panel UI
class OBJECT_PT_LatticeManager(bpy.types.Panel):
    bl_label = "Lattice Manager"
    bl_idname = "OBJECT_PT_lattice_manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout
        props = context.scene.lattice_manager_props

        if not props.is_managing:
            layout.operator("object.lattice_manage_selected", text="Manage Selected Objects")
        else:
            layout.operator("object.lattice_unmanage_all", text="Unmanage All")
            layout.prop(props, "use_existing_lattice")
            if props.use_existing_lattice:
                layout.prop_search(props, "lattice_object", context.scene, "objects")

            row = layout.row(align=True)
            row.operator("object.lattice_add_to_all", text="Add Lattice to All")
            row.operator("object.lattice_add_to_selected", text="Add Lattice to Selected")

            # Display lattice modifiers in managed objects
            self.draw_lattice_modifiers(context, layout)

    def draw_lattice_modifiers(self, context, layout):
        lattice_modifiers = gather_lattice_modifiers(context)
        if lattice_modifiers:
            layout.label(text="Lattice Modifiers:")
            for lattice_name, data in lattice_modifiers.items():
                box = layout.box()

                # Draw lattice name
                row = box.row(align=True)
                row.label(text=lattice_name)

                # Visibility toggle button
                visibility_icon = 'HIDE_OFF' if data["visible"] else 'HIDE_ON'
                op = row.operator("object.toggle_lattice_visibility", text="", icon=visibility_icon, emboss=False)
                op.lattice_name = data["lattice_object"].name

                # Action buttons: Select/Deselect
                row = box.row(align=True)
                select_op = row.operator("object.select_objects_with_modifier", text="Select Objects")
                select_op.modifier_name = lattice_name

                deselect_op = row.operator("object.deselect_objects_with_modifier", text="Deselect Objects")
                deselect_op.modifier_name = lattice_name

                # Action buttons: Apply/Delete
                row = box.row(align=True)
                apply_op = row.operator("object.apply_lattice_modifier", text="Apply Lattice Modifiers")
                apply_op.modifier_name = lattice_name

                delete_op = row.operator("object.delete_lattice_modifier", text="Delete Lattice Modifiers")
                delete_op.modifier_name = lattice_name

                # Strength slider
                row = box.row()
                row.prop(data["strength_modifier"], "strength", text="Strength", slider=True)


# Operators
class OBJECT_OT_LatticeManageSelected(bpy.types.Operator):
    bl_idname = "object.lattice_manage_selected"
    bl_label = "Manage Selected Objects"

    def execute(self, context):
        props = context.scene.lattice_manager_props
        props.is_managing = True

        # Clear previous managed objects
        context.scene.managed_objects.clear()

        # Add selected objects to managed list
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                item = context.scene.managed_objects.add()
                item.object_name = obj.name

        self.report({'INFO'}, "Managed selected objects.")
        return {'FINISHED'}


class OBJECT_OT_LatticeUnmanageAll(bpy.types.Operator):
    bl_idname = "object.lattice_unmanage_all"
    bl_label = "Unmanage All Managed Objects"

    def execute(self, context):
        props = context.scene.lattice_manager_props
        props.is_managing = False
        context.scene.managed_objects.clear()
        self.report({'INFO'}, "Unmanaged all objects.")
        return {'FINISHED'}


class OBJECT_OT_LatticeAddToAll(bpy.types.Operator):
    bl_idname = "object.lattice_add_to_all"
    bl_label = "Add Lattice to All"

    def execute(self, context):
        self.add_lattice(context, manage_all=True)
        return {'FINISHED'}


class OBJECT_OT_LatticeAddToSelected(bpy.types.Operator):
    bl_idname = "object.lattice_add_to_selected"
    bl_label = "Add Lattice to Selected"

    def execute(self, context):
        self.add_lattice(context, manage_all=False)
        return {'FINISHED'}

    def add_lattice(self, context, manage_all):
        props = context.scene.lattice_manager_props
        if manage_all:
            objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                       item.object_name in context.scene.objects]
        else:
            objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        # Check if we should use an existing lattice
        if props.use_existing_lattice and props.lattice_object:
            lattice = props.lattice_object
            modifier_name = lattice.name
        else:
            # Calculate bounding box and create new lattice
            min_coords, max_coords = self.calculate_bounding_box(objects)
            lattice = self.create_and_position_lattice(context, min_coords, max_coords)

            # Increment lattice count and rename lattice object
            props.lattice_count += 1
            lattice.name = f"Lattice {props.lattice_count}"
            modifier_name = lattice.name

            # Move the lattice to a "Lattices" collection in the Scene Collection
            lattice_collection = bpy.data.collections.get("Lattices")
            if not lattice_collection:
                lattice_collection = bpy.data.collections.new("Lattices")
                context.scene.collection.children.link(lattice_collection)

            # Ensure lattice is only linked to "Lattices" collection
            for col in lattice.users_collection:
                col.objects.unlink(lattice)
            lattice_collection.objects.link(lattice)

        # Add lattice modifier to all selected or managed objects
        for obj in objects:
            mod = obj.modifiers.new(name=modifier_name, type='LATTICE')
            mod.object = lattice

    def calculate_bounding_box(self, objects):
        # Start with the bounding box of the first object
        min_coords = Vector((float('inf'), float('inf'), float('inf')))
        max_coords = Vector((float('-inf'), float('-inf'), float('-inf')))

        for obj in objects:
            for vertex in obj.bound_box:
                world_vertex = obj.matrix_world @ Vector(vertex)
                min_coords = Vector((min(min_coords[i], world_vertex[i]) for i in range(3)))
                max_coords = Vector((max(max_coords[i], world_vertex[i]) for i in range(3)))

        return min_coords, max_coords

    def create_and_position_lattice(self, context, min_coords, max_coords):
        # Create a new lattice object
        lattice_data = bpy.data.lattices.new("Lattice")
        lattice = bpy.data.objects.new("Lattice", lattice_data)

        # Position the lattice at the center of the bounding box
        lattice.location = (min_coords + max_coords) / 2

        # Set the dimensions of the lattice to fit the bounding box with a scaling factor of 2
        lattice.scale = (max_coords - min_coords) / 2 * 2  # Scaling up by a factor of 2

        return lattice


class OBJECT_OT_ToggleLatticeVisibility(bpy.types.Operator):
    bl_idname = "object.toggle_lattice_visibility"
    bl_label = "Toggle Lattice Visibility"

    lattice_name: bpy.props.StringProperty()

    def execute(self, context):
        lattice_object = bpy.data.objects.get(self.lattice_name)
        if lattice_object:
            lattice_object.hide_viewport = not lattice_object.hide_viewport
            self.report({'INFO'}, f"Toggled visibility of lattice '{self.lattice_name}'.")
        return {'FINISHED'}


class OBJECT_OT_SelectObjectsWithModifier(bpy.types.Operator):
    bl_idname = "object.select_objects_with_modifier"
    bl_label = "Select Objects with Modifier"

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH' and self.modifier_name in obj.modifiers:
                obj.select_set(True)
        self.report({'INFO'}, f"Selected objects with modifier '{self.modifier_name}'.")
        return {'FINISHED'}


class OBJECT_OT_DeselectObjectsWithModifier(bpy.types.Operator):
    bl_idname = "object.deselect_objects_with_modifier"
    bl_label = "Deselect Objects with Modifier"

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH' and self.modifier_name in obj.modifiers:
                obj.select_set(False)
        self.report({'INFO'}, f"Deselected objects with modifier '{self.modifier_name}'.")
        return {'FINISHED'}


class OBJECT_OT_ApplyLatticeModifier(bpy.types.Operator):
    bl_idname = "object.apply_lattice_modifier"
    bl_label = "Apply Lattice Modifier"

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH' and self.modifier_name in obj.modifiers:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=self.modifier_name)
        self.report({'INFO'}, f"Applied lattice modifier '{self.modifier_name}' to all objects.")
        return {'FINISHED'}


class OBJECT_OT_DeleteLatticeModifier(bpy.types.Operator):
    bl_idname = "object.delete_lattice_modifier"
    bl_label = "Delete Lattice Modifier"

    modifier_name: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH' and self.modifier_name in obj.modifiers:
                obj.modifiers.remove(obj.modifiers[self.modifier_name])
        self.report({'INFO'}, f"Deleted lattice modifier '{self.modifier_name}' from all objects.")
        return {'FINISHED'}


# Helper functions
def group_objects_by_collection(context):
    grouped = {}
    managed_objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                       item.object_name in context.scene.objects]

    for obj in managed_objects:
        collection = obj.users_collection[0].name if obj.users_collection else "None"
        if collection not in grouped:
            grouped[collection] = []
        grouped[collection].append(obj)

    return grouped


def gather_lattice_modifiers(context):
    """ Gathers all lattice modifiers by modifier name across managed objects. """
    lattice_modifiers = {}
    managed_objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                       item.object_name in context.scene.objects]

    for obj in managed_objects:
        for mod in obj.modifiers:
            if mod.type == 'LATTICE' and mod.object:
                if mod.name not in lattice_modifiers:
                    lattice_modifiers[mod.name] = {
                        "lattice_object": mod.object,
                        "strength_modifier": mod,
                        "visible": not mod.object.hide_viewport
                    }
    return lattice_modifiers


# Registration
classes = [
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
]


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


if __name__ == "__main__":
    register()
