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

            layout.operator("object.lattice_add_to_all", text="Add Lattice to All")

            # Display managed objects grouped by collection
            col = layout.column()
            for coll_name, objs in group_objects_by_collection(context).items():
                col.label(text=f"Collection: {coll_name}")
                for obj in objs:
                    col.label(text=f"  - {obj.name}")

            # Display all lattice modifiers across managed objects
            layout.label(text="Lattice Modifiers in Managed Objects:")
            lattice_modifiers = get_lattice_modifiers(context)

            for lattice_name, mods in lattice_modifiers.items():
                box = layout.box()
                row = box.row()
                row.label(text=lattice_name)

                # Toggle lattice visibility
                lattice_object = mods[0].object if mods else None
                if lattice_object:
                    icon = "HIDE_OFF" if lattice_object.visible_get() else "HIDE_ON"
                    row.prop(lattice_object, "hide_viewport", text="", icon=icon, toggle=True)

                # Strength slider for all lattice modifiers with the same name
                row = box.row()
                row.prop(mods[0], "strength", text="Strength")
                for mod in mods[1:]:
                    mod.strength = mods[0].strength


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
        props = context.scene.lattice_manager_props
        managed_objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                           item.object_name in context.scene.objects]

        # Check if we should use an existing lattice
        if props.use_existing_lattice and props.lattice_object:
            lattice = props.lattice_object
            modifier_name = lattice.name
        else:
            # Calculate bounding box and create new lattice
            min_coords, max_coords = self.calculate_bounding_box(managed_objects)
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

        # Add lattice modifier to all managed objects with specified name
        for obj in managed_objects:
            mod = obj.modifiers.new(name=modifier_name, type='LATTICE')
            mod.object = lattice
        self.report({'INFO'}, "Lattice modifiers added to managed objects.")
        return {'FINISHED'}

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


# Helper function to group objects by collection
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


# Helper function to get lattice modifiers for managed objects
def get_lattice_modifiers(context):
    lattice_modifiers = {}
    managed_objects = [context.scene.objects[item.object_name] for item in context.scene.managed_objects if
                       item.object_name in context.scene.objects]

    for obj in managed_objects:
        for mod in obj.modifiers:
            if mod.type == 'LATTICE':
                if mod.name not in lattice_modifiers:
                    lattice_modifiers[mod.name] = []
                lattice_modifiers[mod.name].append(mod)

    return lattice_modifiers


# Registration
classes = [
    LatticeManagerProperties,
    ManagedObject,
    OBJECT_PT_LatticeManager,
    OBJECT_OT_LatticeManageSelected,
    OBJECT_OT_LatticeUnmanageAll,
    OBJECT_OT_LatticeAddToAll,
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
