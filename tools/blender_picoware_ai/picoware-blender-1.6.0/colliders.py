# SPDX-License-Identifier: GPL-3.0-or-later
"""Authored upright collision boxes; independent of visible asset geometry."""
import math
import struct
from pathlib import Path
import bpy
from mathutils import Vector

MAX_BOXES = 4


def is_collider(obj):
    return obj.name.startswith('COLLIDER_')


def split_objects(objects, *, enforce_limit=True):
    objects = list(objects)
    helpers = {o for o in objects if is_collider(o)}
    visible = [o for o in objects if not is_collider(o)]
    for obj in visible:
        helpers.update(o for o in obj.children_recursive if is_collider(o))
    helpers = sorted(helpers, key=lambda o: o.name)
    if enforce_limit and len(helpers) > MAX_BOXES:
        raise ValueError(f'Asset has {len(helpers)} collision boxes; maximum is {MAX_BOXES}. Remove or combine boxes.')
    return visible, helpers


def encode_boxes(context, visible, helpers, **settings):
    from . import blender_to_source
    context.view_layer.update()
    if len(helpers) > MAX_BOXES:
        raise ValueError('Maximum four collision boxes per asset')
    records = []
    axes = settings.get('axes', 'AUTO')
    if helpers and not settings.get('apply_transform', True):
        raise ValueError('Collision boxes require Apply Object Transforms.')
    conventions = {(o.get('sprite3d_source_axes', 'Y_UP'), float(o.get('sprite3d_import_scale', 1))) for o in visible}
    if axes == 'AUTO':
        if len(conventions) > 1 and helpers:
            raise ValueError('Collision boxes require one shared axis and import scale convention.')
        axes, import_scale = next(iter(conventions), ('Y_UP', 1.0))
    else:
        import_scale = 1.0
    if helpers and axes != 'Y_UP':
        raise ValueError('Collision boxes require Y Up export axes.')
    scale = settings.get('export_scale', 1.0) / import_scale
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Collision box export scale must be positive and finite.')
    for obj in helpers:
        if obj.type != 'MESH' or obj.modifiers or len(obj.data.vertices) != 8:
            raise ValueError(f'{obj.name}: use an unmodified cube for collision.')
        if obj.mode == 'EDIT':
            obj.update_from_editmode()
        points = [v.co for v in obj.data.vertices]
        lo = Vector(tuple(min(v[k] for v in points) for k in range(3)))
        hi = Vector(tuple(max(v[k] for v in points) for k in range(3)))
        corners = {tuple(v) for v in points}
        expected = {(x,y,z) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)}
        if len(expected) != 8 or corners != expected:
            raise ValueError(f'{obj.name}: collision mesh must remain a rectangular box.')
        m = obj.matrix_world
        basis = [m.to_3x3().col[i].copy() for i in range(3)]
        lengths = [v.length for v in basis]
        if min(lengths) <= 1e-8:
            raise ValueError(f'{obj.name}: collision box has zero size.')
        unit = [v / n for v,n in zip(basis,lengths)]
        if (abs(unit[2].z) < 1-1e-5 or abs(unit[0].z) > 1e-5 or abs(unit[1].z) > 1e-5
                or any(abs(unit[a].dot(unit[b])) > 1e-5 for a,b in ((0,1),(0,2),(1,2)))):
            raise ValueError(f'{obj.name}: boxes must be upright without shear; rotate around Z only.')
        center = blender_to_source(m @ ((lo+hi)*.5), 'Y_UP')
        half = (hi-lo)*.5
        extents = (half.x*lengths[0], half.z*lengths[2], half.y*lengths[1])
        yaw = math.atan2(-unit[0].y, unit[0].x)
        values = tuple(v*scale for v in (*center,*extents)) + (yaw,)
        if not all(math.isfinite(v) and abs(v) < 1e30 for v in values):
            raise ValueError(f'{obj.name}: invalid collision transform.')
        records.append(struct.pack('<7f', *values))
    return struct.pack('<4sI', b'PCB1', len(records)) + b''.join(records)


def write_sidecar(path, data, backup=True):
    from . import write_atomic
    write_atomic(Path(str(path)+'.colliders'), data, backup=backup, validate_mesh=False)


class SPRITE3D_OT_add_collider(bpy.types.Operator):
    bl_idname = 'sprite3d.add_collider'
    bl_label = 'Add Collision Box'
    bl_description = 'Add one editable box around the selected asset (maximum four per export)'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' and not is_collider(o) for o in context.selected_objects)

    def execute(self, context):
        try:
            visible, helpers = split_objects(context.selected_objects)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        meshes = [o for o in visible if o.type == 'MESH']
        if not meshes:
            self.report({'ERROR'}, 'Select the asset mesh first')
            return {'CANCELLED'}
        if len(helpers) >= MAX_BOXES:
            self.report({'ERROR'}, 'Maximum four collision boxes per asset')
            return {'CANCELLED'}
        points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        lo = Vector(tuple(min(v[k] for v in points) for k in range(3)))
        hi = Vector(tuple(max(v[k] for v in points) for k in range(3)))
        parent = context.active_object if context.active_object in meshes else meshes[0]
        bpy.ops.mesh.primitive_cube_add(size=1, location=(lo+hi)*.5)
        box = context.object
        box.name = 'COLLIDER_' + parent.name
        box.dimensions = tuple(max(v, .01) for v in hi-lo)
        context.view_layer.update()
        world = box.matrix_world.copy()
        box.parent = parent
        box.matrix_parent_inverse = parent.matrix_world.inverted()
        box.matrix_world = world
        box.display_type = 'WIRE'
        box.hide_render = True
        for obj in meshes:
            obj.select_set(True)
        context.view_layer.objects.active = parent
        self.report({'INFO'}, 'Collision box added; move, resize, or rotate around Z')
        return {'FINISHED'}


def collider_scope(context, obj, *, enforce_limit=True):
    """Selected export group plus the active object's existing parent hierarchy."""
    objects = set(context.selected_objects)
    root = obj
    while root.parent is not None:
        root = root.parent
    objects.add(root)
    return split_objects(objects, enforce_limit=enforce_limit)


class SPRITE3D_OT_convert_collider(bpy.types.Operator):
    bl_idname = 'sprite3d.convert_collider'
    bl_label = 'Convert to Bounding Box'
    bl_description = 'Replace the active mesh with an upright collision box fitted to its evaluated bounds (undo supported)'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return context.mode == 'OBJECT' and obj is not None and obj.type == 'MESH' and obj.is_editable

    def execute(self, context):
        obj = context.active_object
        try:
            _, helpers = collider_scope(context, obj)
            if len(helpers) + (0 if obj in helpers else 1) > MAX_BOXES:
                raise ValueError('Maximum four collision boxes per asset')
            if obj.constraints or obj.animation_data:
                raise ValueError('Use a static helper mesh without constraints or animation')
            context.view_layer.update()
            evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
            if not evaluated.data.vertices:
                raise ValueError('The selected mesh has no geometry')
            points = [evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box]
            lo = Vector(tuple(min(v[k] for v in points) for k in range(3)))
            hi = Vector(tuple(max(v[k] for v in points) for k in range(3)))
            if not all(math.isfinite(v) for v in (*lo, *hi)) or min(hi-lo) <= 1e-8:
                raise ValueError('The selected mesh must have finite, nonzero width, depth and height')
            parent_inverse = obj.parent.matrix_world.inverted() if obj.parent else None
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        from mathutils import Matrix
        center = (lo+hi)*.5
        half = (hi-lo)*.5
        vertices = [(x*half.x,y*half.y,z*half.z) for x,y,z in
                    ((-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                     (1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1))]
        faces = [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)]
        mesh = bpy.data.meshes.new('Collision box')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        children = [(child, child.matrix_world.copy()) for child in obj.children]
        obj.data = mesh  # Other objects sharing the old mesh are unaffected.
        obj.modifiers.clear()
        if parent_inverse is not None:
            obj.matrix_parent_inverse = parent_inverse
        obj.matrix_world = Matrix.Translation(center)
        context.view_layer.update()
        for child, world in children:
            child.matrix_world = world
        if not is_collider(obj):
            obj.name = 'COLLIDER_' + obj.name
        for key in list(obj.keys()):
            if key.startswith('sprite3d_'):
                del obj[key]
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.hide_render = True
        obj.hide_set(False)
        self.report({'INFO'}, 'Converted to bounding box; G to move, S to resize, R Z to rotate')
        return {'FINISHED'}


class SPRITE3D_OT_assign_collider(bpy.types.Operator):
    bl_idname = 'sprite3d.assign_collider'
    bl_label = 'Assign to Asset'
    bl_description = 'Select boxes, then select the asset last; parent the boxes to the active mesh without moving them'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (context.mode == 'OBJECT' and obj is not None and obj.type == 'MESH'
                and not is_collider(obj) and any(is_collider(o) for o in context.selected_objects))

    def execute(self, context):
        asset = context.active_object
        boxes = [o for o in context.selected_objects if is_collider(o)]
        try:
            _, existing = collider_scope(context, asset)
            if len(set(existing) | set(boxes)) > MAX_BOXES:
                raise ValueError('Maximum four collision boxes per asset')
            ancestors = set()
            root = asset
            while root is not None:
                ancestors.add(root)
                root = root.parent
            if any(o in ancestors or not o.is_editable for o in boxes):
                raise ValueError('Cannot parent a linked box or an ancestor of the asset')
            context.view_layer.update()
            inverse = asset.matrix_world.inverted()
            worlds = [(o, o.matrix_world.copy()) for o in boxes]
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        for box, world in worlds:
            box.parent = asset
            box.parent_type = 'OBJECT'
            box.matrix_parent_inverse = inverse
            box.matrix_world = world
        self.report({'INFO'}, f'Assigned {len(boxes)} box(es) to {asset.name}')
        return {'FINISHED'}


class SPRITE3D_OT_select_colliders(bpy.types.Operator):
    bl_idname = 'sprite3d.select_colliders'
    bl_label = 'Select Boxes'
    bl_description = 'Reveal and select all boxes belonging to the selected asset, including hidden boxes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object is not None

    def execute(self, context):
        _, helpers = collider_scope(context, context.active_object, enforce_limit=False)
        helpers = [o for o in helpers if o.name in context.view_layer.objects]
        if not helpers:
            self.report({'WARNING'}, 'No collision boxes found for this selection')
            return {'CANCELLED'}
        for obj in context.selected_objects:
            obj.select_set(False)
        for box in helpers:
            box.hide_viewport = False
            box.hide_set(False)
            box.hide_select = False
            box.select_set(True)
            box.show_in_front = True
        context.view_layer.objects.active = helpers[0]
        return {'FINISHED'}


class SPRITE3D_OT_show_colliders(bpy.types.Operator):
    bl_idname = 'sprite3d.show_colliders'
    bl_label = 'Show / Hide Boxes'
    bl_description = 'Change viewport visibility of this asset’s boxes; export is unaffected'
    bl_options = {'REGISTER', 'UNDO'}
    hide: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object is not None

    def execute(self, context):
        _, helpers = collider_scope(context, context.active_object, enforce_limit=False)
        for box in helpers:
            if box.name in context.view_layer.objects:
                if not self.hide:
                    box.hide_viewport = False
                box.hide_set(self.hide)
        self.report({'INFO'}, f'{"Hidden" if self.hide else "Shown"} {len(helpers)} box(es) in viewport')
        return {'FINISHED'}


class SPRITE3D_OT_validate_colliders(bpy.types.Operator):
    bl_idname = 'sprite3d.validate_colliders'
    bl_label = 'Validate Boxes'
    bl_description = 'Check the selected asset’s box count, shape and transforms for Y Up export'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        try:
            visible, helpers = collider_scope(context, context.active_object)
            data = encode_boxes(context, visible, helpers, axes='Y_UP')
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if not helpers:
            self.report({'WARNING'}, 'No collision boxes found; asset will not block movement')
        else:
            self.report({'INFO'}, f'Valid: {len(helpers)} / {MAX_BOXES} boxes, {len(data)} bytes')
        return {'FINISHED'}


class SPRITE3D_OT_remove_collider_tag(bpy.types.Operator):
    bl_idname = 'sprite3d.remove_collider_tag'
    bl_label = 'Remove Collision Tag'
    bl_description = 'Make selected helpers normal visible meshes; this does not restore geometry replaced by conversion'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(is_collider(o) and o.is_editable for o in context.selected_objects)

    def execute(self, context):
        for box in context.selected_objects:
            if not is_collider(box) or not box.is_editable:
                continue
            name = box.name
            while name.startswith('COLLIDER_'):
                name = name[len('COLLIDER_'):]
            box.name = name or 'Box'
            box.display_type = 'TEXTURED'
            box.hide_render = False
            box.show_in_front = False
            box.hide_viewport = False
            box.hide_set(False)
        self.report({'INFO'}, 'Collision tags removed; geometry remains a box')
        return {'FINISHED'}


class SPRITE3D_OT_fit_collider(bpy.types.Operator):
    bl_idname = 'sprite3d.fit_collider'
    bl_label = 'Fit to Selected Geometry'
    bl_description = 'In Edit Mode, create a box around selected vertices; flat selections get 0.01 units minimum thickness'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None and not is_collider(context.active_object)

    def execute(self, context):
        import bmesh
        from mathutils import Matrix
        asset = context.active_object
        try:
            _, helpers = collider_scope(context, asset)
            if len(helpers) >= MAX_BOXES:
                raise ValueError('Maximum four collision boxes per asset')
            points = [obj.matrix_world @ v.co for obj in context.objects_in_mode
                      if obj.type == 'MESH' and not is_collider(obj)
                      for v in bmesh.from_edit_mesh(obj.data).verts if v.select and not v.hide]
            if not points:
                raise ValueError('Select vertices, edges or faces in Edit Mode first')
            if not all(math.isfinite(c) for v in points for c in v):
                raise ValueError('Selected geometry contains invalid coordinates')
            lo = Vector(tuple(min(v[k] for v in points) for k in range(3)))
            hi = Vector(tuple(max(v[k] for v in points) for k in range(3)))
            inverse = asset.matrix_world.inverted()
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        center = (lo+hi)*.5
        half = Vector(tuple(max(d, .01)*.5 for d in hi-lo))
        vertices = [(x*half.x,y*half.y,z*half.z) for x,y,z in
                    ((-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                     (1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1))]
        mesh = bpy.data.meshes.new('Fitted collision box')
        mesh.from_pydata(vertices, [], [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])
        mesh.update()
        box = bpy.data.objects.new('COLLIDER_' + asset.name, mesh)
        context.collection.objects.link(box)
        box.parent = asset
        box.matrix_parent_inverse = inverse
        box.matrix_world = Matrix.Translation(center)
        box.display_type = 'WIRE'
        box.show_in_front = True
        box.hide_render = True
        self.report({'INFO'}, 'Box fitted to selection; leave Edit Mode and use Select Boxes to edit it')
        return {'FINISHED'}


class SPRITE3D_PT_colliders(bpy.types.Panel):
    bl_label = 'Bounding Boxes'
    bl_idname = 'SPRITE3D_PT_colliders'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sprite3D'

    def draw(self, context):
        layout = self.layout
        layout.operator('sprite3d.convert_collider', icon='MESH_CUBE')
        layout.operator('sprite3d.add_collider', text='Add Box Around Asset', icon='CUBE')
        layout.operator('sprite3d.fit_collider')
        layout.label(text='Fit uses vertices selected in Edit Mode')
        layout.separator()
        layout.operator('sprite3d.assign_collider')
        layout.label(text='Select boxes, then the asset last')
        layout.operator('sprite3d.select_colliders')
        row = layout.row(align=True)
        row.operator('sprite3d.show_colliders', text='Show Boxes').hide = False
        row.operator('sprite3d.show_colliders', text='Hide Boxes').hide = True
        layout.operator('sprite3d.validate_colliders', icon='CHECKMARK')
        layout.operator('sprite3d.remove_collider_tag')
        layout.separator()
        layout.label(text='1 recommended; 4 maximum per asset')
        layout.label(text='Sidecars require custom game collision logic', icon='INFO')
        obj = context.active_object
        if obj is not None:
            _, helpers = collider_scope(context, obj, enforce_limit=False)
            layout.label(text=f'Boxes in selection / asset: {len(helpers)} / {MAX_BOXES}',
                         icon='ERROR' if len(helpers) > MAX_BOXES else 'INFO')
            if is_collider(obj):
                layout.prop(obj, 'dimensions', text='Size')
                layout.label(text='Move: G   Resize: S   Rotate: R Z')
        layout.label(text='Conversion replaces the active mesh')


COLLIDER_CLASSES = (SPRITE3D_OT_add_collider, SPRITE3D_OT_convert_collider,
                   SPRITE3D_OT_assign_collider, SPRITE3D_OT_select_colliders,
                   SPRITE3D_OT_show_colliders, SPRITE3D_OT_validate_colliders,
                   SPRITE3D_OT_remove_collider_tag, SPRITE3D_OT_fit_collider,
                   SPRITE3D_PT_colliders)
