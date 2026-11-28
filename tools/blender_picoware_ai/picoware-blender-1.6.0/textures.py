# SPDX-License-Identifier: GPL-3.0-or-later
"""Sprite3D texture bundles and isolated Blender atlas baking."""
import hashlib
import json
import math
from pathlib import Path
import struct

import bpy


def bundle_paths(path):
    path = Path(path)
    return [path, Path(str(path) + '.uv'), Path(str(path) + '.rgb565'),
            Path(str(path) + '.json')]


def write_bundle(path, mesh, uvs, pixels, size, backup):
    from . import FormatError, write_atomic
    paths = bundle_paths(path)
    metadata = {'version': 1, 'width': size, 'height': size,
                'format': 'RGB565_LE', 'uv_origin': 'top-left',
                'triangles': len(mesh) // 40,
                'sha256': {p.name: hashlib.sha256(data).hexdigest()
                           for p, data in zip(paths, (mesh, uvs, pixels))}}
    payloads = [mesh, uvs, pixels, (json.dumps(metadata, indent=2) + '\n').encode()]
    # Validate every destination before replacing any member. Keep originals for
    # rollback even when the user disables persistent timestamped backups.
    originals = {}
    for p in paths:
        if p.is_symlink() or (p.exists() and not p.is_file()):
            raise FormatError('Bundle destination must be a regular file: ' + str(p))
        originals[p] = p.read_bytes() if p.exists() else None
    completed, first_backup = [], None
    try:
        for p, data in zip(paths, payloads):
            saved = write_atomic(p, data, backup=backup, validate_mesh=(p == paths[0]))
            if p == paths[0]:
                first_backup = saved
            completed.append(p)
    except Exception:
        for p in reversed(completed):
            old = originals[p]
            if old is None:
                p.unlink()
            else:
                write_atomic(p, old, backup=False, validate_mesh=False)
        raise
    return first_backup


def read_bundle(path, count):
    from . import FormatError
    paths = bundle_paths(path)
    if not paths[3].exists():
        return None
    meta = json.loads(paths[3].read_text())
    w, h = meta.get('width'), meta.get('height')
    if (meta.get('version') != 1 or meta.get('format') != 'RGB565_LE'
            or meta.get('uv_origin') != 'top-left' or meta.get('triangles') != count
            or type(w) is not int or type(h) is not int or not 1 <= w <= 2048 or not 1 <= h <= 2048):
        raise FormatError('Invalid Sprite3D texture bundle metadata.')
    data = [p.read_bytes() for p in paths[:3]]
    if len(data[1]) != count * 24 or len(data[2]) != w * h * 2:
        raise FormatError('Texture/UV size does not match mesh or dimensions.')
    for p, blob in zip(paths, data):
        if hashlib.sha256(blob).hexdigest() != meta.get('sha256', {}).get(p.name):
            raise FormatError('Texture bundle changed or is incomplete: ' + p.name)
    uvs = list(struct.iter_unpack('<6f', data[1]))
    if not all(math.isfinite(v) for uv in uvs for v in uv):
        raise FormatError('Non-finite texture coordinates.')
    return w, h, uvs, data[2]


def attach_bundle(mesh, bundle):
    from . import rgb565_to_linear
    w, h, uvs, pixels = bundle
    layer = mesh.uv_layers.new(name='Picoware UV')
    for polygon, values in zip(mesh.polygons, uvs):
        for corner, loop in enumerate(polygon.loop_indices):
            layer.data[loop].uv = (values[corner * 2], 1 - values[corner * 2 + 1])
    image = bpy.data.images.new(mesh.name + ' texture', width=w, height=h, float_buffer=True)
    rgba = [0.] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            color = struct.unpack_from('<H', pixels, (y * w + x) * 2)[0]
            offset = ((h - 1 - y) * w + x) * 4
            rgba[offset:offset + 4] = (*rgb565_to_linear(color), 1.)
    image.pixels.foreach_set(rgba)
    image.pack()
    for material in mesh.materials:
        tree = material.node_tree
        shader = next(n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED')
        texture = tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        texture.interpolation = 'Closest'
        texture.extension = 'EXTEND'
        # Preserve the mesh tint in the Blender preview.
        multiply = tree.nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        multiply.inputs[2].default_value = shader.inputs['Base Color'].default_value
        tree.links.new(texture.outputs['Color'], multiply.inputs[1])
        tree.links.new(multiply.outputs[0], shader.inputs['Base Color'])
    return image


def bake_export(context, objects, filepath, *, texture_size=128, backup=True, **settings):
    from . import (FormatError, collect_triangles, encode, linear_to_rgb565,
                  _principled, SOURCE_AXES, SOURCE_SCALE)
    if texture_size not in (32, 64, 128, 256, 512, 1024, 2048):
        raise FormatError('Choose a power-of-two atlas size from 32 to 2048.')
    objects = list(objects)
    if not objects or any(o.type != 'MESH' for o in objects):
        raise FormatError('Select mesh objects to export.')
    if any(o.mode != 'OBJECT' for o in objects):
        raise FormatError('Switch to Object Mode before baking textures.')
    scene = None
    original_scene = context.window.scene
    clones, meshes, materials = [], [], []
    image = None
    try:
        context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        scene = bpy.data.scenes.new('Picoware texture bake')
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 1
        image = bpy.data.images.new('Picoware atlas', width=texture_size, height=texture_size,
                                    alpha=False, float_buffer=True)
        image.generated_color = (0, 0, 0, 1)
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph) if settings.get('apply_modifiers', True) else obj
            mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
            meshes.append(mesh)
            clone = bpy.data.objects.new(obj.name + ' texture export', mesh)
            clones.append(clone)
            scene.collection.objects.link(clone)
            clone.matrix_world = evaluated.matrix_world.copy()
            clone[SOURCE_AXES] = obj.get(SOURCE_AXES, 'Y_UP')
            clone[SOURCE_SCALE] = obj.get(SOURCE_SCALE, 1.)
            # Preserve the original render UV layer for source image textures.
            original_uv = mesh.uv_layers.active
            if original_uv is None:
                raise FormatError(obj.name + ': create a UV map before textured export.')
            atlas = mesh.uv_layers.new(name='Picoware Atlas')
            mesh.uv_layers.active = atlas
            original_uv.active_render = True
            if not mesh.materials:
                mesh.materials.append(None)
            for i, original in enumerate(list(mesh.materials)):
                if i < len(obj.material_slots) and obj.material_slots[i].link == 'OBJECT':
                    original = obj.material_slots[i].material
                material = original.copy() if original else bpy.data.materials.new('White texture material')
                materials.append(material)
                material.use_nodes = True
                tree = material.node_tree
                shader = _principled(material)
                if shader is None:
                    raise FormatError(obj.name + ': texture baking requires Principled Base Color.')
                base = shader.inputs['Base Color']
                if not original or not original.use_nodes:
                    base.default_value = original.diffuse_color if original else (1, 1, 1, 1)
                emission = tree.nodes.new('ShaderNodeEmission')
                emission.inputs['Color'].default_value = base.default_value
                if base.is_linked:
                    tree.links.new(base.links[0].from_socket, emission.inputs['Color'])
                output = tree.get_output_node('CYCLES')
                tree.links.new(emission.outputs[0], output.inputs['Surface'])
                target = tree.nodes.new('ShaderNodeTexImage')
                target.image = image
                for node in tree.nodes:
                    node.select = False
                target.select = True
                tree.nodes.active = target
                mesh.materials[i] = material
        context.window.scene = scene
        layer = scene.view_layers[0]
        with context.temp_override(scene=scene, view_layer=layer):
            for clone in clones:
                clone.select_set(True, view_layer=layer)
            layer.objects.active = clones[0]
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(island_margin=0.04)
            finally:
                bpy.ops.object.mode_set(mode='OBJECT')
            # All selected objects share one packed atlas, but bake independently
            # without clearing pixels produced by earlier objects.
            for clone in clones:
                for other in clones:
                    other.select_set(other == clone, view_layer=layer)
                layer.objects.active = clone
                bpy.ops.object.bake(type='EMIT', use_clear=False, margin=2,
                                    uv_layer=clone.data.uv_layers.active.name)
            uv_values = []
            options = dict(settings, apply_modifiers=False, color_mode='TEXTURE',
                           texture_uvs=uv_values)
            triangles, warnings = collect_triangles(context, clones, **options)
        mesh_data = encode(triangles)
        uv_data = b''.join(struct.pack('<6f', *uv) for uv in uv_values)
        rgba = list(image.pixels)
        pixels = bytearray()
        for y in range(texture_size - 1, -1, -1):
            for x in range(texture_size):
                offset = (y * texture_size + x) * 4
                pixels.extend(struct.pack('<H', linear_to_rgb565(rgba[offset:offset + 3])))
        path = Path(bpy.path.abspath(str(filepath))).expanduser().absolute()
        saved = write_bundle(path, mesh_data, uv_data, pixels, texture_size, backup)
        warnings.append('Texture is opaque RGB565 Base Color; lighting and transparency are not exported')
        return len(triangles), warnings, saved, hashlib.sha256(mesh_data).hexdigest()
    finally:
        context.window.scene = original_scene
        for clone in clones:
            bpy.data.objects.remove(clone, do_unlink=True)
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        for material in materials:
            bpy.data.materials.remove(material)
        if image is not None:
            bpy.data.images.remove(image)
        if scene is not None:
            bpy.data.scenes.remove(scene)
