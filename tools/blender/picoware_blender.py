# SPDX-License-Identifier: GPL-3.0-or-later
"""Install this file as a Blender add-on, or run it in Blender's Text Editor."""
bl_info = {
    'name': 'Picoware Mesh and Billboard Export',
    'author': 'Sprite3D Tools',
    'version': (1, 4, 5),
    'blender': (5, 0, 0),
    'location': 'File > Import/Export; View3D > Sidebar > Sprite3D',
    'description': 'Import Sprite3D meshes and export packed pixel-art billboards',
    'category': 'Import-Export',
}

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import struct
import stat
import tempfile
from typing import Iterable

RECORD = struct.Struct('<9fHH')
VERTEX = struct.Struct('<3f')
MAX_TRIANGLES = 4096  # Picoware engine_config.hpp; smaller builds may differ.
MAX_COORDINATE = 1e12
MAX_BYTES = MAX_TRIANGLES * RECORD.size


class FormatError(ValueError):
    """Unsupported input or data that cannot be represented by this format."""


@dataclass(frozen=True)
class Triangle:
    coordinates: tuple[float, ...]
    color: int
    extra: int


def decode(data: bytes) -> list[Triangle]:
    if not data:
        raise FormatError('Empty file: expected headerless 40-byte triangle records.')
    if len(data) % RECORD.size:
        raise FormatError(
            f'File size {len(data):,} is not a multiple of 40. '
            'Only the binary layout used by knight.sprite3d is supported.')
    if len(data) > MAX_BYTES:
        raise FormatError(f'Safety limit: at most {MAX_TRIANGLES:,} triangles per file.')
    result = []
    for index, values in enumerate(RECORD.iter_unpack(data), 1):
        if not all(math.isfinite(v) for v in values[:9]):
            raise FormatError(f'Triangle {index} has a non-finite coordinate; wrong format?')
        if any(abs(v) > MAX_COORDINATE for v in values[:9]):
            raise FormatError(f'Triangle {index}: coordinates must be within +/-1e12.')
        if values[10] & 0xFF not in (0, 1):
            raise FormatError(f'Triangle {index}: wireframe flag must be 0 or 1.')
        result.append(Triangle(values[:9], values[9], values[10]))
    return result


def read(path: str | Path) -> list[Triangle]:
    with Path(path).open('rb') as stream:
        # Limit the read as well as checking file size; do not trust a size race.
        return decode(stream.read(MAX_BYTES + 1))


def encode(triangles: Iterable[Triangle]) -> bytes:
    output = bytearray()
    for index, triangle in enumerate(triangles, 1):
        if index > MAX_TRIANGLES:
            raise FormatError(f'Safety limit: at most {MAX_TRIANGLES:,} triangles per file.')
        coords = triangle.coordinates
        if len(coords) != 9 or not all(math.isfinite(v) for v in coords):
            raise FormatError(f'Triangle {index} needs nine finite coordinates.')
        if any(abs(v) > MAX_COORDINATE for v in coords):
            raise FormatError(f'Triangle {index}: coordinates must be within +/-1e12.')
        for label, value in (('color', triangle.color), ('extra data', triangle.extra)):
            if not isinstance(value, int) or not 0 <= value <= 0xFFFF:
                raise FormatError(f'Triangle {index}: {label} must be an integer from 0 to 65535.')
        if triangle.extra & 0xFF not in (0, 1):
            raise FormatError(f'Triangle {index}: wireframe flag must be 0 or 1.')
        try:
            output.extend(RECORD.pack(*coords, triangle.color, triangle.extra))
        except (OverflowError, struct.error) as exc:
            raise FormatError(f'Triangle {index} is outside the float32 range.') from exc
    if not output:
        raise FormatError('Nothing to export: no triangle faces were found.')
    return bytes(output)


def source_to_blender(vertex, axes: str = 'Y_UP', scale: float = 1.0):
    """Exact permutation, not a trigonometric 90-degree rotation matrix."""
    check_scale(scale)
    x, y, z = vertex
    if axes == 'Y_UP':
        result = (x, -z, y)
    elif axes == 'BLENDER':
        result = (x, y, z)
    else:
        raise FormatError(f'Unsupported axis convention: {axes!r}')
    return result if scale == 1.0 else tuple(v * scale for v in result)


def blender_to_source(vertex, axes: str = 'Y_UP', import_scale: float = 1.0):
    check_scale(import_scale)
    x, y, z = vertex
    if axes == 'Y_UP':
        result = (x, z, -y)
    elif axes == 'BLENDER':
        result = (x, y, z)
    else:
        raise FormatError(f'Unsupported axis convention: {axes!r}')
    return result if import_scale == 1.0 else tuple(v / import_scale for v in result)


def check_scale(scale: float):
    if not math.isfinite(scale) or scale <= 0:
        raise FormatError('Scale must be a finite number greater than zero.')


def build_mesh_arrays(triangles, axes='Y_UP', scale=1.0, weld=True):
    """Return vertices/faces; weld only bit-identical source coordinates.

    Joining coincident coordinates can join formerly disconnected surfaces.
    It is optional. Degenerate triangles use separate indices to keep valid
    Blender loop topology, without moving their original positions.
    """
    vertices, faces, lookup = [], [], {}
    for tri in triangles:
        face = []
        for start in (0, 3, 6):
            xyz = tri.coordinates[start:start + 3]
            key = VERTEX.pack(*xyz)
            index = lookup.get(key) if weld else None
            if index is None or index in face:
                index = len(vertices)
                vertices.append(source_to_blender(xyz, axes, scale))
                lookup.setdefault(key, index)
            face.append(index)
        faces.append(tuple(face))
    return vertices, faces


def rgb565_to_srgb(value: int):
    return ((value >> 11 & 31) / 31.0,
            (value >> 5 & 63) / 63.0,
            (value & 31) / 31.0)


def srgb_to_linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value: float) -> float:
    if not math.isfinite(value):
        raise FormatError('Material color contains a non-finite value.')
    value = min(1.0, max(0.0, value))
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1.0 / 2.4) - 0.055


def rgb565_to_linear(value: int):
    return tuple(srgb_to_linear(v) for v in rgb565_to_srgb(value))


def linear_to_rgb565(rgb) -> int:
    if len(rgb) < 3:
        raise FormatError('Material color needs three channels.')
    r, g, b = (linear_to_srgb(float(v)) for v in rgb[:3])
    # Half-up rounding, clamped for float roundoff. No texture or shader baking.
    red = min(31, max(0, int(r * 31 + 0.5)))
    green = min(63, max(0, int(g * 63 + 0.5)))
    blue = min(31, max(0, int(b * 31 + 0.5)))
    return (red << 11) | (green << 5) | blue


def write_atomic(path: str | Path, data: bytes, backup: bool = True) -> Path | None:
    """Validate, write a temporary sibling, back up old bytes, then replace.

    Backup names are unique. A failed backup prevents replacement. Symlinks
    are refused to avoid accidentally replacing an unrelated linked asset.
    Returns the new backup path, if a previous destination was backed up.
    """
    decode(data)
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise FormatError('Refusing to replace a symbolic link. Choose a regular file path.')
    if path.exists() and not path.is_file():
        raise FormatError('The destination exists but is not a regular file.')
    if not path.parent.is_dir():
        raise FormatError('The destination folder does not exist.')
    previous = None
    temp_path = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
        temp_path = Path(temp_name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temp_path, stat.S_IMODE(path.stat().st_mode))
        if path.exists() and backup:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            previous = path.with_name(f'{path.name}.{stamp}.bak')
            with path.open('rb') as source, previous.open('xb') as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
                target.flush()
                os.fsync(target.fileno())
        os.replace(temp_path, path)
        temp_path = None
        return previous
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


# Fixed palette shared by every view and pose. Values are already device colors.
PALETTE = (0, 37, 73, 146, 219, 255, 224, 236, 252, 104, 80, 20, 28, 121, 11, 151)


def rgb(code):
    return ((code >> 5) * 255 // 7, ((code >> 2) & 7) * 255 // 7, (code & 3) * 255 // 3)


def nearest(code):
    r, g, b = rgb(code)
    return min(PALETTE, key=lambda c: sum(w*(a-v)**2 for w,a,v in zip((2,3,1),(r,g,b),rgb(c))))


LOOKUP = bytes(nearest(c) for c in range(256))


def stylize(pixels, mask, width, height, outline=False):
    if len(pixels) != width*height or len(mask) != (width*height+7)//8:
        raise ValueError('Invalid pixel or mask length')
    result = bytearray(len(pixels)); output_mask = bytearray(mask)
    opaque = lambda k: bool(mask[k//8] & (128 >> (k%8)))
    for k, color in enumerate(pixels):
        if opaque(k): result[k] = LOOKUP[color]
        elif outline:
            x,y = k%width,k//width
            neighbors = [ny*width+nx for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if 0<=nx<width and 0<=ny<height]
            if any(opaque(n) for n in neighbors): output_mask[k//8] |= 128 >> (k%8)
    return bytes(result), bytes(output_mask)


import struct
import math
from pathlib import Path
import shutil
import tempfile

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector


def pack_rgba(rgba, width, height, pixel_art=False, outline=False, scene_linear=True):
    """Convert bottom-up RGBA to RGB332/mask; byte PNG buffers are already sRGB."""
    if len(rgba) != width * height * 4:
        raise ValueError('Unexpected rendered pixel count')
    pixels = bytearray(width * height)
    mask = bytearray((width * height + 7) // 8)
    for y in range(height):
        for x in range(width):
            src = ((height - 1 - y) * width + x) * 4
            dst = y * width + x
            if rgba[src + 3] >= 0.5:
                r, g, b = ((linear_to_srgb(rgba[src + k]) if scene_linear else max(0.0, min(1.0, rgba[src + k]))) for k in range(3))
                pixels[dst] = (min(7, int(r * 7 + .5)) << 5 |
                               min(7, int(g * 7 + .5)) << 2 |
                               min(3, int(b * 3 + .5)))
                mask[dst >> 3] |= 0x80 >> (dst & 7)
    if pixel_art:
        return stylize(pixels, mask, width, height, outline)
    return bytes(pixels), bytes(mask)


def sample_frames(start, end, poses, loop=True):
    """Loop ranges exclude the closing frame; one-shot ranges include it."""
    if not 1 <= poses <= 8 or end < start or (poses > 1 and end == start):
        raise ValueError('Choose 1–8 poses and an increasing frame range')
    if poses == 1:
        return [float(start)]
    divisor = poses if loop else poses - 1
    return [start + (end - start) * i / divisor for i in range(poses)]


def set_sample_frame(scene, frame):
    whole = math.floor(frame)
    scene.frame_set(whole, subframe=frame-whole)


def payload_bytes(resolution, directions, poses):
    return directions * poses * (resolution**2 + (resolution**2 + 7)//8)


def bake(context, filepath, resolution=16, directions=8, forward='NEG_Y',
         animated=False, frame_start=1, frame_end=25, poses=4, playback_fps=8.0, loop=True,
         pixel_art=False, outline=False, azimuth=0.0, elevation=0.0):
    if resolution not in (8, 16) or directions not in (1, 4, 8):
        raise ValueError('Unsupported billboard resolution or direction count')
    angles = {'POS_X': 0, 'POS_Y': math.pi / 2, 'NEG_X': math.pi, 'NEG_Y': -math.pi / 2}
    if forward not in angles:
        raise ValueError('Invalid forward axis')
    if not all(math.isfinite(v) for v in (azimuth, elevation)) or not -45 <= elevation <= 45:
        raise ValueError('Camera elevation must be between -45 and 45 degrees')
    source_scene = context.scene
    original_frame = source_scene.frame_current + source_scene.frame_subframe
    frames = sample_frames(frame_start, frame_end, poses, loop) if animated else [original_frame]
    if not math.isfinite(playback_fps) or not 0 < playback_fps <= 60:
        raise ValueError('Playback rate must be greater than zero and at most 60')
    objects = [ob for ob in context.selected_objects if ob.type == 'MESH']
    if not objects:
        raise ValueError('Select the meshes to bake')
    destination = Path(bpy.path.abspath(filepath))
    if destination.suffix.lower() not in ('.bin', '.billboard'):
        destination = destination.with_suffix('.bin')
    if destination.exists():
        raise ValueError('Output file already exists; choose a new name')
    if not destination.parent.is_dir():
        raise ValueError('Output parent directory does not exist')
    scene = None
    meshes, lights, cameras, materials = [], [], [], []
    material_map = {}
    temporary = Path(tempfile.mkdtemp(prefix='.billboard-', dir=destination.parent))
    try:
        scene = bpy.data.scenes.new('Picoware billboard bake')
        deps = context.evaluated_depsgraph_get()
        bounds = []
        for ob in objects:
            if ob.mode == 'EDIT':
                ob.update_from_editmode()
        context.view_layer.update()
        # First evaluate every exported pose for one shared camera volume.
        for frame in frames:
            set_sample_frame(source_scene, frame)
            context.view_layer.update()
            for ob in objects:
                evaluated = ob.evaluated_get(deps)
                bounds.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
        low = Vector(tuple(min(v[k] for v in bounds) for k in range(3)))
        high = Vector(tuple(max(v[k] for v in bounds) for k in range(3)))
        center = (low + high) * .5
        # One projection volume across ALL poses and views prevents frame jitter.
        view_vectors = []
        projected = []
        view_ups = []
        # Blender Y maps to negative engine ground Y: engine view indices
        # advance clockwise in Blender, matching the mesh coordinate conversion.
        for direction in range(directions):
            angle = angles[forward] + math.radians(azimuth) - direction * 2 * math.pi / directions
            elev = math.radians(elevation)
            outward = Vector((math.cos(angle)*math.cos(elev), math.sin(angle)*math.cos(elev), math.sin(elev)))
            right = Vector((-math.sin(angle), math.cos(angle), 0))
            up = outward.cross(right)
            view_vectors.append(outward)
            view_ups.append(up)
            projected.extend(((v-center).dot(right), (v-center).dot(up)) for v in bounds)
        margin = 1 if pixel_art and outline else .5
        bottom = min(y for _, y in projected)
        top = max(y for _, y in projected)
        width = 2 * max(abs(x) for x, _ in projected)
        extent = max(width, top-bottom) / (1 - 2*margin/resolution)
        if not math.isfinite(extent) or extent <= 0:
            raise ValueError('Selected meshes have no finite volume')
        # Align the shared bottom across all poses/views with the ground anchor.
        # Centering a wide, short model would leave a large transparent gap below it.
        vertical_offset = bottom + extent * (.5-margin/resolution)
        targets = [center + up*vertical_offset for up in view_ups]
        if not pixel_art and azimuth == 0 and elevation == 0:
            radius = max(math.hypot(v.x-center.x, v.y-center.y) for v in bounds)
            extent = max(2*radius, high.z-low.z)*1.1
            targets = [Vector((center.x, center.y, low.z+extent*.47)) for _ in view_vectors]
        camera = bpy.data.cameras.new('Billboard camera'); cameras.append(camera)
        cam = bpy.data.objects.new('Billboard camera', camera); scene.collection.objects.link(cam)
        camera.type = 'ORTHO'; camera.ortho_scale = extent; camera.clip_end = extent * 30
        scene.camera = cam
        # Camera-relative illumination gives consistent readable views.
        for name, energy, size in [('Key', 1000, 5), ('Fill', 500, 5)]:
            data = bpy.data.lights.new(name, 'AREA'); lights.append(data)
            light = bpy.data.objects.new(name, data); scene.collection.objects.link(light)
            light.parent = cam; light.location = (-extent*.3 if name=='Key' else extent*.3, extent*.4, extent*.1)
            data.energy = energy * (extent / 5) ** 2; data.shape = 'DISK'; data.size = extent
        world = bpy.data.worlds.new('Billboard world'); scene.world = world
        world.use_nodes = True; world.node_tree.nodes['Background'].inputs[1].default_value = .5
        scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.use_denoising = True
        if pixel_art:
            scene.cycles.samples = 1
            scene.cycles.use_denoising = False
            scene.cycles.filter_width = .01
            scene.cycles.seed = 0
            scene.cycles.use_animated_seed = False
            scene.render.dither_intensity = 0
        scene.render.film_transparent = True
        scene.render.resolution_x = scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        scene.view_settings.view_transform = 'Standard'
        scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
        packed = temporary / 'asset.billboard'
        with packed.open('wb') as stream:
            stream.write(struct.pack('<4sBBBBHHffI', b'PWBB', 1, directions, len(frames),
                                     int(bool(loop)), resolution, resolution, playback_fps, extent,
                                     payload_bytes(resolution, directions, len(frames))))
        for pose, frame in enumerate(frames):
            set_sample_frame(source_scene, frame)
            context.view_layer.update()
            clones = []
            material_map.clear()  # Capture material colors separately at each sampled pose.
            for ob in objects:
                evaluated = ob.evaluated_get(deps)
                mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=deps)
                meshes.append(mesh)
                clone = bpy.data.objects.new(ob.name + ' bake', mesh)
                scene.collection.objects.link(clone)
                clone.matrix_world = evaluated.matrix_world.copy()
                for i, slot in enumerate(ob.material_slots):
                    if slot.link == 'OBJECT' and i < len(mesh.materials):
                        mesh.materials[i] = slot.material
                if pixel_art:
                    # Copy shaders, preserving linked base-color textures. Source materials stay intact.
                    if not mesh.materials:
                        mesh.materials.append(None)
                    for i, original in enumerate(list(mesh.materials)):
                        key = original.as_pointer() if original else 0
                        if key not in material_map:
                            flat = original.copy() if original else bpy.data.materials.new('Pixel default')
                            materials.append(flat); flat.use_nodes = True
                            tree = flat.node_tree
                            output = tree.get_output_node('CYCLES')
                            base = None
                            if original and original.use_nodes and output and output.inputs['Surface'].is_linked:
                                shader = output.inputs['Surface'].links[0].from_node
                                seen = set()
                                while shader.type == 'REROUTE':
                                    if shader.as_pointer() in seen or not shader.inputs[0].is_linked:
                                        raise ValueError('Invalid surface reroute in material ' + original.name)
                                    seen.add(shader.as_pointer())
                                    shader = shader.inputs[0].links[0].from_node
                                if shader.type != 'BSDF_PRINCIPLED':
                                    raise ValueError('Pixel Art needs a Principled shader connected to Material Output: ' + original.name)
                                base = shader.inputs['Base Color']
                            emission = tree.nodes.new('ShaderNodeEmission')
                            emission.inputs['Color'].default_value = base.default_value if base else (original.diffuse_color if original else (.8,.8,.8,1))
                            if base and base.is_linked:
                                tree.links.new(base.links[0].from_socket, emission.inputs['Color'])
                            if output is None: output = tree.nodes.new('ShaderNodeOutputMaterial')
                            tree.links.new(emission.outputs[0], output.inputs['Surface'])
                            material_map[key] = flat
                        mesh.materials[i] = material_map[key]
                clones.append(clone)
            set_sample_frame(scene, frame)
            for direction in range(directions):
                target = targets[direction]
                cam.location = target + view_vectors[direction] * extent * 3
                cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
                stem = ('pose_%02d_view_%02d' % (pose,direction) if animated else 'view_%02d' % direction)
                scene.render.filepath = str(temporary / (stem + '.png'))
                bpy.ops.render.render(write_still=True, scene=scene.name)
                image = bpy.data.images.load(scene.render.filepath, check_existing=False)
                try:
                    pixels, mask = pack_rgba(image.pixels[:], resolution, resolution, pixel_art, outline, scene_linear=image.is_float)
                finally:
                    bpy.data.images.remove(image)
                if not any(mask):
                    raise ValueError('Rendered view is empty')
                with packed.open('ab') as stream:
                    stream.write(pixels)
                    stream.write(mask)
                Path(scene.render.filepath).unlink()
            for clone in clones:
                mesh = clone.data
                bpy.data.objects.remove(clone, do_unlink=True)
                meshes.remove(mesh)
                bpy.data.meshes.remove(mesh)
        metadata = {'format': 'picoware-rgb332-mask', 'width': resolution, 'height': resolution,
                    'directions': directions, 'poses': len(frames), 'forward_axis': forward,
                    'sample_frames': frames, 'playback_fps': playback_fps, 'loop': bool(loop),
                    'view_order': 'camera azimuth decreases clockwise around Blender +Z from forward axis',
                    'world_height': extent, 'pixel_art': pixel_art, 'outline': outline,
                    'azimuth': azimuth, 'elevation': elevation,
                    'mask_order': 'row-major top-down, MSB-first, no row padding',
                    'payload_bytes': payload_bytes(resolution, directions, len(frames))}
        packed.rename(destination)
        return destination, metadata
    finally:
        if scene is not None:
            world = scene.world
            for ob in list(scene.objects): bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.scenes.remove(scene)
            if world is not None and world.users == 0: bpy.data.worlds.remove(world)
        for collection, items in ((bpy.data.meshes,meshes),(bpy.data.cameras,cameras),(bpy.data.lights,lights),(bpy.data.materials,materials)):
            for item in items:
                if item.users == 0: collection.remove(item)
        if temporary.exists(): shutil.rmtree(temporary)
        set_sample_frame(source_scene, original_frame)


class SPRITE3D_OT_export_billboard(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.picoware_billboard'
    bl_label = 'Export Picoware Billboard'
    bl_description = 'Bake selected meshes into one static or animated .bin asset'
    filename_ext = '.bin'
    filter_glob: StringProperty(default='*.bin;*.billboard', options={'HIDDEN'})
    resolution: EnumProperty(name='Resolution', items=[(str(n),str(n)+' x '+str(n),'') for n in (16,8)], default='16')
    directions: EnumProperty(name='Views', items=[(str(n),str(n),'') for n in (1,4,8)], default='8')
    forward: EnumProperty(name='Model Forward', items=[('POS_X','+X',''),('NEG_X','-X',''),('POS_Y','+Y',''),('NEG_Y','-Y','')], default='NEG_Y')
    pixel_art: BoolProperty(name='Pixel Art', default=True, description='Flat base colors, a fixed 16-color RGB332 palette, and crisp pixel edges')
    outline: BoolProperty(name='Dark Outline', default=False, description='Add a one-pixel outside outline; reserves room in the shared framing')
    azimuth: FloatProperty(name='View Angle', default=0, min=-180, max=180, description='Rotate baked views relative to Model Forward; zero preserves engine-facing alignment')
    elevation: FloatProperty(name='Camera Height Angle', default=0, min=-45, max=45, description='Degrees above the model; try 10 to separate overlapping feet')
    animated: BoolProperty(name='Animated', default=False)
    frame_start: IntProperty(name='Frame Start', default=1)
    frame_end: IntProperty(name='Frame End', default=25)
    poses: IntProperty(name='Exported Poses', default=4, min=1, max=8)
    playback_fps: FloatProperty(name='Poses per Second', default=8, min=.1, max=60)
    loop: BoolProperty(name='Loop (Exclude Closing Frame)', default=True)

    use_timeline: BoolProperty(name='Use Timeline Range and Speed', default=True)
    advanced: BoolProperty(name='Advanced', default=False)

    def settings(self, context):
        if self.animated and self.use_timeline:
            start, end = context.scene.frame_start, context.scene.frame_end
            frames = sample_frames(start,end,self.poses,self.loop)
            source_fps = context.scene.render.fps / context.scene.render.fps_base
            intervals = self.poses if self.loop else max(1,self.poses-1)
            rate = intervals * source_fps / max(1,end-start)
            if not .1 <= rate <= 60:
                raise ValueError('Timeline speed is outside 0.1–60 poses/sec; adjust range or use Advanced timing')
            return start,end,rate
        return self.frame_start,self.frame_end,self.playback_fps

    def check(self, context):
        if Path(self.filepath).suffix.lower() in ('.bin', '.billboard'):
            return False
        return ExportHelper.check(self, context)

    def invoke(self, context, event):
        if not self.properties.is_property_set('frame_start'):
            self.frame_start = context.scene.frame_start
        if not self.properties.is_property_set('frame_end'):
            self.frame_end = context.scene.frame_end
        if not self.properties.is_property_set('forward'):
            self.forward = context.scene.get('picoware_billboard_forward','NEG_Y')
        return ExportHelper.invoke(self, context, event)

    def draw(self, context):
        layout = self.layout
        layout.prop(self,'pixel_art')
        layout.prop(self,'resolution')
        if self.pixel_art:
            layout.prop(self,'outline')
        layout.prop(self,'azimuth')
        layout.prop(self,'elevation')
        layout.prop(self,'animated')
        if self.animated:
            layout.prop(self,'poses')
            layout.prop(self,'loop')
            try:
                start,end,rate = self.settings(context)
                frames = sample_frames(start,end,self.poses,self.loop)
                layout.label(text='Timeline %g–%g · %.2f poses/sec' % (start,end,rate))
            except ValueError as exc:
                layout.label(text=str(exc),icon='ERROR')
            layout.label(text='For loops, end with the same pose you started with')
        count = self.poses if self.animated else 1
        size = payload_bytes(int(self.resolution),int(self.directions),count)
        layout.label(text='Single .bin asset file')
        layout.label(text='Image + mask payload: %.1f KiB' % (size/1024))
        layout.label(text='16 x 16 default; 8 x 8 optional')
        layout.prop(self,'advanced',icon='PREFERENCES')
        if self.advanced:
            for name in ('directions','forward'):
                layout.prop(self,name)
            if self.animated:
                layout.prop(self,'use_timeline')
                if not self.use_timeline:
                    for name in ('frame_start','frame_end','playback_fps'):
                        layout.prop(self,name)
            layout.label(text='Memory excludes loading copies and object overhead')

    def execute(self, context):
        try:
            start,end,rate = self.settings(context)
            path, info = bake(context, self.filepath, int(self.resolution), int(self.directions), self.forward,
                              self.animated,start,end,self.poses,rate,self.loop,
                              self.pixel_art,self.outline,self.azimuth,self.elevation)
            self.report({'INFO'}, 'Exported %d views x %d poses (%d bytes) to %s' % (info['directions'],info['poses'],info['payload_bytes'],path))
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


import hashlib
import math
from pathlib import Path
import re
import traceback

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper


ATTR_COLOR = 's3d_color565'
ATTR_EXTRA = 's3d_extra16'
ATTR_VALID = 's3d_metadata_valid'
SOURCE_PATH = 'sprite3d_source_path'
SOURCE_AXES = 'sprite3d_source_axes'
SOURCE_SCALE = 'sprite3d_import_scale'
SOURCE_HASH = 'sprite3d_source_sha256'
MAT_COLOR = 'sprite3d_color565'
MAT_EXTRA = 'sprite3d_extra16'
OLD_MATERIAL = re.compile(r'^s3d_([0-9a-fA-F]{8})(?:\.\d+)?$')

AXES_IMPORT = (
    ('Y_UP', 'Source Y Up (knight)', 'Convert source (X, Y, Z) to Blender (X, -Z, Y)'),
    ('BLENDER', 'Already Blender Z Up', 'Keep coordinates in their original axes'),
)
AXES_EXPORT = (
    ('AUTO', 'Automatic / Match Import', 'Use each object\'s saved import axes and undo its import scale; new meshes use source Y Up'),
) + AXES_IMPORT
COLOR_MODES = (
    ('AUTO', 'Material Colors / Keep Extra Data', 'Read flat Principled Base Color as RGB565; preserve wireframe and padding per face; missing materials retain original data'),
    ('PRESERVE', 'Preserve Original Face Data', 'Ignore material edits and assignments; preserve both original uint16 fields per face'),
    ('MATERIAL', 'Require Material Colors', 'Every face must have a supported flat-color material; preserve wireframe and padding per face'),
)


def _material_word(material):
    """Read our properties; accept the earlier OBJ converter's material names."""
    if material is None:
        return None
    if MAT_COLOR in material and MAT_EXTRA in material:
        color, extra = material[MAT_COLOR], material[MAT_EXTRA]
        if isinstance(color, int) and isinstance(extra, int) and 0 <= color <= 65535 and 0 <= extra <= 65535:
            return color, extra
        raise FormatError(f'Material {material.name!r} has invalid Sprite3D custom data.')
    match = OLD_MATERIAL.fullmatch(material.name)
    if match:
        word = int(match.group(1), 16)
        return word & 65535, word >> 16
    return None


def _principled(material):
    """Find the Principled shader directly feeding the active material output.

    Reroutes are accepted. Shader groups/mixes and procedural colors are not
    approximated silently: this file format only stores a flat face color.
    """
    tree = material.node_tree
    if tree is None:
        return None
    outputs = [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL']
    output = next((n for n in outputs if n.is_active_output), outputs[0] if outputs else None)
    if output is None or not output.inputs['Surface'].is_linked:
        return None
    node = output.inputs['Surface'].links[0].from_node
    visited = set()
    while node.type == 'REROUTE' and node.as_pointer() not in visited:
        visited.add(node.as_pointer())
        if not node.inputs[0].is_linked:
            return None
        node = node.inputs[0].links[0].from_node
    return node if node.type == 'BSDF_PRINCIPLED' else None


def _flat_material_color(material):
    if material.node_tree is None or getattr(material, 'use_nodes', True) is False:
        return tuple(material.diffuse_color[:3])
    shader = _principled(material)
    if shader is None:
        raise FormatError(
            f'Material {material.name!r}: use a Principled BSDF connected to Material Output, '
            'or export with Preserve Original Face Data.')
    socket = shader.inputs.get('Base Color')
    if socket is None or socket.is_linked:
        raise FormatError(
            f'Material {material.name!r}: linked/procedural Base Color cannot be exported. '
            'Use a solid Base Color or Preserve Original Face Data; textures are not baked.')
    return tuple(socket.default_value[:3])


def _new_material(color, extra):
    material = bpy.data.materials.new(f'S3D_{color:04X}_{extra:04X}')
    linear = rgb565_to_linear(color)
    material.diffuse_color = (*linear, 1.0)
    # Blender versions with the switch need it; versions where nodes are always
    # enabled may expose it as read-only or remove it.
    if hasattr(material, 'use_nodes'):
        try:
            material.use_nodes = True
        except (AttributeError, TypeError):
            pass
    if material.node_tree is None:
        bpy.data.materials.remove(material)
        raise FormatError('Blender could not create the material node tree.')
    tree = material.node_tree
    tree.nodes.clear()
    shader = tree.nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value = (*linear, 1.0)
    shader.inputs['Roughness'].default_value = 1.0
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    shader.location = (-240, 0)
    material[MAT_COLOR] = color
    material[MAT_EXTRA] = extra
    material['sprite3d_color_note'] = 'RGB565 color; extra low byte is wireframe, high byte is preserved padding'
    return material


def _dispose_object(obj):
    """Remove only this object's newly-created unused data; never scene orphans."""
    mesh = obj.data
    materials = list(mesh.materials)
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    for material in materials:
        if material is not None and material.users == 0:
            bpy.data.materials.remove(material)


def load_sprite(context, filepath, *, axes='Y_UP', scale=1.0, weld=True):
    path = Path(bpy.path.abspath(str(filepath))).expanduser().resolve()
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    triangles = decode(data)
    vertices, faces = build_mesh_arrays(triangles, axes, scale, weld)
    mesh = bpy.data.meshes.new(path.stem)
    obj = None
    made_materials = []
    try:
        mesh.from_pydata(vertices, [], faces)
        # Do not run mesh.validate(), weld by distance, recalculate winding, or
        # reorder triangles: these may discard/reorder valid original records.
        mesh.update()
        colors = mesh.attributes.new(name=ATTR_COLOR, type='INT', domain='FACE')
        extras = mesh.attributes.new(name=ATTR_EXTRA, type='INT', domain='FACE')
        valid = mesh.attributes.new(name=ATTR_VALID, type='INT', domain='FACE')
        # Re-fetch after adding attributes; collection storage may be reallocated.
        colors = mesh.attributes[ATTR_COLOR]
        extras = mesh.attributes[ATTR_EXTRA]
        valid = mesh.attributes[ATTR_VALID]
        colors.data.foreach_set('value', [t.color for t in triangles])
        extras.data.foreach_set('value', [t.extra for t in triangles])
        valid.data.foreach_set('value', [1] * len(triangles))
        slots = {}
        for polygon, triangle in zip(mesh.polygons, triangles):
            key = (triangle.color, triangle.extra)
            if key not in slots:
                material = _new_material(*key)
                made_materials.append(material)
                slots[key] = len(mesh.materials)
                mesh.materials.append(material)
            polygon.material_index = slots[key]
            polygon.use_smooth = False
        obj = bpy.data.objects.new(path.stem, mesh)
        context.collection.objects.link(obj)
        obj[SOURCE_PATH] = str(path)
        obj[SOURCE_AXES] = axes
        obj[SOURCE_SCALE] = float(scale)
        obj[SOURCE_HASH] = hashlib.sha256(data).hexdigest()
        obj['sprite3d_original_triangle_count'] = len(triangles)
        obj['sprite3d_format'] = 'headerless_le_9f_2u16_v1'
        return obj
    except Exception:
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        for material in made_materials:
            if material.users == 0:
                bpy.data.materials.remove(material)
        raise


def _face_metadata(mesh, polygon_index):
    attrs = [mesh.attributes.get(name) for name in (ATTR_COLOR, ATTR_EXTRA, ATTR_VALID)]
    if any(a is None or a.domain != 'FACE' or a.data_type != 'INT' for a in attrs):
        return None
    if attrs[2].data[polygon_index].value != 1:
        return None
    color, extra = (a.data[polygon_index].value for a in attrs[:2])
    if not 0 <= color <= 65535 or not 0 <= extra <= 65535:
        raise FormatError(f'Face {polygon_index + 1} has invalid Sprite3D data.')
    return color, extra


def _is_identity(matrix):
    return all(matrix[r][c] == (1.0 if r == c else 0.0) for r in range(4) for c in range(4))


def collect_triangles(context, objects, *, apply_modifiers=True, apply_transform=True,
                      axes='AUTO', export_scale=1.0, color_mode='AUTO', default_extra=1,
                      fix_mirrors=True):
    """Extract without editing the original mesh, modifiers, or selection."""
    check_scale(export_scale)
    objects = list(objects)
    if not objects:
        raise FormatError('Select at least one mesh object to export.')
    for obj in objects:
        if obj.type != 'MESH':
            raise FormatError(f'{obj.name!r} is not a mesh.')
        if obj.mode == 'EDIT':
            obj.update_from_editmode()
    context.view_layer.update()
    depsgraph = context.evaluated_depsgraph_get()
    result, warnings = [], set()
    material_colors = {}
    for obj in objects:
        source_axes = obj.get(SOURCE_AXES, 'Y_UP') if axes == 'AUTO' else axes
        import_scale = float(obj.get(SOURCE_SCALE, 1.0)) if axes == 'AUTO' else 1.0
        check_scale(import_scale)
        evaluated = None
        if apply_modifiers:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        else:
            mesh = obj.data
        try:
            if mesh is None:
                raise FormatError(f'{obj.name!r}: no evaluated mesh could be obtained.')
            mesh.calc_loop_triangles()
            world = (evaluated.matrix_world if evaluated is not None else obj.matrix_world).copy()
            transform = apply_transform and not _is_identity(world)
            mirrored = apply_transform and world.to_3x3().determinant() < 0
            if any(mod.type == 'NODES' and mod.show_viewport for mod in obj.modifiers) and apply_modifiers:
                warnings.add('Geometry Nodes: only realized mesh geometry is exported; realize instances first')
            vertex_cache = {}
            no_metadata = 0
            for triangle in mesh.loop_triangles:
                polygon = mesh.polygons[triangle.polygon_index]
                face_data = _face_metadata(mesh, polygon.index)
                if face_data is None:
                    no_metadata += 1
                # Object-linked material overrides take precedence; evaluated
                # mesh slots also support materials created by modifiers.
                material = mesh.materials[polygon.material_index] if polygon.material_index < len(mesh.materials) else None
                if polygon.material_index < len(obj.material_slots):
                    slot = obj.material_slots[polygon.material_index]
                    if slot.link == 'OBJECT':
                        material = slot.material
                imported_material = _material_word(material)
                extra = (face_data[1] if face_data is not None else
                         imported_material[1] if imported_material is not None else default_extra)
                if color_mode == 'PRESERVE':
                    preserved = face_data if face_data is not None else imported_material
                    if preserved is None:
                        raise FormatError(
                            f'{obj.name!r}, face {polygon.index + 1}: no original data to preserve. '
                            'Assign an imported material or choose Material Colors for new geometry.')
                    color = preserved[0]
                elif material is not None:
                    key = material.as_pointer()
                    if key not in material_colors:
                        material_colors[key] = linear_to_rgb565(_flat_material_color(material))
                    color = material_colors[key]
                elif color_mode == 'MATERIAL':
                    raise FormatError(f'{obj.name!r}, face {polygon.index + 1}: no material assigned.')
                elif face_data is not None:
                    color = face_data[0]
                else:
                    color = 0xFFFF
                    warnings.add('Faces without materials/original colors exported as white')
                indices = list(triangle.vertices)
                if mirrored and fix_mirrors:
                    indices[1], indices[2] = indices[2], indices[1]
                coordinates = []
                for index in indices:
                    if index not in vertex_cache:
                        value = mesh.vertices[index].co
                        if transform:
                            value = world @ value
                        xyz = blender_to_source(value, source_axes, import_scale)
                        if export_scale != 1.0:
                            xyz = tuple(v * export_scale for v in xyz)
                        vertex_cache[index] = xyz
                    coordinates.extend(vertex_cache[index])
                result.append(Triangle(tuple(coordinates), color, extra))
                if len(result) > MAX_TRIANGLES:
                    raise FormatError(f'Safety limit: {MAX_TRIANGLES:,} triangles.')
            if no_metadata:
                warnings.add(
                    f'{obj.name}: {no_metadata} triangles lack original face data; '
                    'wireframe and padding use imported material data or the New Face Wireframe setting')
        finally:
            if evaluated is not None:
                evaluated.to_mesh_clear()
    if not result:
        raise FormatError('The selected meshes contain no triangle faces.')
    return result, sorted(warnings)


def export_sprite(context, objects, filepath, *, backup=True, **settings):
    triangles, warnings = collect_triangles(context, objects, **settings)
    data = encode(triangles)
    # Validate the complete result before touching an existing output.
    path = Path(bpy.path.abspath(str(filepath))).expanduser().absolute()
    backup_path = write_atomic(path, data, backup=backup)
    return len(triangles), warnings, backup_path, hashlib.sha256(data).hexdigest()


def _report_export(operator, count, warnings, backup_path):
    for warning in warnings:
        print('Sprite3D warning:', warning)
    if warnings:
        operator.report({'WARNING'}, '; '.join(warnings)[:900])
    suffix = ' (backup created)' if backup_path is not None else ''
    operator.report({'INFO'}, f'Exported {count:,} triangles{suffix}')


def _error(operator, exc):
    # Keep an actionable short UI error; put the full exception in the console.
    traceback.print_exc()
    operator.report({'ERROR'}, str(exc)[:900])
    return {'CANCELLED'}


class SPRITE3D_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.sprite3d_mesh'
    bl_label = 'Import Sprite3D Mesh'
    bl_description = 'Import the headerless 40-byte-per-triangle layout used by knight.sprite3d'
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = '.bin'
    filter_glob: StringProperty(default='*.bin;*.sprite3d', options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    axes: EnumProperty(name='File Coordinates', items=AXES_IMPORT, default='Y_UP')
    scale: FloatProperty(name='Import Scale', default=1.0, min=0.000001, max=1000000.0)
    weld: BoolProperty(name='Merge Exact Duplicate Positions', default=True,
                      description='Makes connected editing easier; may join touching surfaces. Disable to keep every triangle independent')
    material_preview: BoolProperty(name='Show Material Colors', default=True,
                                  description='Switch 3D viewports to Material Preview so Base Color edits are visible')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Headerless triangle mesh format only', icon='INFO')
        layout.prop(self, 'axes')
        layout.prop(self, 'scale')
        layout.prop(self, 'weld')
        layout.prop(self, 'material_preview')

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, 'Switch to Object Mode before importing.')
            return {'CANCELLED'}
        paths = [str(Path(self.directory) / entry.name) for entry in self.files] if self.files else [self.filepath]
        created = []
        try:
            for path in paths:
                created.append(load_sprite(context, path, axes=self.axes, scale=self.scale, weld=self.weld))
        except Exception as exc:
            for obj in created:
                _dispose_object(obj)
            return _error(self, exc)
        for obj in list(context.selected_objects):
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        context.view_layer.objects.active = created[-1]
        if self.material_preview:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.spaces.active.shading.color_type = 'MATERIAL'
                        area.spaces.active.shading.type = 'MATERIAL'
        count = sum(len(obj.data.polygons) for obj in created)
        self.report({'INFO'}, f'Imported {len(created)} mesh(es), {count:,} triangles')
        return {'FINISHED'}


class SPRITE3D_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.sprite3d_mesh'
    bl_label = 'Export Sprite3D Mesh'
    bl_description = 'Export static geometry to the knight.sprite3d binary layout'
    bl_options = {'PRESET'}
    filename_ext = '.bin'
    filter_glob: StringProperty(default='*.bin;*.sprite3d', options={'HIDDEN'})
    selected_only: BoolProperty(name='Selected Objects Only', default=True)
    apply_modifiers: BoolProperty(name='Apply Modifiers', default=True,
                                 description='Export the evaluated mesh at the current frame; the modifier stack is not changed')
    apply_transform: BoolProperty(name='Apply Object Transforms', default=True,
                                 description='Include world-space location, rotation, scale and parenting')
    axes: EnumProperty(name='File Coordinates', items=AXES_EXPORT, default='AUTO')
    export_scale: FloatProperty(name='Additional Export Scale', default=1.0, min=0.000001, max=1000000.0)
    color_mode: EnumProperty(name='Colors / Data', items=COLOR_MODES, default='AUTO')
    default_wireframe: BoolProperty(name='New Face Wireframe', default=True,
                                    description='Draw outlines on new faces without imported data; padding is zero')
    fix_mirrors: BoolProperty(name='Correct Mirrored Winding', default=True,
                             description='Reverse winding when an applied object transform has a negative determinant')
    backup: BoolProperty(name='Back Up Existing File', default=True,
                         description='Make a unique timestamped .bak before replacing a file; failure stops the export')

    def check(self, context):
        if Path(self.filepath).suffix.lower() in ('.bin', '.sprite3d'):
            return False
        return ExportHelper.check(self, context)

    def invoke(self, context, event):
        if not self.filepath:
            obj = context.active_object
            source = obj.get(SOURCE_PATH) if obj is not None else None
            if source:
                path = Path(source)
                self.filepath = str(path.with_name(path.stem + '_edited.bin'))
            else:
                self.filepath = bpy.path.clean_name(obj.name if obj else 'mesh') + '.bin'
        return ExportHelper.invoke(self, context, event)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'selected_only')
        layout.prop(self, 'apply_modifiers')
        layout.prop(self, 'apply_transform')
        layout.prop(self, 'axes')
        layout.prop(self, 'export_scale')
        layout.prop(self, 'color_mode')
        layout.prop(self, 'default_wireframe')
        layout.prop(self, 'fix_mirrors')
        layout.prop(self, 'backup')
        layout.label(text=f'Picoware limit: {MAX_TRIANGLES:,} triangles', icon='INFO')
        layout.label(text='No textures, rigs or animation data')

    def execute(self, context):
        self.check(context)
        objects = list(context.selected_objects) if self.selected_only else list(context.scene.objects)
        objects = sorted((obj for obj in objects if obj.type == 'MESH'), key=lambda obj: obj.name)
        try:
            count, warnings, backup_path, _digest = export_sprite(
                context, objects, self.filepath, backup=self.backup,
                apply_modifiers=self.apply_modifiers, apply_transform=self.apply_transform,
                axes=self.axes, export_scale=self.export_scale, color_mode=self.color_mode,
                default_extra=int(self.default_wireframe), fix_mirrors=self.fix_mirrors)
            _report_export(self, count, warnings, backup_path)
            return {'FINISHED'}
        except Exception as exc:
            return _error(self, exc)


class SPRITE3D_OT_save_source(bpy.types.Operator):
    bl_idname = 'sprite3d.save_source'
    bl_label = 'Save Back to Source'
    bl_description = 'Export the active mesh to its imported path, always making a backup before replacing existing data'
    bl_options = set()  # External writes are not undoable.
    color_mode: EnumProperty(name='Colors / Data', items=COLOR_MODES, default='AUTO')
    apply_modifiers: BoolProperty(name='Apply Modifiers', default=True)
    apply_transform: BoolProperty(name='Apply Object Transforms', default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and bool(obj.get(SOURCE_PATH))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        obj = context.active_object
        layout = self.layout
        layout.label(text='Replace the source file for the ACTIVE mesh only.', icon='ERROR')
        layout.label(text=Path(obj[SOURCE_PATH]).name)
        layout.label(text='A unique .bak copy will be made first.')
        layout.label(text='File writes cannot be undone with Ctrl+Z.')
        layout.prop(self, 'color_mode')
        layout.prop(self, 'apply_modifiers')
        layout.prop(self, 'apply_transform')

    def execute(self, context):
        obj = context.active_object
        try:
            path = Path(bpy.path.abspath(obj[SOURCE_PATH]))
            old_hash = obj.get(SOURCE_HASH)
            if path.is_file() and old_hash:
                with path.open('rb') as stream:
                    current_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
                if current_hash != old_hash:
                    raise FormatError(
                        'The source file changed on disk since import/last save. '
                        'Use File > Export to a different name, or re-import the current source.')
            count, warnings, backup_path, digest = export_sprite(
                context, [obj], path, backup=True, axes='AUTO',
                color_mode=self.color_mode, apply_modifiers=self.apply_modifiers,
                apply_transform=self.apply_transform)
            obj[SOURCE_HASH] = digest
            _report_export(self, count, warnings, backup_path)
            return {'FINISHED'}
        except Exception as exc:
            return _error(self, exc)


class SPRITE3D_PT_tools(bpy.types.Panel):
    bl_label = 'Sprite3D Mesh'
    bl_idname = 'SPRITE3D_PT_tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sprite3D'

    def draw(self, context):
        layout = self.layout
        layout.operator('import_scene.sprite3d_mesh', text='Import Mesh (.bin / .sprite3d)', icon='IMPORT')
        op = layout.operator('export_scene.sprite3d_mesh', text='Export Selected...', icon='EXPORT')
        op.selected_only = True
        obj = context.active_object
        if obj is not None and obj.type == 'MESH':
            box = layout.box()
            box.label(text=obj.name, icon='MESH_DATA')
            box.label(text=f'Base mesh: {len(obj.data.polygons):,} faces')
            source = obj.get(SOURCE_PATH)
            if source:
                box.label(text='Source: ' + Path(source).name)
                box.operator('sprite3d.save_source', icon='FILE_TICK')
            material = obj.active_material
            if material is not None:
                shader = _principled(material)
                if shader is not None:
                    socket = shader.inputs.get('Base Color')
                    if socket is not None and not socket.is_linked:
                        box.label(text='Active Material: ' + material.name)
                        box.prop(socket, 'default_value', text='Face Color')
            box.label(text='Picoware RGB565 triangle colors', icon='INFO')
        layout.separator()
        layout.operator('export_scene.picoware_billboard', text='Export Billboard', icon='RENDER_STILL')
        animated = layout.operator('export_scene.picoware_billboard', text='Export Animated Billboard', icon='RENDER_ANIMATION')
        animated.animated = True
        layout.label(text='Animate on timeline, select meshes, then export')


def _menu_import(self, context):
    self.layout.operator(SPRITE3D_OT_import.bl_idname, text='Sprite3D Mesh (.bin / .sprite3d)')


def _menu_export(self, context):
    self.layout.operator(SPRITE3D_OT_export.bl_idname, text='Sprite3D Mesh (.bin / .sprite3d)')
    self.layout.operator(SPRITE3D_OT_export_billboard.bl_idname, text='Picoware Billboard (.bin)')
    animated = self.layout.operator(SPRITE3D_OT_export_billboard.bl_idname, text='Picoware Animated Billboard (.bin)')
    animated.animated = True


CLASSES = (SPRITE3D_OT_import, SPRITE3D_OT_export, SPRITE3D_OT_export_billboard,
           SPRITE3D_OT_save_source, SPRITE3D_PT_tools)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(_menu_import)
    bpy.types.TOPBAR_MT_file_export.append(_menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_import)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
