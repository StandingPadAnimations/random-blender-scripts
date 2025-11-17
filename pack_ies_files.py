# Copyright (C) 2025 Mahid Sheikh <mahid@standingpad.org>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path
import bpy

bl_info = {
    "name" : "Pack IES Files",
    "author" : "Mahid Sheikh <mahid@stanidngpad.org>",
    "version" : (1, 0),
    "blender" : (4, 3, 0),
    "description" : "Doing what Blender should have done a long time ago and pack IES files with blend files",
    "warning" : "Will pack IES files for all files when saving, please disable if you don't want this",
    "category" : "Fixing Blender",    
}

def pack_ies(node: bpy.types.ShaderNodeTexIES) -> None:
    """Given an IES node with an external file, open the path
    as a text datablock and set the IES node to the datablock.

    Text datablocks are packed with files, unlike external IES
    files. Why this is the case, I don't know, and I'm still
    salty about it, hence why I wrote this script.
    """

    if node.mode == 'EXTERNAL':
        filepath = Path(bpy.path.abspath(node.filepath))
        if filepath.name not in bpy.data.texts:
            bpy.ops.text.open(filepath=bpy.path.abspath(node.filepath))
        node.mode = 'INTERNAL'
        node.ies = bpy.data.texts[filepath.name]

def iterate_nodes(ntree: bpy.types.NodeTree) -> None:
    """Iterate through all nodes, including nodes in group nodes"""
    for node in ntree.nodes:
        print(node.bl_idname)
        if node.type == 'GROUP':
            group_tree = node.node_tree
            if not group_tree:
                continue
            for group_node in group_tree.nodes:
                iterate_nodes(group_node)
        elif node.bl_idname == 'ShaderNodeTexIES':
            print("IES")
            pack_ies(node)
            
def main(scene):
    print("Packing IES lights")
    scene = bpy.context.scene
    scene_lights = [ob.data for ob in scene.objects if ob.type == 'LIGHT']

    for light in scene_lights:
        if not light.use_nodes:
            continue
        iterate_nodes(light.node_tree)
        
    print("Done packing IES lights")

def register():
    bpy.app.handlers.save_pre.append(main)

if __name__ == "__main__":
    register()
