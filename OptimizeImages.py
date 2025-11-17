# Quick script to take every image and optimize it to be a single pixel
# that represents the average color of every pixel. This is meant to be
# used on far away objects where the details of the texture no longer 
# matter, thus allowing us to optimize away all of those details and
# avearge out all of the colors to a single pixel. This should in theory
# reduce vRAM usage a bit

import bpy
import numpy as np
from mathutils import Color

def average_image_color(image):
    """Averages the colors of the pixels in the image."""
    pixels = np.array(image.pixels[:])
    num_pixels = len(pixels) // 4
    pixels = pixels.reshape((num_pixels, 4))  # (R, G, B, A)

    # Average only the RGB channels, ignoring alpha
    avg_rgb = np.mean(pixels[:, :3], axis=0)
    return Color(avg_rgb)

def create_single_pixel_image(color):
    """Creates a 1x1 pixel image of the given color."""
    image = bpy.data.images.new("AvgColor", width=1, height=1)
    image.pixels[0:4] = [color.r, color.g, color.b, 1.0]  # Set RGBA values (A = 1)
    return image

def replace_images_with_average_color():
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if not mat.use_nodes:
                    continue
                for node in mat.node_tree.nodes:
                    # Check if node is an image texture node
                    if not node.type == 'TEX_IMAGE' or not node.image:
                        continue
                    image = node.image
                    avg_color = average_image_color(image)
                    new_image = create_single_pixel_image(avg_color)
                    node.image = new_image
                    new_image.name = f"AvgColor_{image.name}"

replace_images_with_average_color()
