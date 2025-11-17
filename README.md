# Random Blender Scripts

Just some random Blender scripts/addons I've made in the past that are too small to warrent their own repos

- `nuke_version.py` - An addon that, once enabled, will delete a Blender install's configuration
- `pack_ies_files.py` - An addon that adds a hook when saving that goes through all lights in the scene,
  imports external IES files as text datablocks, and sets IES nodes to those datablocks so that IES textures
  can be packed in a blend file like most other external assets
- `unwrap_selected.py` - A script that unwraps selected objets with cube projection; if an object is an instance
  collection, it'll go through the source collection and unwrap it as well
- `OptimizeImages.py` - A script that goes through all the materials on the selected object(s), and for every texture
  used in their materials averages the color and replaces the texture with a single pixel image of the averaged color
