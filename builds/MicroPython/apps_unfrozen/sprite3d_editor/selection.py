"""Small selection masks and clipped, non-destructive component overlays."""

from struct import unpack_from


def vertex(records, index):
    return unpack_from("<3f",records,(index//3)*40+(index%3)*12)


def clipped_line(draw, a, b, box, color):
    left,top,width,height = box
    right,bottom = left+width-1,top+height-1
    x,y = a
    dx,dy = b[0]-x,b[1]-y
    low,high = 0.0,1.0
    for p,q in ((-dx,x-left),(dx,right-x),(-dy,y-top),(dy,bottom-y)):
        if p == 0:
            if q < 0:
                return
        elif p < 0:
            low = max(low,q/p)
        else:
            high = min(high,q/p)
        if low > high:
            return
    draw._line(int(x+low*dx),int(y+low*dy),int(x+high*dx),int(y+high*dy),color)


class SelectionTools:
    def vertex_groups(self):
        """Compact corner-to-representative mapping, rebuilt on geometry edits."""
        if self._vertex_groups is None:
            from array import array
            lookup, representatives, groups = {},array('H'),array('H')
            for i in range(len(self.records)//40*3):
                point = vertex(self.records,i)
                representative = lookup.get(point)
                if representative is None:
                    representative = i
                    lookup[point] = i
                    representatives.append(i)
                groups.append(representative)
            self._vertex_groups = groups,representatives
        return self._vertex_groups

    def visible_vertex_mask(self,projection=None):
        return self.visible_component_mask(projection,False)

    def visible_triangle_mask(self,projection=None):
        return self.visible_component_mask(projection,True)

    def visible_component_mask(self,projection,triangles):
        if self.xray_vertices:
            return None
        if projection is None:
            projection = self.selection_projection()
        box,basis,distance,screen = projection
        key = (triangles,tuple(self.projection_center(basis)),basis,distance,box,screen,self.near_distance())
        cached = self.vertex_visibility_cache.get(box)
        mask = cached[1] if cached is not None and cached[0] == key else None
        if mask is None:
            if self._interactive_visibility:
                from .visibilityjobs import request
                return request(self,box,key,
                    (self.records,tuple(self.projection_center(basis)),basis,distance,box,screen,self.is_ortho(basis)),
                    {'triangles':triangles,'near':self.near_distance()},
                    len(self.records)//40*(1 if triangles else 3))
            from .visibility import visible_vertices
            try:
                mask = visible_vertices(self.records,self.projection_center(basis),basis,distance,box,screen,self.is_ortho(basis),triangles,self.near_distance())
            except MemoryError:
                mask = bytearray(len(self.records)//40*(1 if triangles else 3))
                self.status = "Visibility memory full; enable X-Ray"
            if box not in self.vertex_visibility_cache and len(self.vertex_visibility_cache)>=4:
                del self.vertex_visibility_cache[next(iter(self.vertex_visibility_cache))]
            self.vertex_visibility_cache[box] = (key,mask)
        elif box in self._visibility_pending:
            from .visibilityjobs import cancel
            cancel(self,box)
        return mask

    def active_visibility(self,projection=None):
        if self.selection_mode == 'Quads':
            return self.quads.visible(self.visible_triangle_mask(projection))
        if self.selection_mode == "Edges":
            return self.visible_edge_mask(projection)
        return self.visible_vertex_mask(projection) if self.selection_mode == "Vertices" else self.visible_triangle_mask(projection)

    def ensure_visible_vertex(self):
        if self.selection_mode in ("Vertices","Triangles","Quads","Edges") and self.selection:
            visible = self.active_visibility()
            if self.selection_projection()[0] in self._visibility_pending:
                self._selection_recover = True
            if visible is not None and not visible[self.selection_cursor]:
                self.selection_cursor = next((i for i,v in enumerate(visible) if v),self.selection_cursor)

    def get_islands(self):
        from .islands import detect_islands
        if self.islands is None:
            self.islands = detect_islands(self.records or b"")
        return self.islands

    def active_island(self):
        return next((group for group in self.get_islands() if self.selection_cursor in group),[])

    def browse_island(self, direction):
        groups = self.get_islands()
        if not groups:
            return
        current = next((i for i,g in enumerate(groups) if self.selection_cursor in g),0)
        group = groups[(current+direction)%len(groups)]
        self.selection_cursor = group[0]
        self.selection_fill("None")
        for i in group:
            self.selection[i] = 1
        self.status = ""

    def selection_mode_set(self, mode, refresh=True):
        from .visibilityjobs import cancel
        cancel(self)
        old_mode=self.selection_mode;old_mask=self.selection;old_cursor=self.selection_cursor
        old_camera=self.selection_camera;old_status=self.status;old_recover=self._selection_recover
        if mode == "Islands":
            self.get_islands()
        count = len(self.records or b"")//40
        self._edge_reps = None
        selection = bytearray(count*(3 if mode == "Vertices" else 1)) if mode != "Model" else bytearray()
        if mode == "Edges":
            selection = bytearray(len(self.get_edges()))
        self.selection_mode = mode
        self.selection = selection
        self.selection_cursor = 0
        if mode in ('Quads','Triangles') and old_mode in ('Quads','Triangles') and len(old_mask)==count:
            self.selection=bytearray(old_mask);self.selection_cursor=min(old_cursor,max(0,count-1))
        if mode=='Quads' and count:
            self.quads.expand(self.selection);self.selection_cursor=self.quads.representative(self.selection_cursor)
        self._selection_recover = False
        self.selection_camera = False
        self.status = ""
        if refresh and (mode=='Quads')!=(old_mode=='Quads') and self.mesh is not None:
            try:self.refresh_previews()
            except Exception:
                self.selection_mode,self.selection,self.selection_cursor=old_mode,old_mask,old_cursor
                self.selection_camera,self.status,self._selection_recover=old_camera,old_status,old_recover
                self._preview_angles=None
                raise
            from .rendercache import clear
            clear(self)
        if mode == "Islands":
            self.browse_island(0)
        elif mode in ("Vertices","Triangles","Quads","Edges"):
            self.ensure_visible_vertex()

    def cycle_selection(self):
        if not self.records:
            self.status = "Create geometry first"
            return
        from .modes import MODES as modes
        try:
            self.selection_mode_set(modes[(modes.index(self.selection_mode)+1)%len(modes)])
            self.status = "Selection: " + self.selection_mode
        except (MemoryError,ValueError) as exc:
            self.dialog = ("Selection failed",str(exc) or "Not enough memory")

    def has_selection(self):
        return bool(self.records) and (self.selection_mode == "Model" or any(self.selection))

    def selection_label(self):
        if self.selection_mode=='Quads':
            quads=len(self.quads.pairs)//2;tris=len(self.selection)-quads*2
            selected=sum(bool(self.selection[i]) for i in self.quads.reps)
            return '%d quads / %d tris / Sel %d' % (quads,tris,selected)
        if self.selection_mode == "Model":
            return "%d tris / Model" % (len(self.records)//40)
        if self.selection_mode == "Islands":
            groups = self.get_islands()
            index = next((i+1 for i,g in enumerate(groups) if self.selection_cursor in g),0)
            return "Island %d/%d / %d faces" % (index,len(groups),sum(self.selection))
        return "%s %d/%d Sel %d" % ("Tri" if self.selection_mode == "Triangles" else "Edge" if self.selection_mode == "Edges" else "V",
            self.selection_cursor+1 if self.selection else 0,len(self.selection),sum(self.selection))

    def selection_fill(self, action):
        for i in range(len(self.selection)):
            self.selection[i] = (1-self.selection[i]) if action == "Invert" else int(action == "All")

    def selection_toggle(self):
        if not self.selection:
            return
        index = self.selection_cursor
        if self.selection_mode in ("Vertices","Triangles","Quads","Edges"):
            visible = self.active_visibility()
            if visible is not None and not visible[index]:
                self.status = ("Checking visibility..." if self.selection_projection()[0] in self._visibility_pending
                               else "Hidden component: use arrows or X-Ray")
                return
        value = 1-self.selection[index]
        if self.selection_mode == 'Quads':
            for i in self.quads.group(index):self.selection[i]=value
        elif self.selection_mode == "Islands":
            for i in self.active_island():
                self.selection[i] = value
        elif self.selection_mode == "Vertices" and self.linked_vertices:
            point = vertex(self.records,index)
            for i in range(len(self.selection)):
                if vertex(self.records,i) == point:
                    self.selection[i] = value
        else:
            self.selection[index] = value

    def selection_mask(self):
        if self.selection_mode == "Model":
            return None
        if not any(self.selection):
            raise ValueError("Select geometry with Space first")
        if self.selection_mode == "Edges":
            return self.edge_vertex_mask()
        if self.selection_mode == "Vertices":
            return bytes(self.selection)
        if self.selection_mode in ("Triangles","Quads") and self.linked_vertices:
            # Sprite3D stores separate corners per face. Transform every copy of
            # a selected position so neighboring faces do not split at seams.
            points = set(vertex(self.records,i*3+j)
                         for i,selected in enumerate(self.selection) if selected
                         for j in range(3))
            return bytearray(vertex(self.records,i) in points
                             for i in range(len(self.records)//40*3))
        mask = bytearray(len(self.selection)*3)
        for i,value in enumerate(self.selection):
            if value:
                mask[i*3:i*3+3] = b"\x01\x01\x01"
        return mask

    def selected_bounds(self, mask):
        if mask is None:
            return self.bounds
        low,high = [float("inf")]*3,[-float("inf")]*3
        for i,selected in enumerate(mask):
            if selected:
                point = vertex(self.records,i)
                for axis in range(3):
                    low[axis] = min(low[axis],point[axis])
                    high[axis] = max(high[axis],point[axis])
        return low,high

    def selected_triangles(self):
        count = len(self.records or b"")//40
        if self.selection_mode == "Model":
            return list(range(count))
        if self.selection_mode == "Edges":
            return self.selected_edge_faces()
        if self.selection_mode in ("Triangles","Quads","Islands"):
            return [i for i in range(count) if self.selection[i]]
        return [i for i in range(count) if any(self.selection[i*3:i*3+3])]

    def selection_projection(self):
        """Use the same projection and drawable bounds as the active pane."""
        draw = self.vm.draw
        w,h = int(draw.size.x),int(draw.size.y)
        if self.four_view:
            _,_,box,basis,_,distance = self.panes[self.active_pane]
            x,y,pw,ph = box
            return box,basis,distance,(x+pw/2,y+ph/2,ph)
        return (0,48,w,h-78),self.basis,self.distance,(w/2,h/2,h)

    def projected_vertex(self, index, projection):
        box,basis,distance,screen = projection
        visible = self.visible_vertex_mask(projection)
        if visible is not None and not visible[index]:
            return None
        x,y,z = self.view_point(*vertex(self.records,index),basis=basis,distance=distance)
        depth = distance if self.is_ortho(basis) else z
        if not self.is_ortho(basis) and depth < self.near_distance():
            return None
        cx,cy,focal = screen
        px,py = cx+x*focal/depth,cy-y*focal/depth
        left,top,width,height = box
        if not (left+4 <= px < left+width-4 and top+4 <= py < top+height-4):
            return None
        return px,py,z

    def projected_triangle(self,index,projection):
        visible = self.active_visibility(projection) if self.selection_mode=='Quads' else self.visible_triangle_mask(projection)
        if visible is not None and not visible[index]:
            return None
        box,basis,distance,screen = projection
        points = [vertex(self.records,index*3+j) for j in range(3)]
        if self.selection_mode=='Quads' and self.quads.mates[index]>=0:
            from .quads import boundary
            points=boundary(self.records,index,self.quads.mates[index])[0]
        center = tuple(sum(p[k] for p in points)/len(points) for k in range(3))
        x,y,z = self.view_point(*center,basis=basis,distance=distance)
        depth = distance if self.is_ortho(basis) else z
        if not self.is_ortho(basis) and depth<self.near_distance():
            return None
        cx,cy,focal = screen
        px,py = cx+x*focal/depth,cy-y*focal/depth
        left,top,width,height = box
        if not (left+4<=px<left+width-4 and top+4<=py<top+height-4):
            return None
        return px,py,z

    def navigate_vertex(self,dx,dy):
        self.navigate_component(dx,dy,self.projected_vertex,"vertex")

    def navigate_triangle(self,dx,dy):
        self.navigate_component(dx,dy,self.projected_triangle,"triangle")

    def navigate_component(self,dx,dy,project,label):
        """Find the nearest projected component in a 90-degree direction sector."""
        projection = self.selection_projection()
        origin = project(self.selection_cursor,projection)
        if projection[0] in self._visibility_pending:
            self.status = "Checking visibility..."
            return
        best,index = None,self.selection_cursor
        cx,cy,_ = projection[3]
        for i in range(len(self.selection)):
            if i == self.selection_cursor:
                continue
            point = project(i,projection)
            if point is None:
                continue
            x,y,depth = point
            if origin is None:
                # After orbit/zoom, recover an on-screen component near the pane center.
                score = ((x-cx)**2+(y-cy)**2,0,depth,i)
            else:
                x,y = x-origin[0],y-origin[1]
                forward,across = x*dx+y*dy,abs(x*dy-y*dx)
                # Skip coincident projections and floating point axis noise.
                if forward <= .5 or across > forward+.5:
                    continue
                score = (x*x+y*y,across,depth,i)
            if best is None or score < best:
                best,index = score,i
        if best is None:
            self.status = "No %s in that direction" % label
        else:
            self.selection_cursor = index
            self.status = ""

    def vertex_info(self):
        """Return one selected position without caching a second geometry copy."""
        if self.selection_mode != "Vertices" or not any(self.selection):
            return None
        index = self.selection_cursor
        if not self.selection[index]:
            index = next(i for i,v in enumerate(self.selection) if v)
        point = vertex(self.records,index)
        linked = sum(1 for i,v in enumerate(self.selection)
                     if v and vertex(self.records,i) == point)
        return index,point,linked,sum(self.selection)

    def cycle_vertex_info(self, direction):
        """Visit distinct selected positions in coordinate order, with wrap."""
        info = self.vertex_info()
        if info is None:
            return
        current = info[1]
        best = edge = None
        best_index = edge_index = info[0]
        for i,selected in enumerate(self.selection):
            if not selected:
                continue
            point = vertex(self.records,i)
            if edge is None or (point < edge if direction > 0 else point > edge):
                edge,edge_index = point,i
            ahead = point > current if direction > 0 else point < current
            if ahead and (best is None or (point < best if direction > 0 else point > best)):
                best,best_index = point,i
        self.selection_cursor = best_index if best is not None else edge_index
        self.status = ""

    def selection_control(self, button):
        from picoware.system.buttons import (BUTTON_LEFT_BRACKET, BUTTON_RIGHT_BRACKET,
            BUTTON_SPACE, BUTTON_A, BUTTON_N, BUTTON_I, BUTTON_DELETE,
            BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN, BUTTON_P,
            BUTTON_J, BUTTON_K, BUTTON_B, BUTTON_COMMA, BUTTON_PERIOD, BUTTON_SLASH)
        if self.selection_mode == "Model" or self.mesh is None:
            return False
        if button == BUTTON_P:
            from .modes import control
            control(self,button,alias=True)
            return True
        if self.selection_camera:
            from picoware.system.buttons import BUTTON_R,BUTTON_TAB,BUTTON_ESCAPE,BUTTON_BACK
            if button in (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN,BUTTON_R,BUTTON_TAB,BUTTON_ESCAPE,BUTTON_BACK):return False
            # Only consume selection/edit shortcuts; global tool/menu shortcuts pass through.
            return button in (BUTTON_SPACE,BUTTON_A,BUTTON_N,BUTTON_I,BUTTON_DELETE,BUTTON_J,BUTTON_K,BUTTON_COMMA,BUTTON_PERIOD,BUTTON_SLASH,BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET)
        if self.selection_mode == "Islands" and not self.selection_camera and button in (BUTTON_LEFT,BUTTON_RIGHT):
            self.browse_island(1 if button == BUTTON_RIGHT else -1)
            return True
        if self.selection_mode == "Vertices":
            if button == BUTTON_B:
                self.show_vertex_info = not self.show_vertex_info
                return True
            if button in (BUTTON_J,BUTTON_K):
                self.cycle_vertex_info(1 if button == BUTTON_K else -1)
                return True
        if self.selection_mode in ("Vertices","Triangles","Quads","Edges"):
            if not self.selection_camera and button in (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN):
                if self.selection:
                    dx,dy = {BUTTON_LEFT:(-1,0),BUTTON_RIGHT:(1,0),BUTTON_UP:(0,-1),BUTTON_DOWN:(0,1)}[button]
                    if self.selection_mode == "Vertices":
                        self.navigate_vertex(dx,dy)
                    elif self.selection_mode == "Edges":
                        self.navigate_component(dx,dy,self.projected_edge,"edge")
                    else:
                        self.navigate_triangle(dx,dy)
                return True
        if button in (BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET,BUTTON_COMMA,BUTTON_PERIOD,BUTTON_SLASH) and self.selection:
            forward = button in (BUTTON_RIGHT_BRACKET,BUTTON_PERIOD,BUTTON_SLASH)
            if self.selection_mode == "Islands":
                self.browse_island(1 if forward else -1)
            else:
                visible = self.active_visibility()
                for step in range(1,len(self.selection)+1):
                    index = (self.selection_cursor+(step if forward else -step))%len(self.selection)
                    if visible is None or visible[index]:
                        self.selection_cursor = index
                        break
            self.status = ""
        elif button == BUTTON_SPACE:
            self.selection_toggle()
        elif button in (BUTTON_A,BUTTON_N):
            self.selection_fill("All" if button == BUTTON_A else "None")
        elif button == BUTTON_I and self.selection and self.selection_mode != "Islands":
            self.begin_edit_prompt("Index")
        elif button == BUTTON_DELETE and self.has_selection():
            self.edit_geometry("Delete")
        else:
            return False
        return True

    def draw_selection(self, draw, viewport=None, basis=None, distance=None, wire_only=False):
        if not wire_only and self._transform_pending:
            return
        if not wire_only and (self.boolean_preview is not None or self.selection_mode == "Model" or not self.selection):
            return
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w,h = int(draw.size.x),int(draw.size.y)
        box = (0,48,w,h-78) if viewport is None else viewport
        x,y,pw,ph = box
        cx,cy,focal = (w/2,h/2,h) if viewport is None else (x+pw/2,y+ph/2,ph)
        ortho = self.is_ortho(basis)
        near = self.near_distance()
        if not wire_only:
            self._selection_blank.pop(box,None)
            if self.selection_mode in ('Vertices','Triangles','Quads','Edges'):
                projection = box,basis,distance,(cx,cy,focal)
                # Queue a current mask before withholding stale or moving markers.
                self.active_visibility(projection)
                moving = (self._interactive_visibility and self._camera_pending and
                          box==self.selection_projection()[0])
                if moving or box in self._visibility_pending:
                    stamp = self._scene_stamps.get(box)
                    if stamp is not None:
                        self._selection_blank[box] = stamp
                    return
            elif (self._interactive_visibility and self._camera_pending and
                  box==self.selection_projection()[0]):
                return

        def camera(point):
            a,b,c = self.view_point(*point,basis=basis,distance=distance)
            return (a,b,max(near,distance) if ortho else c)

        def project(p):
            depth = distance if ortho else p[2]
            return (cx+p[0]*focal/depth,cy-p[1]*focal/depth)

        def edge(a,b,color):
            if a[2] < near and b[2] < near:
                return
            if a[2] < near:
                t = (near-a[2])/(b[2]-a[2])
                a = tuple(a[i]+t*(b[i]-a[i]) for i in range(3))
            if b[2] < near:
                t = (near-b[2])/(a[2]-b[2])
                b = tuple(b[i]+t*(a[i]-b[i]) for i in range(3))
            clipped_line(draw,project(a),project(b),box,color)

        if wire_only:
            from .wireframe import draw_wire
            draw_wire(self,draw,box,basis,distance,(cx,cy,focal),ortho,near)
            return

        if not wire_only and self.selection_mode == "Edges":
            self.draw_selected_edges(draw,(box,basis,distance,(cx,cy,focal)),camera,edge)
        elif wire_only or self.selection_mode in ("Triangles","Quads","Islands"):
            visible = self.visible_triangle_mask((box,basis,distance,(cx,cy,focal))) if not wire_only and self.selection_mode in ("Triangles","Quads") else None
            count = len(self.records)//40
            island = set(self.active_island()) if not wire_only and self.selection_mode == "Islands" else None
            if not wire_only and (sum(self.selection)>16 or self.selection_mode=="Quads"):
                # Shared selected edges are projected and drawn once, with the
                # cursor/active island taking precedence over yellow selection.
                from .wireframe import draw_wire
                flags=bytearray(count)
                for i in range(count):
                    if visible is not None and not visible[i]:continue
                    if i==self.selection_cursor or (self.selection_mode=="Quads" and self.quads.mates[i]==self.selection_cursor) or (island is not None and i in island):flags[i]=2
                    elif self.selection[i]:flags[i]=1
                if self.selection_mode=='Quads':
                    for j in range(0,len(self.quads.pairs),2):
                        a,b=self.quads.pairs[j],self.quads.pairs[j+1]
                        value=max(flags[a],flags[b]);flags[a]=flags[b]=value
                draw_wire(self,draw,box,basis,distance,(cx,cy,focal),ortho,near,flags)
                return
            order = (list(i for i in range(count) if i not in island)+list(sorted(island))) if island is not None else range(count if wire_only else count+1)
            for slot in order:
                if not wire_only and island is None and slot == self.selection_cursor:
                    continue
                i = self.selection_cursor if slot == count else slot
                if visible is not None and not visible[i]:
                    continue
                selected = False if wire_only else self.selection[i]
                if not wire_only and not selected and i != self.selection_cursor and (island is None or i not in island):
                    continue
                points = [self.view_point(*vertex(self.records,i*3+j),basis=basis,distance=distance)
                          for j in range(3)]
                if wire_only and self.backface_culling:
                    from .viewport import face_direction
                    if face_direction(points, ortho=ortho) <= 0:
                        continue
                if ortho:
                    points = [(p[0],p[1],max(near,distance)) for p in points]
                color = 0xBDF7 if wire_only else 0x07FF if i == self.selection_cursor or (island is not None and i in island) else 0xFFE0
                for j in range(3):
                    edge(points[j],points[(j+1)%3],color)
        else:
            visible = self.visible_vertex_mask((box,basis,distance,(cx,cy,focal)))
            # Merge marker state at coincident positions, with cursor priority.
            groups,representatives = self.vertex_groups()
            flags = bytearray(len(self.selection))
            for i,selected in enumerate(self.selection):
                if visible is None or visible[i]:
                    representative = groups[i]
                    flags[representative] = max(flags[representative],3 if i==self.selection_cursor else 2 if selected else 1)
            cursor = groups[self.selection_cursor]
            for slot in range(len(representatives)+1):
                i = cursor if slot==len(representatives) else representatives[slot]
                if slot<len(representatives) and i==cursor:
                    continue
                state = flags[i]
                if not state:
                    continue
                point = camera(vertex(self.records,i))
                if point[2] < near:
                    continue
                px,py = project(point)
                radius = 4 if state==3 else 2 if state==2 else 1
                if x+radius <= px < x+pw-radius and y+radius <= py < y+ph-radius:
                    draw._rectangle(int(px)-radius,int(py)-radius,radius*2+1,radius*2+1,
                                    0x07FF if state==3 else 0xFFE0 if state==2 else 0x7BEF)
