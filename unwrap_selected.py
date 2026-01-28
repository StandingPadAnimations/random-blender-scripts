# Copyright (C) 2025-2026 Maryam Sheikh (Mahid Sheikh) <mahid@standingpad.org>
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

import enum

import bpy
import bmesh
from mathutils import Matrix, Vector

SELECTED = (obj for obj in bpy.context.selected_objects)


# The cube projection code is a translation of
# Blender's C++ code to Python.
#
# Reference Commit: e1e3e7e50694de20a3bac6889867ecc770305e2c
#
# We have our own implementation of the operator to
# performance issues associated with using operators
# upon operators. This also (in theory) opens up the
# door for parallel processing of meshes, though that
# may not be necessary.
#
# While it's as close to 1-to-1 as possible, some liberties
# have been taken to keep things minimal. Function names
# are the same as they would be in the Blender source code.
# Comments will contain the source file and lines of the original
# C++ functions.

# ./source/blender/blenlib/BLI_utildefines.h
# Lines: 40-51
INIT_MIN = 1.0e30
INIT_MAX = -1.0e30

INIT_MINMAX = (
    Vector((INIT_MIN, INIT_MIN, INIT_MIN)),
    Vector((INIT_MAX, INIT_MAX, INIT_MAX)),
)


class V3DAround(enum.Enum):
    CENTER_BOUNDS = 0
    CENTER_MEDIAN = 1
    CURSOR = 2
    ACTIVE = 3
    LOCAL_ORIGINS = 4


def get_v3d_pivot() -> V3DAround:
    """Return the current pivot in View3D."""
    if bpy.context.scene:
        match bpy.context.scene.tool_settings.transform_pivot_point:
            case "MEDIAN_POINT":
                return V3DAround.CENTER_MEDIAN
            case "INDIVIDUAL_ORIGINS":
                return V3DAround.LOCAL_ORIGINS
            case "ACTIVE_ELEMENT":
                return V3DAround.ACTIVE
            case "CURSOR":
                return V3DAround.CURSOR
            case "BOUNDING_BOX_CENTER":
                return V3DAround.CENTER_BOUNDS
    return V3DAround.CENTER_BOUNDS


def minmax_v3v3_v3(f_min: Vector, f_max: Vector, vec: Vector) -> tuple[Vector, Vector]:
    """Translation of Blender's minmax_v3v3_v3 function.

    ./source/blender/blenlib/intern/math_vector.cc
    Lines: 716-725
    """
    new_f_min = Vector(
        (min(f_min[0], vec[0]), min(f_min[1], vec[1]), min(f_min[2], vec[2]))
    )
    new_f_max = Vector(
        (max(f_max[0], vec[0]), max(f_max[1], vec[1]), max(f_max[2], vec[2]))
    )

    return new_f_min, new_f_max


def mul_v3_m4v3(mat: Matrix, vec: Vector) -> Vector:
    """Translation of Blender's mul_v3_m4v3 function.

    ./source/blender/blenlib/intern/math_matrix_c.cc
    Lines: 674-682
    """
    x = vec[0]
    y = vec[1]
    return Vector(
        (
            x * mat[0][0] + y * mat[1][0] + mat[2][0] * vec[2] + mat[3][0],
            x * mat[0][1] + y * mat[1][1] + mat[2][1] * vec[2] + mat[3][1],
            x * mat[0][2] + y * mat[1][2] + mat[2][2] * vec[2] + mat[3][2],
        )
    )


def BM_face_calc_bounds_expand(
    bm_face: bmesh.types.BMFace, f_min: Vector, f_max: Vector
) -> tuple[Vector, Vector]:
    """Translation of Blender's BM_face_calc_bounds_expand function.

    ./source/blender/bmesh/intern/bmesh_polygon.cc
    Lines: 607-614
    """
    cur_f_min, cur_f_max = f_min, f_max
    for loop in bm_face.loops:
        cur_f_min, cur_f_max = minmax_v3v3_v3(f_min, f_max, loop.vert.co)
    return cur_f_min, cur_f_max


def BM_editselection_center(
    ese: bmesh.types.BMVert | bmesh.types.BMEdge | bmesh.types.BMFace,
) -> Vector:
    """Translation of Blender's BM_editselection_center function.

    ./source/blender/bmesh/intern/bmesh_marking.cc
    Lines: 1044-1058
    """
    if isinstance(ese, bmesh.types.BMVert):
        return ese.co
    elif isinstance(ese, bmesh.types.BMEdge):
        return 0.5 * (ese.verts[0].co + ese.verts[1].co)
    return ese.calc_center_median()


def ED_uvedit_get_aspect_from_material(
    obj: bpy.types.Object, material_index: int
) -> tuple[float, float]:
    """Translation of Blender's ED_uvedit_get_aspect_from_material function, with other functions inlined.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 494-507

    ./source/blender/editors/space_image/image_edit.cc
    Lines: 311-326
    """
    r_aspx, r_aspy = 1.0, 1.0
    if material_index < 0 or material_index >= len(obj.material_slots):
        return r_aspx, r_aspy

    mat = obj.material_slots[material_index].material
    if mat and mat.node_tree:
        active_node = mat.node_tree.nodes.active
        if not active_node or active_node.bl_idname != "TEX_IMAGE":
            return r_aspx, r_aspy

        image = active_node.image

        if image:
            w, h = image.size[0], image.size[1]
            r_aspx, r_aspy = image.display_aspect[0], image.display_aspect[1]

            r_aspx *= float(w)
            r_aspy *= float(h)

    return r_aspx, r_aspy


def shrink_loop_uv_by_aspect_ratio(
    face: bmesh.types.BMFace, uv_layer: bmesh.types.BMLayerItem, aspect_y: float
) -> None:
    """Translation of Blender's shrink_loop_uv_by_aspect_ratio function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 2504-2524
    """
    assert aspect_y != 1.0  # Nothing to do, should be handled by caller.
    assert aspect_y > 0.0  # Negative aspect ratios are not supported

    for loop in face.loops:
        loop_uv = loop[uv_layer]

        if aspect_y > 1.0:
            loop_uv.uv[0] = loop_uv.uv[0] / aspect_y + (0.5 - 0.5 / aspect_y)
        else:
            loop_uv.uv[1] = loop_uv.uv[1] * aspect_y + (0.5 - 0.5 * aspect_y)


def correct_uv_aspect_per_face(obj: bpy.types.Object, bm: bmesh.types.BMesh) -> None:
    """Translation of Blender's correct_uv_aspect_per_face function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 2543-2584
    """
    materials_num = len(obj.material_slots)
    if materials_num == 0:
        return

    material_aspect_y: list[float] = [-1.0] * materials_num

    for face in bm.faces:
        if not face.select:
            continue

        material_index = face.material_index
        if materials_num < 0 or material_index >= materials_num:
            continue

        aspect_y: float = material_aspect_y[material_index]

        if aspect_y == -1.0:
            aspx, aspy = ED_uvedit_get_aspect_from_material(obj, material_index)
            aspect_y = aspx / aspy
            material_aspect_y[material_index] = aspect_y

        # Not an elif since we need to
        # check this after calculating
        # aspect_y
        if aspect_y == 1.0:
            continue  # Scaling by 1.0 has no effect

        uv_layer = bm.loops.layers.uv.verify()
        shrink_loop_uv_by_aspect_ratio(face, uv_layer, aspect_y)


def uv_map_clip_correct(
    obj: bpy.types.Object, bm: bmesh.types.BMesh, per_face_aspect: bool
) -> None:
    """Heavially simplified translation of Blender's uv_map_clip_correct function."""

    correct_aspect: bool = True

    if correct_aspect and per_face_aspect:
        correct_uv_aspect_per_face(obj, bm)


def uv_map_transform_calc_bounds(
    bm: bmesh.types.BMesh, r_min: Vector, r_max: Vector
) -> tuple[Vector, Vector]:
    """Translation of Blender's uv_map_transform_calc_bounds function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 2275-2285
    """
    cur_r_min, cur_r_max = r_min, r_max
    for face in bm.faces:
        if not face.select:
            continue
        cur_r_min, cur_r_max = BM_face_calc_bounds_expand(face, cur_r_min, cur_r_max)
    return cur_r_min, cur_r_max


def uv_map_transform_calc_center_median(bm: bmesh.types.BMesh) -> Vector:
    """Translation of Blender's uv_map_transform_calc_center_median function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 2287-2302
    """
    cur_r_center: Vector = Vector((0, 0, 0))
    center_accum_num = 0
    for face in bm.faces:
        if not face.select:
            continue
        center = face.calc_center_median()
        cur_r_center = cur_r_center + center
        center_accum_num += 1
    return cur_r_center * (1.0 / center_accum_num)


def uv_map_transform_center(
    object: bpy.types.Object, bm: bmesh.types.BMesh
) -> tuple[Vector, tuple[Vector, Vector]]:
    """Translationof Blender's uv_map_transform_center function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 2304-2359
    """
    bounds: tuple[Vector, Vector] = INIT_MINMAX
    cur_r_center = Vector((0, 0, 0))
    around: V3DAround = get_v3d_pivot()
    is_minmax_set: bool = False

    # TODO: Get CURSOR to have parity with Blender
    match around:
        case V3DAround.CENTER_BOUNDS:
            bounds = uv_map_transform_calc_bounds(bm, bounds[0], bounds[1])
            is_minmax_set = True
            cur_r_center = 0.5 * (bounds[0] + bounds[1])
        case V3DAround.CENTER_MEDIAN:
            cur_r_center = uv_map_transform_calc_center_median(bm)
        case V3DAround.CURSOR:
            inverted = object.matrix_world.inverted()
            if bpy.context.scene and inverted:
                cur_r_center = mul_v3_m4v3(inverted, bpy.context.scene.cursor.location)
        case V3DAround.ACTIVE:
            selection_history = bm.select_history
            if selection_history.active:
                cur_r_center = BM_editselection_center(selection_history.active)
        case V3DAround.LOCAL_ORIGINS:
            cur_r_center = Vector((0, 0, 0))

    if not is_minmax_set:
        bounds = uv_map_transform_calc_bounds(bm, bounds[0], bounds[1])

    return cur_r_center, bounds


def axis_dominant_v3(axis: Vector) -> tuple[int, int]:
    """Translation of Blender's axis_dominant_v3 function.

    ./source/blender/blenlib/intern/math_geom_inline.cc
    Lines: 43-61
    """
    xn, yn, zn = abs(axis[0]), abs(axis[1]), abs(axis[2])

    if zn >= xn and zn >= yn:
        return 0, 1
    elif yn >= xn and yn >= zn:
        return 0, 2
    return 1, 2


def uvedit_unwrap_cube_project(
    bm: bmesh.types.BMesh,
    cube_size: float,
    use_select: bool,
    only_selected_uvs: bool,
    center: Vector | None = None,
) -> None:
    """Translation of uvedit_unwrap_cube_project.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: 4181-4227
    """
    cur_cube_size = cube_size
    loc: Vector = Vector((0, 0, 0))
    cox, coy = 0, 0

    if center is not None:
        loc = center

    if cube_size == 0.0:
        cur_cube_size = 1.0

    for face in bm.faces:
        if use_select and not face.select:
            continue
        elif only_selected_uvs and not face.uv_select:
            continue

        cox, coy = axis_dominant_v3(face.normal)
        uv_layer = bm.loops.layers.uv.verify()

        for loop in face.loops:
            co = loop.vert.co
            loop_uv = loop[uv_layer]

            u = 0.5 + ((co[cox] - loc[cox]) / cur_cube_size)
            v = 0.5 + ((co[coy] - loc[coy]) / cur_cube_size)

            loop_uv.uv = (u, v)


def cube_project_exec(cube_size: float, objects: tuple[bpy.types.Object, ...]) -> None:
    """Translation of Blender's cube_project_exec function.

    ./source/blender/editors/uvedit/uvedit_unwrap_ops.cc
    Lines: ./4229-L4291"""
    cube_size_init = cube_size
    for idx, obj in enumerate(objects):
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        has_selection = any(f.select for f in bm.faces)

        if not has_selection:
            bm.free()
            continue

        # Declare bounds variable in advanced.
        bounds: tuple[Vector, Vector] | None = None
        center: Vector = Vector((0, 0, 0))

        center, bounds = uv_map_transform_center(obj, bm)

        if bounds:
            dims = bounds[1] - bounds[0]
            cube_size = max(dims[0], dims[1], dims[2])

            if idx == 0:
                # This doesn't fit well with multiple objects
                cube_size_init = cube_size

        uvedit_unwrap_cube_project(bm, cube_size_init, True, False, center)

        per_face_aspect = True

        uv_map_clip_correct(obj, bm, per_face_aspect)

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def unwrap_instance_collection() -> None:
    bpy.ops.object.select_all(action="SELECT")
    selected_instance = (obj for obj in bpy.context.selected_objects)
    bpy.ops.object.select_all(action="DESELECT")

    for obj in selected_instance:
        if obj.type != "MESH":
            continue

        cube_project_exec(1.0, (obj,))


def main() -> None:
    for obj in SELECTED:
        # Get the "instance collection"
        coll = obj.instance_collection

        if not coll:
            if obj.type != "MESH":
                continue

            cube_project_exec(1.0, (obj,))

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
