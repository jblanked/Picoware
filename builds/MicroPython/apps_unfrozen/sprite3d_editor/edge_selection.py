"""Unique mesh-edge picking with compact corner references and linked endpoints."""
from array import array
from .selection import vertex


class EdgeMidpoints:
    """Expose samples on demand without retaining another geometry list."""
    def __init__(self,editor):
        self.editor = editor

    def __len__(self):
        return len(self.editor.get_edges())

    def __getitem__(self,index):
        return self.editor.edge_midpoint(index)


class EdgeSelection:
    def get_edges(self):
        if self._edge_reps is None:
            seen,edges = set(),array('H')
            for i in range(len(self.records or b'')//40*3):
                a,b = vertex(self.records,i),vertex(self.records,(i//3)*3+(i+1)%3)
                if a==b:
                    continue
                key = (a,b) if a<b else (b,a)
                if key not in seen:
                    seen.add(key)
                    edges.append(i)
            self._edge_reps = edges
        return self._edge_reps

    def edge_points(self,index):
        i = self.get_edges()[index]
        return vertex(self.records,i),vertex(self.records,(i//3)*3+(i+1)%3)

    def edge_midpoint(self,index):
        a,b = self.edge_points(index)
        return tuple((a[k]+b[k])*.5 for k in range(3))

    def visible_edge_mask(self,projection=None):
        if self.xray_vertices:
            return None
        box,basis,distance,screen = self.selection_projection() if projection is None else projection
        key = ('edges',tuple(self.center),basis,distance,box,screen,self.near_distance())
        cached = self.vertex_visibility_cache.get(box)
        mask = cached[1] if cached is not None and cached[0] == key else None
        if mask is None:
            if self._interactive_visibility:
                from .visibilityjobs import request
                return request(self,box,key,
                    (self.records,tuple(self.center),basis,distance,box,screen,self.is_ortho(basis)),
                    {'near':self.near_distance(),'samples':EdgeMidpoints(self)},len(self.get_edges()))
            from .visibility import visible_vertices
            try:
                points = EdgeMidpoints(self)
                mask = visible_vertices(self.records,self.center,basis,distance,box,screen,
                    self.is_ortho(basis),near=self.near_distance(),samples=points)
            except MemoryError:
                mask = bytearray(len(self.get_edges()))
                self.status = 'Visibility memory full; enable X-Ray'
            if box not in self.vertex_visibility_cache and len(self.vertex_visibility_cache)>=4:
                del self.vertex_visibility_cache[next(iter(self.vertex_visibility_cache))]
            self.vertex_visibility_cache[box] = (key,mask)
        return mask

    def projected_edge(self,index,projection):
        visible = self.visible_edge_mask(projection)
        if visible is not None and not visible[index]:
            return None
        box,basis,distance,(cx,cy,focal) = projection
        x,y,z = self.view_point(*self.edge_midpoint(index),basis=basis,distance=distance)
        depth = distance if self.is_ortho(basis) else z
        if not self.is_ortho(basis) and depth<self.near_distance():
            return None
        px,py = cx+x*focal/depth,cy-y*focal/depth
        left,top,w,h = box
        if left+4<=px<left+w-4 and top+4<=py<top+h-4:
            return px,py,z
        return None

    def edge_vertex_mask(self):
        # Every corner sharing either endpoint moves together, avoiding cracks.
        points = set()
        for i,selected in enumerate(self.selection):
            if selected:
                points.update(self.edge_points(i))
        return bytearray(vertex(self.records,i) in points for i in range(len(self.records)//40*3))

    def selected_edge_faces(self):
        chosen = set()
        for i,selected in enumerate(self.selection):
            if selected:
                a,b = self.edge_points(i)
                chosen.add((a,b) if a<b else (b,a))
        faces = []
        for face in range(len(self.records)//40):
            points = [vertex(self.records,face*3+j) for j in range(3)]
            for j,a in enumerate(points):
                b = points[(j+1)%3]
                if ((a,b) if a<b else (b,a)) in chosen:
                    faces.append(face)
                    break
        return faces

    def draw_selected_edges(self,draw,projection,camera,edge):
        visible = self.visible_edge_mask(projection)
        count = len(self.selection)
        for slot in range(count+1):
            if slot==self.selection_cursor:
                continue
            i = self.selection_cursor if slot==count else slot
            if visible is not None and not visible[i]:
                continue
            if not self.selection[i] and i!=self.selection_cursor:
                continue
            a,b = self.edge_points(i)
            color = 0x07FF if i==self.selection_cursor else 0xFFE0
            edge(camera(a),camera(b),color)
            marker = self.projected_edge(i,projection)
            if marker is not None:
                draw._fill_circle(int(marker[0]),int(marker[1]),2,color)
