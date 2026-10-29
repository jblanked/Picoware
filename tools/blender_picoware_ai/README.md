# Blender AI Scene Generation

## About

Generate editable Blender scenes with a local OpenAI-compatible model, then export
Picoware meshes or animated billboards. The existing exporter works without AI.
Validated on Linux and Blender 5.3 Alpha; other platforms are untested.

## Installation

Install Python 3.10+ and bubblewrap (`bwrap`) using your distribution's package
manager. Unprivileged user/network namespaces and Chromium's sandbox must work.

Both packages are available as readable folders and matching install ZIPs:

- [picoware-blender-1.5.0.zip](picoware-blender-1.5.0.zip?raw=true):
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
├── picoware-blender-1.5.0/       # Blender add-on source and manifest
├── picoware-ai/                # Optional Python helper and vendored browser code
├── picoware-blender-1.5.0.zip
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
- `.sprite3d` is static and limited to 4,096 triangles. Use **Export Animated
  Billboard** for animation. Technical checks do not replace visual inspection;
  check moving-part clearance and baked frames, including pose count and timing.
- Jobs, prompts and reports are saved under `~/.local/share/picoware-ai/jobs`.
  Generation permits two repair attempts; progress and cancellation are in the panel.
