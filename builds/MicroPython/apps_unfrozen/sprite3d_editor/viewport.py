"""Native preview meshes, camera layouts, grid, and transform indicators."""

from math import cos, sin, sqrt, floor, pi
from struct import pack, pack_into, unpack_from
from gc import collect, mem_free
from array import array
from picoware.system.vector import Vector
from .meshes import MeshBuffer, prepare_mesh, apply_updates, discard_updates


def orientation_label(draw,x,y,label,color):
    """Keep axis letters readable without covering the scene with a panel."""
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
        draw._text(x+dx,y+dy,label,0x0000)
    draw._text(x,y,label,color)


def view_basis(angle, pitch):
    """Return right, up, and forward axes for a yaw and elevation."""
    ca, sa, cp, sp = cos(angle), sin(angle), cos(pitch), sin(pitch)
    axes = ((-sa, 0, ca), (ca * sp, cp, sa * sp),
            (ca * cp, -sp, sa * cp))
    return tuple(tuple(0.0 if abs(value) < 1e-7 else value for value in axis)
                 for axis in axes)


def clip_polygon(points, planes):
    """Clip in camera space before projection into a split-view pane."""
    for a, b, c, d in planes:
        result = []
        if not points:
            break
        previous = points[-1]
        pv = a*previous[0]+b*previous[1]+c*previous[2]+d
        for point in points:
            value = a*point[0]+b*point[1]+c*point[2]+d
            if (value >= 0) != (pv >= 0):
                t = pv/(pv-value)
                result.append(tuple(previous[i]+t*(point[i]-previous[i]) for i in range(3)))
            if value >= 0:
                result.append(point)
            previous, pv = point, value
        points = result
    return points


def face_direction(points, distance=0, ortho=False):
    """Positive means front-facing in the editor's left-handed view space."""
    a,b,c = points
    ux,uy,uz = b[0]-a[0],b[1]-a[1],b[2]-a[2]
    vx,vy,vz = c[0]-a[0],c[1]-a[1],c[2]-a[2]
    nx,ny,nz = uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
    return nz if ortho else nx*a[0]+ny*a[1]+nz*(a[2]+distance)


def preview_mesh(records, center, basis, panel_transform=None, ortho_distance=None, wireframe=None, perspective_scale=1.0, culling=True, camera_distance=None, buffer=None, updates=None):
    """Prepare sorted, clipped records, then update matching native storage."""
    if buffer is None:
        buffer = MeshBuffer()
    # Pure wire display uses the deduplicated Python overlay.
    output = b'' if wireframe == -2 else _preview_records_python(
        records, center, basis, panel_transform, ortho_distance, wireframe,
        perspective_scale, culling, camera_distance)
    # View records are generated here from validated document geometry.
    return prepare_mesh(buffer, output, updates, validate=False)



def initial_preview_mesh(records,center,basis,wireframe,perspective_scale,buffer,
                         culling=True,camera_distance=None):
    """Stage a native initial view without retaining a packed preview copy."""
    from picoware.engine.sprite3d import Sprite3D
    from .topology import consume
    args=(records,center,basis,None,None,wireframe,perspective_scale,culling,camera_distance)
    count=0 if wireframe==-2 else consume(_preview_records_pass(*args,count_only=True))
    collect()
    mesh=Sprite3D()
    try:
        reserve=getattr(mesh,'reserve_triangles',None)
        if reserve is not None:reserve(count)
        if count:consume(_preview_records_pass(*args,sink=mesh))
        if mesh.triangle_count!=count:raise MemoryError('Incomplete initial preview')
        mesh.set_active(True)
    except Exception:
        mesh.clear_triangles();raise
    # Normal caching resumes after the previous document has been released.
    buffer.mesh=mesh;buffer.records=b''
    return mesh


def _preview_records_python(*args,**kwargs):
    from .topology import consume
    return consume(preview_records_steps(*args,**kwargs))


def preview_checkpoint(remaining):
    # Checkpoint every four eight-triangle batches on constrained heaps.
    # Avoid heap-stat scans inside the per-triangle loop: they are costly on
    # MicroPython and do not prevent fragmentation once temporaries accumulate.
    if remaining is None:return None
    if remaining<=1:
        collect()
        return 4
    return remaining-1


def preview_collect():
    if mem_free()<262144:collect()


def depth_order_steps(records,forward):
    """Native depth sorting with bounded scratch churn and no second index buffer."""
    count=len(records)//40
    order=[None]*count
    checkpoint=4 if mem_free()<262144 else None
    for i in range(count):
        values=unpack_from('<9f',records,i*40)
        depth=((values[0]+values[3]+values[6])*forward[0]+
               (values[1]+values[4]+values[7])*forward[1]+
               (values[2]+values[5]+values[8])*forward[2])
        order[i]=(depth,-i)
        if i%8==0:
            checkpoint=preview_checkpoint(checkpoint)
            yield None
    order.sort(reverse=True)
    # Convert in place: no growing array allocated while the sorted tuples
    # and their depth floats still occupy fragmented heap space.
    for i in range(count):
        order[i]=-order[i][1]
        if i%32==0:
            checkpoint=preview_checkpoint(checkpoint)
            yield None
    return order


def preview_records_steps(records, center, basis, panel_transform=None, ortho_distance=None, wireframe=None, perspective_scale=1.0, culling=True, camera_distance=None):
    """Reserve exact clipped output when a pane competes with other live views."""
    args=(records,center,basis,panel_transform,ortho_distance,wireframe,perspective_scale,culling,camera_distance)
    preview_collect()
    exact=panel_transform is not None and mem_free()<262144
    if not exact:
        try:output=bytearray(len(records))
        except MemoryError:exact=True
    if exact:
        count=yield from _preview_records_pass(*args,count_only=True)
        collect()
        output=bytearray(count*40)
    return (yield from _preview_records_pass(*args,output=output))


def _preview_records_pass(records, center, basis, panel_transform=None, ortho_distance=None, wireframe=None, perspective_scale=1.0, culling=True, camera_distance=None, output=None, count_only=False, sink=None):
    """Build clipped view geometry while leaving live meshes unchanged."""
    from picoware.engine.sprite3d import Sprite3D
    preview_collect()
    right, up, forward = basis
    rx,ry,rz = right
    ux,uy,uz = up
    fx,fy,fz = forward
    cx,cy,cz = center
    count = 0
    offsets = range(len(records)//40) if count_only else (yield from depth_order_steps(records,forward))
    preview_collect()
    checkpoint=4 if mem_free()<262144 else None
    for step,triangle in enumerate(offsets):
        if step%8==0:
            checkpoint=preview_checkpoint(checkpoint)
            yield None
        offset = triangle*40
        values = unpack_from("<9fHB", records, offset)
        # Most fitted faces need no clipping. Keep their coordinates in locals
        # rather than constructing polygons, planes and per-corner lists.
        x,y,z=values[0]-cx,values[1]-cy,values[2]-cz
        ax,ay,az=x*rx+y*ry+z*rz,x*ux+y*uy+z*uz,x*fx+y*fy+z*fz
        x,y,z=values[3]-cx,values[4]-cy,values[5]-cz
        bx,by,bz=x*rx+y*ry+z*rz,x*ux+y*uy+z*uz,x*fx+y*fy+z*fz
        x,y,z=values[6]-cx,values[7]-cy,values[8]-cz
        ex,ey,ez=x*rx+y*ry+z*rz,x*ux+y*uy+z*uz,x*fx+y*fy+z*fz
        distance=panel_transform[3] if panel_transform is not None else camera_distance
        if distance is not None or ortho_distance is not None:
            abx,aby,abz=bx-ax,by-ay,bz-az
            acx,acy,acz=ex-ax,ey-ay,ez-az
            nx,ny,nz=aby*acz-abz*acy,abz*acx-abx*acz,abx*acy-aby*acx
            facing=nz if ortho_distance is not None else nx*ax+ny*ay+nz*(az+(distance or 0))
            if facing==0 or (culling and facing<0):continue
            if facing<0:ax,ay,az,ex,ey,ez=ex,ey,ez,ax,ay,az
        inside=True
        if panel_transform is not None:
            scale,ox,oy,distance,aspect,edge=panel_transform
            if ortho_distance is not None:
                horizontal,vertical=aspect*distance,edge*distance
                inside=(min(ax,bx,ex)>=-horizontal and max(ax,bx,ex)<=horizontal and
                        min(ay,by,ey)>=-vertical and max(ay,by,ey)<=vertical)
            else:
                near=.11/perspective_scale
                inside=(min(az,bz,ez)+distance>=near and
                    abs(ax)<=aspect*(az+distance) and abs(bx)<=aspect*(bz+distance) and abs(ex)<=aspect*(ez+distance) and
                    abs(ay)<=edge*(az+distance) and abs(by)<=edge*(bz+distance) and abs(ey)<=edge*(ez+distance))
        if inside:
            if count_only:
                count+=1
                if count>Sprite3D.MAX_TRIANGLES_PER_SPRITE:raise MemoryError('Clipped preview exceeds triangle capacity')
                continue
            if ortho_distance is not None:
                render_distance=max(.22,ortho_distance)
                az=.5*az/(1+abs(az)/render_distance)
                bz=.5*bz/(1+abs(bz)/render_distance)
                ez=.5*ez/(1+abs(ez)/render_distance)
                factor=(render_distance+az)/ortho_distance;ax,ay=ax*factor,ay*factor
                factor=(render_distance+bz)/ortho_distance;bx,by=bx*factor,by*factor
                factor=(render_distance+ez)/ortho_distance;ex,ey=ex*factor,ey*factor
            if panel_transform is not None:
                rendered_distance=distance if ortho_distance is None else max(.22,distance)
                ax,ay=ax*scale+ox*(rendered_distance+az),ay*scale+oy*(rendered_distance+az)
                bx,by=bx*scale+ox*(rendered_distance+bz),by*scale+oy*(rendered_distance+bz)
                ex,ey=ex*scale+ox*(rendered_distance+ez),ey*scale+oy*(rendered_distance+ez)
            if ortho_distance is None:
                ax,ay,az=ax*perspective_scale,ay*perspective_scale,az*perspective_scale
                bx,by,bz=bx*perspective_scale,by*perspective_scale,bz*perspective_scale
                ex,ey,ez=ex*perspective_scale,ey*perspective_scale,ez*perspective_scale
            count+=1
            if count>Sprite3D.MAX_TRIANGLES_PER_SPRITE:raise MemoryError('Clipped preview exceeds triangle capacity')
            if sink is not None:
                sink.add_triangle(az,ay+.5,ax,bz,by+.5,bx,ez,ey+.5,ex,values[9],
                                  values[10] if wireframe is None else int(wireframe==1))
                continue
            if count*40>len(output):
                preview_collect();output.extend(bytearray(min(max(8,len(output)//80),Sprite3D.MAX_TRIANGLES_PER_SPRITE-count+1)*40))
                checkpoint=4 if mem_free()<262144 else None
            pack_into('<9fHBB',output,(count-1)*40,az,ay+.5,ax,bz,by+.5,bx,ez,ey+.5,ex,values[9],
                values[10] if wireframe is None else int(wireframe==1),0)
            continue
        polygon = []
        for vertex in range(0, 9, 3):
            # Explicit dot products avoid nested generators per corner.
            x,y,z = values[vertex]-cx,values[vertex+1]-cy,values[vertex+2]-cz
            polygon.append((x*rx+y*ry+z*rz, x*ux+y*uy+z*uz, x*fx+y*fy+z*fz))
        # Cull before clipping and native allocation. For two-sided display,
        # reverse only the preview face so the native culler accepts it.
        distance = panel_transform[3] if panel_transform is not None else camera_distance
        if distance is not None or ortho_distance is not None:
            facing = face_direction(polygon, distance or 0, ortho_distance is not None)
            if facing == 0 or (culling and facing < 0):
                continue
            if facing < 0:
                polygon.reverse()
        if panel_transform is not None:
            scale, ox, oy, distance, aspect, edge = panel_transform
            if ortho_distance is not None:
                planes = ((1,0,0,aspect*distance), (-1,0,0,aspect*distance),
                          (0,1,0,edge*distance), (0,-1,0,edge*distance))
            else:
                planes = ((0,0,1,distance-.11/perspective_scale), (1,0,aspect,aspect*distance),
                          (-1,0,aspect,aspect*distance), (0,1,edge,edge*distance),
                          (0,-1,edge,edge*distance))
            polygon = clip_polygon(polygon, planes)
        if count_only:
            count+=max(0,len(polygon)-2)
            if count>Sprite3D.MAX_TRIANGLES_PER_SPRITE:raise MemoryError('Clipped preview exceeds triangle capacity')
            continue
        for index in range(1, len(polygon)-1):
            points = []
            for side, vertical, depth in (polygon[0], polygon[index], polygon[index+1]):
                if ortho_distance is not None:
                    # Retain depth ordering, but cancel the native perspective divide.
                    render_distance = max(.22, ortho_distance)
                    depth = .5*depth/(1+abs(depth)/render_distance)
                    factor = (render_distance+depth)/ortho_distance
                    side, vertical = side*factor, vertical*factor
                if panel_transform is not None:
                    camera_distance = distance if ortho_distance is None else max(.22, distance)
                    side = side*scale + ox*(camera_distance+depth)
                    vertical = vertical*scale + oy*(camera_distance+depth)
                if ortho_distance is None:
                    depth *= perspective_scale
                    vertical *= perspective_scale
                    side *= perspective_scale
                points.extend((depth, vertical+.5, side))
            count += 1
            if count > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
                raise MemoryError("Clipped preview exceeds triangle capacity")
            if sink is not None:
                sink.add_triangle(*points,values[9],values[10] if wireframe is None else int(wireframe==1))
                continue
            if count*40>len(output):
                preview_collect();output.extend(bytearray(min(max(8,len(output)//80),Sprite3D.MAX_TRIANGLES_PER_SPRITE-count+1)*40))
                checkpoint=4 if mem_free()<262144 else None
            pack_into('<9fHBB',output,(count-1)*40,*points,values[9],
                      values[10] if wireframe is None else int(wireframe == 1),0)
    if count_only or sink is not None:return count
    output[count*40:]=b''
    preview_collect()
    return output


class PreviewInput:
    """Keep native Game updates from polling or clearing editor input."""

    button = -1

    def _key_to_button(self, _key):
        """The simulator asks game inputs to map held keys; preview ignores them."""
        return -1

    def reset(self):
        pass


class ViewportMixin:
    """Render the editor document using single or four-pane views."""

    def shading_wireframe(self):
        if self.selection_mode=="Quads" and self.shading in ("Asset","Solid + Wireframe"):return 0
        return {"Asset":None,"Solid":0,"Wireframe":-2,"Solid + Wireframe":1}[self.shading]

    def set_shading(self, mode=None):
        modes = ("Asset","Solid","Wireframe","Solid + Wireframe")
        mode = modes[(modes.index(self.shading)+1)%len(modes)] if mode is None else mode
        previous = self.shading
        self.shading = mode
        try:
            if self.mesh is not None:
                self.refresh_previews()
                from .rendercache import clear
                clear(self)
            self.status = "Shading: "+mode
        except MemoryError as exc:
            self.shading = previous
            self.status = "Shading failed: "+(str(exc) or "Not enough memory")

    def toggle_culling(self):
        previous = self.backface_culling
        self.backface_culling = not previous
        try:
            if self.mesh is not None:
                self.refresh_previews()
            self.status = "Backface culling: " + ("on" if self.backface_culling else "off")
        except MemoryError as exc:
            self.backface_culling = previous
            self.status = "Culling failed: " + (str(exc) or "Not enough memory")

    def refresh_previews(self):
        from .camera import cancel
        cancel(self)
        if self.four_view:
            self.set_four(force=True, records=self.records)
            self._preview_angles = None
        else:
            self._preview_angles = None
            # A real empty mesh also detaches a previous solid native preview.
            rendered = preview_mesh(self.records,self.center,self.basis,
                ortho_distance=self.distance if self.is_ortho() else None,
                wireframe=self.shading_wireframe(),perspective_scale=self.perspective_scale(),
                culling=self.backface_culling,camera_distance=self.distance,
                buffer=self._preview_buffer)
            old = self.render_mesh
            self.entity.sprite_3d = rendered
            self.render_mesh = rendered
            if old is not rendered:
                old.clear_triangles()
            self._preview_angles = (self.angle,self.pitch,self.distance,self.shading,
                                    self.perspective_scale(),self.backface_culling)

        self._quad_display_mode = self.selection_mode=="Quads"


    def reset_camera(self):
        """Return to the initial elevated orbit and fit the model."""
        from .camera import cancel
        cancel(self)
        self._framed_camera = None
        self.clear_four()
        self.active_pane = 1
        self.four_angle = -0.7
        self.four_pitch = .32
        self.pane_zooms = [1.0]*4
        self.maximized = False
        self.angle = -0.7
        self.pitch = 0.32
        self.view_name = "Orbit"
        self.distance = self.fitted_distance()
        self.update_camera()


    def fit_view(self):
        self.frame_selection(all_visible=True)


    def set_view(self, name):
        """Select a world-axis view, with Y as the vertical model axis."""
        angles = {"Front": (-pi / 2, 0), "Side": (pi, 0),
                  "Back": (pi / 2, 0), "Top": (-pi / 2, pi / 2),
                  "Bottom": (-pi / 2, -pi / 2)}
        angle, pitch = angles[name]
        self.orient(angle, pitch, name, self.fit_distance)
        if self.dialog is None:
            self.clear_four()
            self.maximized = False
            self.fit_view()


    def clear_four(self):
        """Release the split-view copies after detaching them from the scene."""
        if self.entity is not None and self.render_mesh is not None:
            self.entity.sprite_3d = self.render_mesh
        for pane in self.panes:
            pane[4].clear_triangles()
        self.panes = []
        self._pane_buffers = []
        self.four_view = False


    def set_four(self, angle=None, zoom=None, force=False, records=None, updates=None, pitch=None):
        """Prepare four fitted native meshes without changing the source asset."""
        if not self.four_view and records is None:
            # Single-pane projection/overlay caches are obsolete in this layout.
            # Drop them before staging four replacement meshes, retaining all
            # document geometry, selection, and the last valid native preview.
            from .rendercache import clear
            clear(self,geometry_only=True)
            self.vertex_visibility_cache.clear();self.edge_label_cache.clear()
            collect()
        angle = (self.four_angle if self.maximized else self.angle) if angle is None else angle
        perspective_pitch = self.four_pitch if pitch is None else pitch
        zoom = self.four_zoom if zoom is None else max(1/128, min(8.0, zoom))
        for i in range(4):
            if self.pane_targets[i] is None:self.pane_targets[i]=tuple(self.center)
            if self.pane_radii[i] is None:self.pane_radii[i]=self.radius
        zooms = list(self.pane_zooms)
        zooms[self.active_pane] = zoom
        targets=tuple(self.pane_targets)
        if not force and self.four_view and angle == self.angle and perspective_pitch == self.four_pitch and zoom == self.four_zoom and self._pane_centers == targets:
            return
        width, height = int(self.vm.draw.size.x), int(self.vm.draw.size.y)
        half_width, half_height = width // 2, (height - 78) // 2
        specs = (("Top", -pi / 2, pi / 2), ("Perspective", angle, perspective_pitch),
                 ("Front", -pi / 2, 0), ("Side", pi, 0))
        panes = []
        if updates is None:
            updates = []
        buffers = self._pane_buffers if len(self._pane_buffers) == 4 else [MeshBuffer() for _ in range(4)]
        previous = self.panes
        try:
            for index, (label, yaw, pitch) in enumerate(specs):
                x = (index % 2) * half_width
                y = 48 + (index // 2) * half_height
                pane_width = half_width if index % 2 == 0 else width - half_width
                pane_height = half_height if index < 2 else height - 30 - y
                box = (x, y, pane_width, pane_height)
                viewport = (x + 2, y + 16, pane_width - 4, pane_height - 18)
                px, py, pw, ph = viewport
                space = max(4, min(pw * 0.42, ph * 0.42))
                distance = self.pane_radii[index] * (1 + ph / space) * zooms[index]
                if label == "Perspective":
                    distance = max(self.pane_radii[index] + .15/self.perspective_scale(), distance)
                basis = view_basis(yaw, pitch)
                transform = (ph / height, (px + pw / 2 - width / 2) / height,
                             (height / 2 - py - ph / 2) / height, distance,
                             (pw/2-1)/ph, (ph/2-1)/ph)
                if (not force and records is None and self.four_view and len(previous)==4
                        and self._pane_centers is not None and self._pane_centers[index]==targets[index]
                        and previous[index][2]==viewport and previous[index][3]==basis
                        and previous[index][5]==distance):
                    panes.append(previous[index])
                    continue
                if (self.shading == "Wireframe" or self._defer_camera) and len(previous)==4:
                    mesh = previous[index][4]
                else:
                    mesh = preview_mesh(self.records if records is None else records, self.pane_targets[index], basis, transform,
                                        distance if label != "Perspective" else None, self.shading_wireframe(),
                                        self.perspective_scale(), self.backface_culling, distance,
                                        buffer=buffers[index], updates=updates)
                panes.append((label, box, viewport, basis, mesh, distance))
            superseded = [pane[4] for pane in previous
                          if not any(p[4] is pane[4] for p in panes)]
            apply_updates(updates)
        except Exception as exc:
            discard_updates(updates)
            if records is not None or not isinstance(exc, MemoryError):
                raise
            from .camera import failure
            failure(self,exc,"View")
            self.dialog = ("View failed", "Not enough memory for 4 View")
            return
        for mesh in superseded:
            mesh.clear_triangles()
        self.panes = panes
        self._pane_centers = targets
        self.four_pitch = perspective_pitch
        self._pane_buffers = buffers
        self.four_view = True
        self.view_name = "4 View"
        self.angle = angle
        self.pane_zooms = zooms
        self.four_angle = angle
        self.maximized = False


    def toggle_active_view(self):
        """Enlarge the selected pane or restore its four-view layout."""
        if self.mesh is None:
            return
        if self.four_view:
            name = ("Top", "Perspective", "Front", "Side")[self.active_pane]
            angles = ((-pi/2, pi/2), (self.four_angle, self.four_pitch), (-pi/2, 0), (pi, 0))
            angle, pitch = angles[self.active_pane]
            self.center=self.pane_targets[self.active_pane] or self.center
            self.radius=self.pane_radii[self.active_pane] or self.radius
            self.fit_distance=self.panes[self.active_pane][5]/self.four_zoom
            self._preview_angles=None
            self.orient(angle, pitch, name, self.fitted_distance(name)*self.four_zoom)
            if self.dialog is None:
                self.clear_four()
                self.maximized = True
                self.maximized_distance = self.distance
        else:
            if not self.maximized:
                self.active_pane = {"Top":0, "Front":2, "Side":3}.get(self.view_name,1)
            angle = self.angle if self.active_pane == 1 else self.four_angle
            zoom = self.four_zoom*self.distance/self.maximized_distance if self.maximized else self.four_zoom
            self.set_four(angle=angle, zoom=zoom, force=True,
                          pitch=self.pitch if self.active_pane==1 else self.four_pitch)


    def pane_control(self, button):
        """Handle pane selection and F5 before preview or transform controls."""
        from picoware.system.buttons import BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, BUTTON_F5, BUTTON_F3, BUTTON_F4
        if self.mesh is None:
            return False
        if button == BUTTON_F3:
            self.frame_selection(toggle=True)
            return True
        if button == BUTTON_F4:
            self.toggle_isolation()
            return True
        if button == BUTTON_F5:
            self.toggle_active_view()
            if self.transform is not None and self.dialog is not None:
                self.status = self.dialog[1]
                self.dialog = None
            return True
        if self.four_view and button in (BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4):
            self.active_pane = (BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4).index(button)
            return True
        return False


    def draw_four(self, draw, indices=None, overlays=()):
        """Render four independent fitted projections with native triangles."""
        try:
            for index, (label, box, viewport, basis, mesh, distance) in enumerate(self.panes):
                if indices is not None and index not in indices:
                    continue
                moving = self._transform_pending or (self._interactive_visibility and self._camera_pending and index==self.active_pane)
                if index not in overlays:
                    draw._fill_rectangle(*box,0x1082)
                    if self.show_grid and not moving:
                        self.grid(draw, viewport, basis, distance)
                self.entity.sprite_3d = mesh
                self.camera.position = Vector(-max(.22, distance) if label != "Perspective" else -distance*self.perspective_scale(), 0)
                self.game.camera = self.camera
                if index not in overlays:
                    if self.shading == "Wireframe":
                        self.draw_selection(draw,viewport,basis,distance,wire_only=True)
                    else:
                        self.engine.run_async(False)
                        if self.selection_mode=='Quads' and self.shading in ('Asset','Solid + Wireframe'):
                            from .wireframe import draw_wire
                            px,py,pw,ph=viewport
                            draw_wire(self,draw,viewport,basis,distance,(px+pw/2,py+ph/2,ph),self.is_ortho(basis),self.near_distance(),asset_only=self.shading=='Asset')
                    from .framecache import store_base
                    store_base(self,box)
                self.draw_selection(draw,viewport,basis,distance)
                if not moving:
                    self.draw_normals(draw,viewport,basis,distance)
                    self.draw_edge_lengths(draw,viewport,basis,distance)
                if self.boolean_workflow is not None and self.boolean_preview is None:
                    from .boolean_workflow import draw_badges
                    px,py,pw,ph = viewport
                    draw_badges(self,draw,viewport,basis,distance,(px+pw/2,py+ph/2,ph))
                x, y, width, height = box
                selected = index == self.active_pane
                color = 0xFFE0 if selected else 0x528A
                if selected:
                    draw._fill_rectangle(x+2, y+2, width-4, 13, 0x051F)
                draw._text(x + 4, y + 4, "%d %s" % (index+1,label), 0xFFE0 if selected else 0xFFFF)
                if not moving:
                    if self.show_orientation:
                        self.orientation(draw, basis, (x + width - 20, y + 34, 10))
                    self.draw_gizmo(draw, viewport, basis, distance)
            # Rectangle edges share a pixel with their neighboring pane. Replay
            # just the borders in painter order after any partial scene redraw.
            for index,(_,box,_,_,_,_) in enumerate(self.panes):
                x,y,width,height = box
                selected = index == self.active_pane
                draw._rectangle(x,y,width,height,0xFFE0 if selected else 0x528A)
                if selected:
                    draw._rectangle(x+1,y+1,width-2,height-2,0xFFE0)
            # Inclusive rectangle endpoints overlap the footer by one row.
            # Keep that row clean even when the cached footer text is unchanged.
            draw._fill_rectangle(0,int(draw.size.y)-30,int(draw.size.x),1,0x2945 if self.transform is not None else 0x0000)
        finally:
            self.entity.sprite_3d = self.render_mesh
            self.camera.position = Vector(-self.render_distance(), 0)
            self.game.camera = self.camera


    def orient(self, angle, pitch, name, distance):
        """Keep the old preview usable if a new orientation cannot allocate."""
        old = self.angle, self.pitch, self.view_name, self.distance
        if name not in ("Front", "Side", "Back", "Top", "Bottom"):
            distance = max(self.radius + .15/self.perspective_scale(), distance)
        self.angle, self.pitch, self.view_name, self.distance = angle, pitch, name, distance
        try:
            self.update_camera()
        except MemoryError:
            self.angle, self.pitch, self.view_name, self.distance = old
            self.dialog = ("View failed", "Not enough memory for the preview")


    def update_camera(self):
        """Transform the preview into the native camera's coordinate system."""
        angles = (self.angle, self.pitch)
        cache = angles + (self.distance,self.shading,self.perspective_scale(),self.backface_culling)
        if cache != self._preview_angles:
            basis = view_basis(*angles)
            if self._defer_camera:
                self.basis=basis
                return
            if self.shading == "Wireframe":
                self.basis = basis
                self._preview_angles = cache
                self.camera.position = Vector(-self.render_distance(), 0)
                self.game.camera = self.camera
                return
            rendered = preview_mesh(self.records, self.center, basis,
                                    ortho_distance=self.distance if self.is_ortho() else None,
                                    wireframe=self.shading_wireframe(),
                                    perspective_scale=self.perspective_scale(),
                                    culling=self.backface_culling, camera_distance=self.distance,
                                    buffer=self._preview_buffer)
            old_preview = self.render_mesh
            self.entity.sprite_3d = rendered
            self.render_mesh = rendered
            self.basis = basis
            self._preview_angles = cache
            if old_preview is not rendered:
                old_preview.clear_triangles()
        self.camera.position = Vector(-self.render_distance(), 0)
        self.camera.direction = Vector(1, 0)
        self.camera.height = 0.5
        self.game.camera = self.camera


    def fitted_distance(self, name=None):
        name = self.view_name if name is None else name
        if name in ("Front", "Side", "Back", "Top", "Bottom"):
            return self.fit_distance
        return max(self.radius + .15/self.perspective_scale(), self.fit_distance)

    def perspective_scale(self):
        """Normalize tiny previews so the native near plane does not hide them."""
        return max(1.0, .15/self.radius)

    def near_distance(self):
        return .11/self.perspective_scale()

    def render_distance(self):
        return max(.22, self.distance) if self.is_ortho() else self.distance*self.perspective_scale()

    def is_ortho(self, basis=None):
        if basis is None:
            return self.view_name in ("Front", "Side", "Back", "Top", "Bottom")
        return max(abs(v) for v in basis[2]) > .999999


    def view_point(self, x, y, z, basis=None, distance=None):
        """Map an original model-space point to camera coordinates."""
        center=self.projection_center(basis)
        x, y, z = x - center[0], y - center[1], z - center[2]
        right, up, forward = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        return (x * right[0] + y * right[1] + z * right[2],
                x * up[0] + y * up[1] + z * up[2],
                x * forward[0] + y * forward[1] + z * forward[2] + distance)


    def grid_line(self, draw, x1, z1, x2, z2, color, viewport=None, basis=None, distance=None):
        """Project and clip a ground line using the engine's camera convention."""
        ax, ay, az = self.view_point(x1, self.ground, z1, basis, distance)
        bx, by, bz = self.view_point(x2, self.ground, z2, basis, distance)
        ortho = self.is_ortho(basis)
        near = self.near_distance()
        if ortho:
            az = bz = self.distance if distance is None else distance
        if not ortho and az < near and bz < near:
            return
        if not ortho and az < near:
            t = (near - az) / (bz - az)
            ax, ay, az = ax + (bx - ax) * t, ay + (by - ay) * t, near
        if not ortho and bz < near:
            t = (near - bz) / (az - bz)
            bx, by, bz = bx + (ax - bx) * t, by + (ay - by) * t, near
        width, height = draw.size.x, draw.size.y
        left, top, right, bottom = 0, 48, width - 1, height - 31
        cx, cy, focal = width / 2, height / 2, height
        if viewport is not None:
            left, top, pw, ph = viewport
            right, bottom = left + pw - 1, top + ph - 1
            cx, cy, focal = left + pw / 2, top + ph / 2, ph
        x1, y1 = cx + ax * focal / az, cy - ay * focal / az
        x2, y2 = cx + bx * focal / bz, cy - by * focal / bz
        sx, sy = x2 - x1, y2 - y1
        low, high = 0.0, 1.0
        for p, q in ((-sx, x1 - left), (sx, right - x1),
                     (-sy, y1 - top), (sy, bottom - y1)):
            if p == 0:
                if q < 0:
                    return
            elif p < 0:
                low = max(low, q / p)
            else:
                high = min(high, q / p)
        if low <= high:
            draw._line(int(x1 + low * sx), int(y1 + low * sy),
                       int(x1 + high * sx), int(y1 + high * sy), color)


    def ortho_grid(self, draw, viewport=None, basis=None, distance=None):
        """Fill an axis-view pane with its world-aligned viewing-plane grid."""
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        width,height = int(draw.size.x),int(draw.size.y)
        left,top,pw,ph = (0,48,width,height-78) if viewport is None else viewport
        right,bottom = left+pw-1,top+ph-1
        cx,cy,focal = (width/2,height/2,height) if viewport is None else (left+pw/2,top+ph/2,ph)
        scale = focal/distance
        # Match the model projection, including the camera's world-space center.
        ox = cx-sum(self.projection_center(basis)[i]*basis[0][i] for i in range(3))*scale
        oy = cy+sum(self.projection_center(basis)[i]*basis[1][i] for i in range(3))*scale
        spacing = self.grid_step*scale
        # Keep the grid readable at each pane's independent zoom. This affects
        # drawing density only; snapping continues to use the document grid step.
        while spacing < 12:
            spacing *= 2
        while spacing > 24:
            spacing /= 2
        horizontal = max(range(3),key=lambda i:abs(basis[0][i]))
        vertical = max(range(3),key=lambda i:abs(basis[1][i]))
        colors = (0xA208,0x2424,0x3297)
        for index in range(int(floor((left-ox)/spacing)),int(floor((right-ox)/spacing))+1):
            x = int(round(ox+index*spacing))
            if left <= x <= right:
                draw._line(x,top,x,bottom,colors[vertical] if index==0 else 0x3186)
        for index in range(int(floor((top-oy)/spacing)),int(floor((bottom-oy)/spacing))+1):
            y = int(round(oy+index*spacing))
            if top <= y <= bottom:
                draw._line(left,y,right,y,colors[horizontal] if index==0 else 0x3186)

    def grid(self, draw, viewport=None, basis=None, distance=None):
        """Use a viewing-plane grid for axis views and a ground grid for orbit."""
        if self.is_ortho(basis):
            self.ortho_grid(draw,viewport,basis,distance)
            return
        step = self.grid_step
        cx = floor(self.projection_center(basis)[0] / step) * step
        cz = floor(self.projection_center(basis)[2] / step) * step
        extent = step * 6
        for index in range(-6, 7):
            x, z = cx + index * step, cz + index * step
            self.grid_line(draw, cx - extent, z, cx + extent, z,
                           0xA208 if abs(z) < step * 0.01 else 0x3186,
                           viewport, basis, distance)
            self.grid_line(draw, x, cz - extent, x, cz + extent,
                           0x3297 if abs(x) < step * 0.01 else 0x3186,
                           viewport, basis, distance)


    def orientation(self, draw, basis=None, placement=None):
        """Draw labeled world axes using the current camera direction."""
        cx, cy, length = (int(draw.size.x) - 37, 87, 22) if placement is None else placement
        right, up, forward = self.basis if basis is None else basis
        draw._fill_circle(cx, cy, 2, 0xFFFF)
        for axis, (label, color) in enumerate((("X", 0xF800), ("Y", 0x07E0), ("Z", 0x3DFF))):
            side, vertical, depth = right[axis], up[axis], forward[axis]
            if abs(side) + abs(vertical) < 0.01:
                draw._circle(cx, cy, 4, color)
                orientation_label(draw,cx - 4,cy + 10,label,color)
                if depth > 0:
                    draw._line(cx - 3, cy - 3, cx + 3, cy + 3, color)
                    draw._line(cx - 3, cy + 3, cx + 3, cy - 3, color)
                continue
            scale = length / (1 + depth * 0.15)
            x, y = cx + int(side * scale), cy - int(vertical * scale)
            draw._line(cx, cy, x, y, color)
            orientation_label(draw,x - 3,y - 10,label,color)


    def draw_gizmo(self, draw, viewport=None, basis=None, distance=None):
        """Show the active transform or custom pivot in world axes."""
        if self.transform is None:
            if self.pivot_edit is None:return
            state=self.pivot_edit
            t={"kind":"Pivot","axis":state["axis"],"position":state["position"]}
        else:
            t=self.transform
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w, h = int(draw.size.x), int(draw.size.y)
        left, top, pw, ph = (0,48,w,h-78) if viewport is None else viewport
        cx, cy, focal = (w/2,h/2,h) if viewport is None else (left+pw/2,top+ph/2,ph)
        bottom = min(top+ph-2,h-31)
        if t["kind"]=="Pivot":
            pivot=list(t["position"])
        else:
            low, high = t["low"],t["high"]
            pivot = [(low[i]+high[i])*.5+t["values"][i] for i in range(3)]
            if t["kind"] == "Move" and t["pivot"] == 1:
                pivot[1] = low[1]+t["values"][1]
            if t["kind"] != "Move":
                pivot = [(t["low"][i]+t["high"][i])*.5 for i in range(3)]
                if t["pivot"] == 1:
                    pivot[1] = t["low"][1]
                elif t["pivot"] == 2:
                    pivot = [0,0,0]
                elif t["pivot"] == 3 and self.custom_pivot is not None:
                    pivot = list(self.custom_pivot)
        length = distance*min(pw,ph)*.22/focal

        def project(point):
            x,y,z = self.view_point(*point, basis=basis, distance=distance)
            if self.is_ortho(basis):
                z = distance
            elif z < self.near_distance():
                return None
            x,y = int(cx+x*focal/z),int(cy-y*focal/z)
            if not (left+2 <= x < left+pw-2 and top+2 <= y < bottom):
                return None
            return x,y

        origin = project(pivot)
        plane = self.is_ortho() if viewport is None else self.is_ortho(basis)
        depth_axis = max(range(3),key=lambda i:abs(basis[2][i])) if plane else -1
        for axis, color in enumerate((0xF800,0x07E0,0x001F)):
            if t["kind"] == "Move" and axis == depth_axis:
                continue
            selected = axis == t["axis"] or (t["kind"] == "Scale" and t["uniform"])
            if selected:
                color = 0xFFE0
            endpoint = list(pivot)
            endpoint[axis] += length
            end = project(endpoint)
            if t["kind"] == "Rotate":
                # Ring geometry is independent of the current rotation values.
                key = (basis,distance,tuple(self.projection_center(basis)),tuple(pivot),left,top,pw,ph,w,h,plane,self.near_distance())
                cache = t['gizmo']
                rings = cache.get(key)
                if rings is None:
                    rings = []
                    for ring_axis in range(3):
                        points = array('h')
                        for step in range(33):
                            angle = step*pi/16
                            point = list(pivot)
                            point[(ring_axis+1)%3] += cos(angle)*length
                            point[(ring_axis+2)%3] += sin(angle)*length
                            current = project(point)
                            points.extend(current if current is not None else (-1,-1))
                        rings.append(points)
                    if len(cache)>=4:
                        cache.clear()
                    cache[key] = rings
                points = rings[axis]
                for j in range(2,len(points),2):
                    if points[j-2]>=0 and points[j]>=0:
                        draw._line(points[j-2],points[j-1],points[j],points[j+1],color)
            elif origin is not None and end is not None:
                draw._line(*origin,*end,color)
                ex,ey = end
                if t["kind"] in ("Scale","Pivot"):
                    draw._fill_rectangle(ex-2,ey-2,5,5,color)
                else:
                    dx,dy = ex-origin[0],ey-origin[1]
                    magnitude = max(1,sqrt(dx*dx+dy*dy))
                    ux,uy = dx/magnitude,dy/magnitude
                    draw._line(ex,ey,int(ex-6*ux+3*uy),int(ey-6*uy-3*ux),color)
                    draw._line(ex,ey,int(ex-6*ux-3*uy),int(ey-6*uy+3*ux),color)
            if end is not None and end[0]+6 < left+pw and end[1]+8 < bottom:
                draw._text(end[0],end[1],"XYZ"[axis],color)
        if origin is not None:
            draw._rectangle(origin[0]-2,origin[1]-2,5,5,0xFFFF)
