# Copyright (C) 2025 Maryam Sheikh (Mahid Sheikh) <mahid@standingpad.org>
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

import bpy
import bmesh
import mathutils

SELECTED = (obj for obj in bpy.context.selected_objects)
ACTIVE = bpy.context.view_layer.objects.active


# The cube projection code is a translation of
# Blender's C++ code to Python, done by Gemini
#
# Reference
# https://projects.blender.org/blender/blender/src/commit/e1e3e7e50694de20a3bac6889867ecc770305e2c/source/blender/editors/uvedit/uvedit_unwrap_ops.cc#L4181-L4227
#
# We have our own implementation of the operator to
# performance issues associated with using operators
# upon operators. This also (in theory) opens up the
# door for parallel processing of meshes, though that
# may not be necessary.
#
# In testing, this is virtually identical results wise
# to the built-in cube projection
def get_dominant_axis_indices(normal: mathutils.Vector) -> tuple[int, int]:
    """
    Determines which axes (x, y) to use for projection based on the
    largest component of the face normal.
    """
    abs_x = abs(normal.x)
    abs_y = abs(normal.y)
    abs_z = abs(normal.z)

    # Replicating BLI_math_geom.c logic
    if abs_x > abs_y:
        if abs_x > abs_z:
            return 1, 2  # X is dominant, project on Y, Z
        else:
            return 0, 1  # Z is dominant, project on X, Y
    else:
        if abs_y > abs_z:
            return 0, 2  # Y is dominant, project on X, Z
        else:
            return 0, 1  # Z is dominant, project on X, Y


def calculate_selection_center(
    bm: bmesh.types.BMesh, use_select: bool
) -> mathutils.Vector:
    """Calculates the average center of selected faces to use as the projection pivot."""
    total_co = mathutils.Vector((0.0, 0.0, 0.0))
    count = 0

    for face in bm.faces:
        if use_select and not face.select:
            continue
        # Use face center (centroid) for average
        total_co += face.calc_center_median()
        count += 1

    if count == 0:
        return mathutils.Vector((0.0, 0.0, 0.0))

    return total_co / count


def cube_project(
    bm: bmesh.types.BMesh,
    cube_size: float = 1.0,
    use_select: bool = True,
    center: mathutils.Vector | None = None,
) -> None:
    """
    Python equivalent of Blender's Cube Projection operator, so
    we don't have to use operators (and their performance impact)
    """
    loc = center
    if center is None:
        loc = calculate_selection_center(bm, use_select)

    # Prevent division by zero
    if cube_size == 0.0:
        cube_size = 1.0

    scale_inv = 1.0 / cube_size
    uv_layer = bm.loops.layers.uv.verify()

    for face in bm.faces:
        if use_select and not face.select:
            continue

        # Determine which plane to map this face onto
        cox, coy = get_dominant_axis_indices(face.normal)

        for loop in face.loops:
            co = loop.vert.co
            loop_uv = loop[uv_layer]

            # Project coordinate to 0-1 UV space
            # 0.5 centers the projection on the UV tile
            u = 0.5 + ((co[cox] - loc[cox]) * scale_inv)
            v = 0.5 + ((co[coy] - loc[coy]) * scale_inv)

            loop_uv.uv = (u, v)


def unwrap_instance_collection() -> None:
    bpy.ops.object.select_all(action="SELECT")
    selected_instance = (obj for obj in bpy.context.selected_objects)
    bpy.ops.object.select_all(action="DESELECT")

    for obj in selected_instance:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        has_selection = any(f.select for f in bm.faces)

        cube_project(bm, 1.0, has_selection, center=None)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def main() -> None:
    for obj in SELECTED:
        # Get the "instance collection"
        coll = obj.instance_collection

        if not coll:
            if obj.type != "MESH":
                continue

            bm = bmesh.new()
            bm.from_mesh(obj.data)
            has_selection = any(f.select for f in bm.faces)

            cube_project(bm, 1.0, has_selection, center=None)

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

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
        unwrap_instance_collection()

        # Delete the new scene created for modifying
        # instance collection
        bpy.ops.scene.delete()


if __name__ == "__main__":
    main()
