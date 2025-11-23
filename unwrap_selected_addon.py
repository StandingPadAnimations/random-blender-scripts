# Copyright (C) 2025 Maryam Sheikh (Mahid Sheikh) <mahid@standingpad.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy

bl_info = {
    "name": "Unwrap Selected",
    "category": "Object",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "3D window toolshelf > Tool",
    "description": "Simple addon to unwrap all selected objects, including collection instances",
    "author": "Maryam Sheikh <mahid@standingpad.org>",
    "tracker_url": "https://github.com/StandingPadAnimations/random-blender-scripts/issues",
}


class UNWRAP_OT_unwrap_selected(bpy.types.Operator):
    bl_idname = "object.unwrap_selected"
    bl_label = "Unwrap Selected Objects"

    def execute(self, context: bpy.types.Context):
        selected = (obj for obj in bpy.context.selected_objects)
        active = bpy.context.view_layer.objects.active

        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected:
            # Get the "instance collection"
            coll = obj.instance_collection

            if not coll:
                if obj.type != "MESH":
                    continue
                self.unwrap_mesh(obj)
                continue

            # Copied from here:
            # https://github.com/SuperFLEB/BlenderEditCollectionAddon/blob/7468e21cf887cb89b92eb0b46a75165ca51b750e/src/__init__.py#L37C9-L42C49
            #
            # In essence, what we're doing here is we're
            # creating a new Blender scene that contains
            # just the source collection for the object
            #
            # From there, we can then perform the rest
            # of our tasks
            scene_name = f"temp:{coll.name}"
            bpy.ops.scene.new(type="EMPTY")
            new_scene = bpy.context.scene
            new_scene.name = scene_name
            bpy.context.window.scene = new_scene
            new_scene.collection.children.link(coll)
            bpy.context.view_layer.active_layer_collection = (
                bpy.context.view_layer.layer_collection.children[coll.name]
            )

            bpy.ops.object.select_all(action="DESELECT")
            self.unwrap_instance_collection()

            # Delete the new scene created for modifying
            # instance collection
            bpy.ops.scene.delete()

        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active

        return {"FINISHED"}

    def unwrap_mesh(self, obj) -> None:
        """Unwrap mesh with cube projection"""
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project()
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)

    def unwrap_instance_collection(self) -> None:
        bpy.ops.object.select_all(action="SELECT")
        selected_instance = (obj for obj in bpy.context.selected_objects)
        bpy.ops.object.select_all(action="DESELECT")

        for obj in selected_instance:
            if obj.type != "MESH":
                continue
            self.unwrap_mesh(obj)


class UNWRAP_PT_unwrap_selected(bpy.types.Panel):
    bl_idname = "UNWRAP_PT_unwrap_selected"
    bl_label = "Unwrap Selected"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        row = layout.row()
        row.operator("object.unwrap_selected")


classes = (UNWRAP_OT_unwrap_selected, UNWRAP_PT_unwrap_selected)


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
