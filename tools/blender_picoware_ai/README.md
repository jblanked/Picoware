# Blender AI Scene Generation

## About

Generate editable Blender scenes with a local OpenAI-compatible model, then export
Picoware meshes or animated billboards. The existing exporter works without AI.
Validated on Linux and Blender 5.3 Alpha; other platforms are untested.

## Textured Sprite3D export (1.6.0)

Select UV-mapped mesh objects in Object Mode, then choose **Export Selected** and
turn on **Bake Texture Atlas**. The exporter evaluates modifiers, packs UV islands
across the selected objects, and bakes Principled BSDF **Base Color** into one
opaque RGB565 atlas. Linked image textures and procedural Base Color inputs are
supported. Original objects, UVs, selection, materials and scene settings are
preserved. Baking uses Cycles on the CPU and can take time for larger assets.

Choose the atlas size to fit the device: 128 x 128 uses 32 KiB; 256 x 256 uses
128 KiB; 512 x 512 uses 512 KiB. UVs add 24 bytes per triangle, in addition to the
40-byte mesh record. The 65,535-triangle format limit is not a recommended device
budget. Texture rendering requires a supported backend (PicoCalc or the updated
Desktop simulator); this does not add texture rendering to every board.

For `model.sprite3d`, export creates these files together:

- `model.sprite3d`: unchanged mesh layout, white tint on baked triangles.
- `model.sprite3d.uv`: six little-endian float32 values per triangle, in exactly
  the mesh's vertex order, including mirrored-winding corrections.
- `model.sprite3d.rgb565`: little-endian RGB565 pixels, top row first.
- `model.sprite3d.json`: dimensions, format, triangle count and integrity hashes.

The metadata is for the Blender workflow; load assets explicitly in a game:

```python
from picoware.engine.sprite3d import Sprite3D

sprite = Sprite3D()
assert sprite.from_path("assets/model.sprite3d", False)
assert sprite.from_uv_path("assets/model.sprite3d.uv")
assert sprite.from_texture_path("assets/model.sprite3d.rgb565", 128, 128)
```

Keep the JSON beside the mesh when importing into Blender. Import restores the
UV map and a packed preview texture; mismatched or incomplete bundles are rejected.
Re-export with **Bake Texture Atlas** to save edits. **Save Back to Source** is
reserved for flat-color meshes. Existing flat exports still work with texture
baking disabled; use a new filename rather than overwriting a textured bundle
with a flat mesh. Existing bundle members receive backups when backup is enabled;
a failed write rolls back replaced members (this is not crash-atomic across files).

Textures contain Base Color only: transparency, lighting, metallic/roughness and
normal maps are not exported. **New Face Wireframe** controls outlines as before;
turn it off for solid textured surfaces. For AI-generated textured assets, export
the original scene directly: **Prepare for Picoware** deliberately creates a
flat-color copy and is unnecessary for texture baking.

## Billboard resolution

Billboard export supports 8, 16, 32 and 64 pixels per side (default: 32).
Use 64 for recognizable props such as benches; eight static views use 36 KiB
plus a 24-byte header. Each additional animation pose adds another 36 KiB.
Disable **Pixel Art** to retain the full RGB332 color range and rendered lighting.

## Installation

Install Python 3.10+ and bubblewrap (`bwrap`) using your distribution's package
manager. Unprivileged user/network namespaces and Chromium's sandbox must work.

Both packages are available as readable folders and matching install ZIPs:

- [picoware-blender-1.6.0.zip](picoware-blender-1.6.0.zip?raw=true):
  install through Blender's **Install from Disk** menu. Disable any older
  Picoware exporter first.
- [picoware-ai-helper-1.0.0.zip](picoware-ai-helper-1.0.0.zip?raw=true):
  the optional local AI helper. Extraction creates the `picoware-ai` directory.

Everything lives in `tools/blender_picoware_ai/`, including the editable source
folders and installation ZIPs:

```text
blender_picoware_ai/
├── README.md
├── build_package.py
├── picoware-blender-1.6.0/       # Blender add-on source and manifest
├── picoware-ai/                # Optional Python helper and vendored browser code
├── picoware-blender-1.6.0.zip
└── picoware-ai-helper-1.0.0.zip
```

The folders are the source of truth; there is no separate packaging copy to edit.
Each ZIP contains the same file bytes as its corresponding folder, excluding
local environments, caches and tests. Extract the helper ZIP here to recreate
`picoware-ai/`. The add-on ZIP has its manifest at the archive root for Blender's
**Install from Disk** menu. Neither component requires compilation; ZIPs provide
convenient installation, and the helper needs the Python dependencies below.

From the directory containing the downloaded helper archive:

```sh
unzip picoware-ai-helper-1.0.0.zip
cd picoware-ai
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python helper.py
```

With a repository checkout, you can instead run the helper directly from
`tools/blender_picoware_ai/picoware-ai/`, starting at the `python3 -m venv` step above.
To regenerate the ZIPs beside these source folders:

```sh
python3 tools/blender_picoware_ai/build_package.py
```

Use `--output /tmp/picoware-ai-release` to write ZIPs elsewhere.

In Blender, open **N → Sprite3D → Generate with AI**. Paste the helper token,
configure the model endpoint/name, and select **Check Connection**. Defaults use
`http://127.0.0.1:11438/v1` and `qwen3.5-4b-3d-coder-Q8_0` as examples.
For authenticated model servers, set `PICOWARE_MODEL_API_KEY` in the helper's
environment; credentials stay out of Blender and generated scenes.

## Notes and Examples

- Try: “A low-poly wooden windmill with a rotating blade group, under 1,000 triangles.”
  Generate a preview, inspect it, then import into a new Blender collection.
- Generated JavaScript runs in an isolated browser with external network blocked.
  Missing isolation support stops generation. Generated Python never runs in Blender.
- Animation supports fixed meshes/hierarchy with position, rotation and scale
  changes. Deformation, topology changes and animated materials are unsupported.
- **Prepare for Picoware** creates a separate flat-color copy. Transparency and
  shader effects are discarded there; original materials remain intact.
- `.sprite3d` is static and limited to 65,535 triangles. Use **Export Animated
  Billboard** for animation. Technical checks do not replace visual inspection;
  check moving-part clearance and baked frames, including pose count and timing.
- Jobs, prompts and reports are saved under `~/.local/share/picoware-ai/jobs`.
  Generation permits two repair attempts; progress and cancellation are in the panel.

### Authored collision boxes

Open the 3D View sidebar (N), then **Sprite3D → Bounding Boxes**.
**Convert to Bounding Box** replaces the active mesh with an upright box fitted
to its evaluated world bounds, including modifiers. The result is an invisible
wireframe collision helper. Conversion supports Undo and leaves other objects
sharing the original mesh unchanged. Existing parenting is retained; parent a
standalone helper to its asset or select both when exporting. Animated or
constrained objects must first be replaced by a static helper.

To keep the visible mesh and create a separate helper, select an asset and use
**Add Box Around Asset**. This creates one
wireframe `COLLIDER_` cube around the selected geometry. Move and resize it to
match the solid part of the asset; rotate around Blender Z for an angled box.
One box is recommended, with a hard maximum of **four boxes per exported
asset**, including all selected meshes together. Add more with the same button.
Helpers parented under selected meshes are included automatically. Manually
created helpers must be selected or parented under a selected mesh.

The toolbox also provides:

- **Assign to Asset:** select the boxes, then select the asset last (active). This
  parents them without changing their world placement and enforces the four-box limit.
- **Select Boxes / Show Boxes / Hide Boxes:** find the selected asset's helpers
  and control viewport visibility. Hidden helpers still export. Select also
  reveals hidden helpers; these recovery controls work even above the box limit.
- **Validate Boxes:** checks count, upright transforms and rectangular shape for
  Y Up export, reporting errors before export.
- **Remove Collision Tag:** makes selected helpers normal visible meshes again.
  It does not restore the shape replaced by conversion; use Undo for that.
- **Fit to Selected Geometry:** in Edit Mode, select vertices, edges or faces,
  then create a separate box fitted to those vertices in world space. The source
  geometry and Edit Mode selection stay intact. Flat selections receive 0.01 units
  of thickness. This uses the editable geometry, before modifiers, and parents
  the helper to the active mesh. Leave Edit Mode and use Select Boxes to edit it.

Helpers never enter exported triangles, texture atlases, or billboard renders.
Use rectangular cubes without modifiers, tilt, or shear. Collision exports
require Y Up axes and applied object transforms; unsupported settings and a
fifth box produce an error before overwriting the asset. Boxes are static,
including for animated billboard exports (author a suitable fixed envelope).
Assets without helpers export an empty sidecar. This does not disable the engine's
normal Entity collision handling.

Both mesh and billboard export write `<asset filename>.colliders`. These are
asset-space coordinates using the mesh export's origin, scale, and Y Up mapping
(Blender X/Z/-Y). Keep the same origin and placement for sprite and mesh versions;
a sprite's image dimensions or transparent padding are not collision dimensions.
Current Pico-Game-Engine uses `Entity::updateAABB()` and `Level::is_collision()`
for built-in collision handling. It does not load `.colliders` files. These
sidecars are optional authoring data for custom game collision logic, not a
replacement for the engine's Entity bounds. A game must explicitly read the
records and implement its desired collision checks, including asset transforms.
Mesh, UV, texture and billboard exports work without a sidecar loader.

Binary format version 1: ASCII `PCB1`, little-endian uint32 box count (0–4), then
seven little-endian float32 values per box: center X/Y/Z, half-size X/Y/Z, yaw
radians around vertical Y (positive yaw rotates +X toward +Z). File size is
8–120 bytes. Zero-count files explicitly clear previously authored colliders.
