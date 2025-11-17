# Copyright (C) 2025 Mahid Sheikh <mahid@standingpad.org>
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

SELECTED = (obj for obj in bpy.context.selected_objects)
ACTIVE = bpy.context.view_layer.objects.active


def unwrap_mesh(obj) -> None:
    """Unwrap mesh with cube projection"""
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project()
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    
def unwrap_instance_collection() -> None:
    bpy.ops.object.select_all(action='SELECT')
    selected_instance = (obj for obj in bpy.context.selected_objects)
    bpy.ops.object.select_all(action='DESELECT')
    
    for obj in selected_instance:
        if obj.type != 'MESH':
            continue
        unwrap_mesh(obj)
    
def main() -> None:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in SELECTED:
        # Get the "instance collection"
        coll = obj.instance_collection
         
        if not coll:
            if obj.type != 'MESH':
                continue
            unwrap_mesh(obj)
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
        bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
        
        bpy.ops.object.select_all(action='DESELECT')
        unwrap_instance_collection()
        
        # Delete the new scene created for modifying
        # instance collection
        bpy.ops.scene.delete()
        
    for obj in SELECTED:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = ACTIVE
    
if __name__ == "__main__":
    main()
