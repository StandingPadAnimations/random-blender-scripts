# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# I am not responsible for any lost configs that occur from 
# the use of this addon. This whole point of this addon is to 
# nuke your config.

import bpy
import os 
import shutil
import atexit
from pathlib import Path

bl_info = {
	"name": "Nuke Config",
	"category": "Object",
	"location": "3D window toolshelf > Nuke Config",
	"version": (0, 0, 1),
	"blender": (2, 80, 0),
	"description": "Addon to nuke the Blender config when you accidently forget to import previous settings.",
	"warning": "Nuked configs are not recoverable.",
	"author": "Mahid Sheikh <mahid@standingpad.org>",
}

CONFIG_FOLDER = Path(os.path.dirname(__file__)).parents[1]

def delete_config():
	shutil.rmtree(CONFIG_FOLDER)
_ = atexit.register(delete_config)

class NUKE_CONFIG_PT_nuke(bpy.types.Panel):
	bl_label = "Nuke Config"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'	
	bl_category = "Nuke Config"

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.operator("nuke_config.nuke")

class NUKE_CONFIG_OT_nuke(bpy.types.Operator):
	bl_idname = "nuke_config.nuke"
	bl_label = "Nuke Blender Config"
	bl_description = "Nuke your Blender config :D"

	def execute(self, ctx):
		delete_config()
		return {'FINISHED'}

classes = (NUKE_CONFIG_OT_nuke,
		   NUKE_CONFIG_PT_nuke)
def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

print(f"WILL NUKE CONFIG, COPY {CONFIG_FOLDER} TO A SAFE LOCATION BEFORE CLOSING BLENDER")
