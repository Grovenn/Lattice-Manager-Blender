import bpy
from mathutils import Vector

bl_info = {
    "name": "Lattice Manager",
    "blender": (4, 1, 0),
    "category": "Object",
}

# Properties for per-lattice data
class LatticeData(bpy.types.PropertyGroup):
    lattice_name: bpy.props.StringProperty()
    strength: bpy.props.FloatProperty(
        name="Strength",
        default=0.0,
        min=0.0,
        max=1.0,
        update=lambda self, context: update_strength(context, self.lattice_name, self.strength)
    )

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
    lattice_data: bpy.props.CollectionProperty(type=LatticeData)

# Collection Property to Store Managed Objects
class ManagedObject(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty()
    lattice_modifiers: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)

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
        print(f"Gathered lattice modifiers: {lattice_modifiers}")
        if lattice_modifiers:
            layout.label(text="Lattice Modifiers:")
            props = context.scene.lattice_manager_props
            for lattice_name, data in lattice_modifiers.items():
                print(f"Drawing UI for lattice modifier: {lattice_name}")
                box = layout.box()

                # Draw lattice name
                row = box.row(align=True)
                row.label(text=lattice_name)

                # Visibility toggle button
                visibility_icon = 'HIDE_OFF' if data["visible"] else 'HIDE_ON'
                op = row.operator("object.toggle_lattice_visibility", text="", icon=visibility_icon, emboss=False)
                op.lattice_name = data["lattice_object"].name
                print(f"Visibility toggle button for {lattice_name} with icon {visibility_icon}")

                # Action buttons: Select/Deselect
                row = box.row(align=True)
                select_op = row.operator("object.select_objects_with_modifier", text="Select Objects")
                select_op.modifier_name = lattice_name
                print(f"Select button for {lattice_name}")

                deselect_op = row.operator("object.deselect_objects_with_modifier", text="Deselect Objects")
                deselect_op.modifier_name = lattice_name
                print(f"Deselect button for {lattice_name}")

                # Action buttons: Apply/Delete
                row = box.row(align=True)
                apply_op = row.operator("object.apply_lattice_modifier", text="Apply Lattice Modifiers")
                apply_op.modifier_name = lattice_name
                print(f"Apply button for {lattice_name}")

                delete_op = row.operator("object.delete_lattice_modifier", text="Delete Lattice Modifiers")
                delete_op.modifier_name = lattice_name
                print(f"Delete button for {lattice_name}")

                # Strength slider
                row = box.row()
                # Find the corresponding lattice data item
                lattice_data_item = next((item for item in props.lattice_data if item.lattice_name == lattice_name), None)
                if lattice_data_item:
                    print(f"Drawing strength slider for {lattice_name} with current strength {lattice_data_item.strength}")
                    row.prop(lattice_data_item, "strength", text="Strength", slider=True)
                else:
                    print(f"No lattice data found for {lattice_name}")

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

        # Update lattice data after managing objects
        update_lattice_data(context)

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
        add_lattice(context, manage_all=True)
        # Update lattice data after adding lattices
        update_lattice_data(context)
        self.report({'INFO'}, "Added lattice to all managed objects.")
        return {'FINISHED'}

class OBJECT_OT_LatticeAddToSelected(bpy.types.Operator):
    bl_idname = "object.lattice_add_to_selected"
    bl_label = "Add Lattice to Selected"

    def execute(self, context):
        add_lattice(context, manage_all=False)
        # Update lattice data after adding lattices
        update_lattice_data(context)
        self.report({'INFO'}, "Added lattice to selected objects.")
        return {'FINISHED'}

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
        # Update lattice data after applying modifiers
        update_lattice_data(context)
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
        # Update lattice data after deleting modifiers
        update_lattice_data(context)
        self.report({'INFO'}, f"Deleted lattice modifier '{self.modifier_name}' from all objects.")
        return {'FINISHED'}

# Helper Functions
def add_lattice(context, manage_all):
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
        min_coords, max_coords = calculate_bounding_box(objects)
        lattice = create_and_position_lattice(context, min_coords, max_coords)

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
        mod.strength = 0.0  # Set default strength to 0

def calculate_bounding_box(objects):
    # Start with the bounding box of the first object
    min_coords = Vector((float('inf'), float('inf'), float('inf')))
    max_coords = Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in objects:
        for vertex in obj.bound_box:
            world_vertex = obj.matrix_world @ Vector(vertex)
            min_coords = Vector((min(min_coords[i], world_vertex[i]) for i in range(3)))
            max_coords = Vector((max(max_coords[i], world_vertex[i]) for i in range(3)))

    return min_coords, max_coords

def create_and_position_lattice(context, min_coords, max_coords):
    # Create a new lattice object
    lattice_data = bpy.data.lattices.new("Lattice")
    lattice = bpy.data.objects.new("Lattice", lattice_data)

    # Position the lattice at the center of the bounding box
    lattice.location = (min_coords + max_coords) / 2

    # Set the dimensions of the lattice to fit the bounding box with a scaling factor of 2
    lattice.scale = (max_coords - min_coords) / 2 * 2  # Scaling up by a factor of 2

    return lattice

def gather_lattice_modifiers(context):
    """ Gathers all lattice modifiers by modifier name across managed objects without modifying props. """
    lattice_modifiers = {}
    managed_objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                       item.object_name in context.scene.objects]

    for obj in managed_objects:
        for mod in obj.modifiers:
            if mod.type == 'LATTICE' and mod.object:
                lattice_name = mod.name
                if lattice_name not in lattice_modifiers:
                    lattice_modifiers[lattice_name] = {
                        "lattice_object": mod.object,
                        "strength_modifiers": [mod],
                        "visible": not mod.object.hide_viewport
                    }
                else:
                    lattice_modifiers[lattice_name]["strength_modifiers"].append(mod)

    return lattice_modifiers

def update_lattice_data(context):
    """ Updates the lattice_data collection in props based on current lattice modifiers. """
    props = context.scene.lattice_manager_props
    props.lattice_data.clear()
    lattice_modifiers = gather_lattice_modifiers(context)

    for lattice_name, data in lattice_modifiers.items():
        lattice_data_item = props.lattice_data.add()
        lattice_data_item.lattice_name = lattice_name
        # Set default strength or retrieve from existing modifiers
        first_mod = data["strength_modifiers"][0]
        lattice_data_item.strength = first_mod.strength

def update_strength(context, lattice_name, strength_value):
    """ Update the strength of all lattice modifiers with the given lattice_name. """
    print(f"Updating strength to {strength_value} for lattice modifiers named {lattice_name}")
    lattice_modifiers = gather_lattice_modifiers(context)
    if lattice_name in lattice_modifiers:
        for mod in lattice_modifiers[lattice_name]["strength_modifiers"]:
            print(f"Updating {mod.name} on object {mod.id_data.name} to strength {strength_value}")
            mod.strength = strength_value
            print(f"Updated {mod.name} on object {mod.id_data.name} to strength {mod.strength}")
