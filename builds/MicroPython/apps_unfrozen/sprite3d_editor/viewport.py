"""Native preview meshes, camera layouts, grid, and transform indicators."""

from math import cos, sin, sqrt, floor, pi
from struct import unpack_from
from picoware.system.vector import Vector


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


def preview_mesh(records, center, basis, panel_transform=None, ortho_distance=None, wireframe=None, perspective_scale=1.0, culling=True, camera_distance=None):
    """Use bounded native construction when available; preserve old firmware."""
    from picoware.engine.sprite3d import Sprite3D
    mesh = Sprite3D()
    if wireframe == -2:  # Pure wire display uses the deduplicated Python overlay.
        mesh.set_active(True)
        return mesh
    build = getattr(mesh, 'build_preview', None)
    if build is not None:
        try:
            build(records,center,basis,panel_transform,ortho_distance,wireframe,
                  perspective_scale,culling,camera_distance)
            return mesh
        except Exception:
            mesh.clear_triangles()
            raise
    return _preview_mesh_python(records,center,basis,panel_transform,ortho_distance,
                                wireframe,perspective_scale,culling,camera_distance)


def _preview_mesh_python(records, center, basis, panel_transform=None, ortho_distance=None, wireframe=None, perspective_scale=1.0, culling=True, camera_distance=None):
    """Build clipped view geometry while leaving editable records unchanged."""
    from picoware.engine.sprite3d import Sprite3D
    mesh = Sprite3D()
    right, up, forward = basis
    rx,ry,rz = right
    ux,uy,uz = up
    fx,fy,fz = forward
    cx,cy,cz = center
    count = 0
    try:
        # Culling removes back-facing triangles, not faces hidden by another
        # object. The native painter needs far-to-near order in both modes.
        # MicroPython sort may invoke key repeatedly. Calculate each depth
        # once; discard the temporary decorated list before building geometry.
        order = []
        for offset in range(0,len(records),40):
            values = unpack_from("<9f", records, offset)
            depth = ((values[0]+values[3]+values[6])*forward[0] +
                     (values[1]+values[4]+values[7])*forward[1] +
                     (values[2]+values[5]+values[8])*forward[2])
            order.append((depth,-offset))
        order.sort(reverse=True)
        from array import array
        offsets = array('H',(-item[1]//40 for item in order))
        del order
        for triangle in offsets:
            offset = triangle*40
            values = unpack_from("<9fHB", records, offset)
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
                mesh.add_triangle(*points, values[9], values[10] if wireframe is None else int(wireframe == 1))
        if mesh.triangle_count != count:
            raise MemoryError("Could not build complete preview")
        mesh.set_active(True)
        return mesh
    except Exception:
        mesh.clear_triangles()
        raise


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
        if self.four_view:
            self.set_four(force=True, records=self.records)
            self._preview_angles = None
        else:
            self._preview_angles = None
            # A real empty mesh also detaches a previous solid native preview.
            rendered = preview_mesh(self.records,self.center,self.basis,
                ortho_distance=self.distance if self.is_ortho() else None,
                wireframe=self.shading_wireframe(),perspective_scale=self.perspective_scale(),
                culling=self.backface_culling,camera_distance=self.distance)
            old = self.render_mesh
            self.entity.sprite_3d = rendered
            self.render_mesh = rendered
            old.clear_triangles()
            self._preview_angles = (self.angle,self.pitch,self.distance,self.shading,
                                    self.perspective_scale(),self.backface_culling)


    def reset_camera(self):
        """Return to the initial elevated orbit and fit the model."""
        self.clear_four()
        self.active_pane = 1
        self.four_angle = -0.7
        self.pane_zooms = [1.0]*4
        self.maximized = False
        self.angle = -0.7
        self.pitch = 0.32
        self.view_name = "Orbit"
        self.distance = self.fitted_distance()
        self.update_camera()


    def fit_view(self):
        """Fit edited bounds without moving the ground or changing orientation."""
        old = (self.center, self.radius, self.fit_distance, self.distance, self.four_zoom)
        try:
            low, high = self.bounds
            self.center = [(low[i]+high[i])*.5 for i in range(3)]
            self.radius = max(1e-9, sqrt(sum((high[i]-low[i])**2 for i in range(3)))*.5)
            width, height = self.vm.draw.size.x, self.vm.draw.size.y
            self.fit_distance = self.radius*(1+height/max(10,min(width*.42,height*.5-64)))
            self.distance = self.fitted_distance()
            self.four_zoom = 1.0
            self.replace_records(self.records)
            if self.maximized:
                self.maximized_distance = self.distance
        except MemoryError as exc:
            self.center, self.radius, self.fit_distance, self.distance, self.four_zoom = old
            self.dialog = ("Fit failed", str(exc) or "Not enough memory")
        self.camera.position = Vector(-self.render_distance(), 0)
        self.game.camera = self.camera


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
        self.four_view = False


    def set_four(self, angle=None, zoom=None, force=False, records=None):
        """Prepare four fitted native meshes without changing the source asset."""
        angle = (self.four_angle if self.maximized else self.angle) if angle is None else angle
        zoom = self.four_zoom if zoom is None else max(1/128, min(8.0, zoom))
        zooms = list(self.pane_zooms)
        zooms[self.active_pane] = zoom
        if not force and self.four_view and angle == self.angle and zoom == self.four_zoom:
            return
        width, height = int(self.vm.draw.size.x), int(self.vm.draw.size.y)
        half_width, half_height = width // 2, (height - 78) // 2
        specs = (("Top", -pi / 2, pi / 2), ("Perspective", angle, 0.32),
                 ("Front", -pi / 2, 0), ("Side", pi, 0))
        panes = []
        created = []
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
                distance = self.radius * (1 + ph / space) * zooms[index]
                if label == "Perspective":
                    distance = max(self.radius + .15/self.perspective_scale(), distance)
                basis = view_basis(yaw, pitch)
                transform = (ph / height, (px + pw / 2 - width / 2) / height,
                             (height / 2 - py - ph / 2) / height, distance,
                             (pw/2-1)/ph, (ph/2-1)/ph)
                if (not force and records is None and self.four_view and len(previous)==4
                        and previous[index][2]==viewport and previous[index][3]==basis
                        and previous[index][5]==distance):
                    panes.append(previous[index])
                    continue
                if self.shading == "Wireframe" and len(previous)==4:
                    mesh = previous[index][4]
                else:
                    mesh = preview_mesh(self.records if records is None else records, self.center, basis, transform,
                                        distance if label != "Perspective" else None, self.shading_wireframe(),
                                        self.perspective_scale(), self.backface_culling, distance)
                    created.append(mesh)
                panes.append((label, box, viewport, basis, mesh, distance))
        except MemoryError:
            for mesh in created:
                mesh.clear_triangles()
            if records is not None:
                raise
            self.dialog = ("View failed", "Not enough memory for 4 View")
            return
        for pane in previous:
            if not any(p[4] is pane[4] for p in panes):
                pane[4].clear_triangles()
        self.panes = panes
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
            angles = ((-pi/2, pi/2), (self.four_angle, .32), (-pi/2, 0), (pi, 0))
            angle, pitch = angles[self.active_pane]
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
            self.set_four(angle=angle, zoom=zoom, force=True)


    def pane_control(self, button):
        """Handle pane selection and F5 before preview or transform controls."""
        from picoware.system.buttons import BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, BUTTON_F5
        if self.mesh is None:
            return False
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
                    from .framecache import store_base
                    store_base(self,box)
                self.draw_selection(draw,viewport,basis,distance)
                if not moving:
                    self.draw_normals(draw,viewport,basis,distance)
                    self.draw_edge_lengths(draw,viewport,basis,distance)
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
                                    culling=self.backface_culling, camera_distance=self.distance)
            old_preview = self.render_mesh
            self.entity.sprite_3d = rendered
            self.render_mesh = rendered
            self.basis = basis
            self._preview_angles = cache
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
        x, y, z = x - self.center[0], y - self.center[1], z - self.center[2]
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
        ox = cx-sum(self.center[i]*basis[0][i] for i in range(3))*scale
        oy = cy+sum(self.center[i]*basis[1][i] for i in range(3))*scale
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
        cx = floor(self.center[0] / step) * step
        cz = floor(self.center[2] / step) * step
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
        if placement is None:
            draw._fill_rectangle(cx - 33, 50, 70, 65, 0x1082)
        right, up, forward = self.basis if basis is None else basis
        draw._fill_circle(cx, cy, 2, 0xFFFF)
        for axis, (label, color) in enumerate((("X", 0xF800), ("Y", 0x07E0), ("Z", 0x3DFF))):
            side, vertical, depth = right[axis], up[axis], forward[axis]
            if abs(side) + abs(vertical) < 0.01:
                draw._circle(cx, cy, 4, color)
                draw._text(cx - 4, cy + 10, label, color)
                if depth > 0:
                    draw._line(cx - 3, cy - 3, cx + 3, cy + 3, color)
                    draw._line(cx - 3, cy + 3, cx + 3, cy - 3, color)
                continue
            scale = length / (1 + depth * 0.15)
            x, y = cx + int(side * scale), cy - int(vertical * scale)
            draw._line(cx, cy, x, y, color)
            draw._text(x - 3, y - 10, label, color)


    def draw_gizmo(self, draw, viewport=None, basis=None, distance=None):
        """Show the active whole-model tool in world axes in each viewport."""
        if self.transform is None:
            return
        t = self.transform
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w, h = int(draw.size.x), int(draw.size.y)
        left, top, pw, ph = (0,48,w,h-78) if viewport is None else viewport
        cx, cy, focal = (w/2,h/2,h) if viewport is None else (left+pw/2,top+ph/2,ph)
        bottom = min(top+ph-2,h-31)
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
                key = (basis,distance,tuple(self.center),tuple(pivot),left,top,pw,ph,w,h,plane,self.near_distance())
                cache = t['gizmo']
                rings = cache.get(key)
                if rings is None:
                    from array import array
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
                if t["kind"] == "Scale":
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
