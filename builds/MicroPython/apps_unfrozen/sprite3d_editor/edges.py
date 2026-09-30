"""Compact model-space edge measurements, clipped to each editor viewport."""
from math import sqrt
from struct import unpack_from

DIGITS = ((7,5,5,5,7),(2,6,2,2,7),(7,1,7,4,7),(7,1,7,1,7),
          (5,5,7,1,1),(7,4,7,1,7),(7,4,7,5,7),(7,1,2,2,2),
          (7,5,7,5,7),(7,5,7,1,7))


def label_width(text):
    return sum(2 if c=='.' else 4 for c in text)-1


def small_number(draw,x,y,text):
    """Three-by-five digits keep a five-character measurement only 17px wide."""
    draw._fill_rectangle(x-1,y-1,label_width(text)+2,7,0x1082)
    for char in text:
        if char=='.':
            draw._fill_rectangle(x,y+4,1,1,0xFFFF)
            x+=2
        else:
            for row,bits in enumerate(DIGITS[int(char)]):
                for col in range(3):
                    if bits & (4>>col):
                        draw._fill_rectangle(x+col,y+row,1,1,0xFFFF)
            x+=4


class EdgeTools:
    def edge_labels(self,viewport=None,basis=None,distance=None):
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w,h = int(self.vm.draw.size.x),int(self.vm.draw.size.y)
        box = (0,48,w,h-78) if viewport is None else viewport
        left,top,pw,ph = box
        screen = (w/2,h/2,h) if viewport is None else (left+pw/2,top+ph/2,ph)
        key = (tuple(self.center),basis,distance,box,screen,self.xray_vertices)
        cached = self.edge_label_cache.get(box)
        if cached is not None and cached[0] == key:
            return cached[1]
        ortho,near = self.is_ortho(basis),self.near_distance()
        cx,cy,focal = screen
        def project(point):
            x,y,z = self.view_point(*point,basis=basis,distance=distance)
            if not ortho and z<near:
                return None
            depth = distance if ortho else z
            return cx+x*focal/depth,cy-y*focal/depth,z
        candidates,seen = [],set()
        # Bound temporary annotation storage, even for a 2,048-face document.
        for offset in range(0,len(self.records),40):
            points = [unpack_from('<3f',self.records,offset+i*12) for i in range(3)]
            for i,a in enumerate(points):
                b = points[(i+1)%3]
                edge = (a,b) if a<b else (b,a)
                if edge in seen:
                    continue
                middle = tuple((a[k]+b[k])/2 for k in range(3))
                p = project(middle)
                if p is None:
                    continue
                length = sqrt(sum((a[k]-b[k])**2 for k in range(3)))
                text = '%05.2f' % length
                width = label_width(text)
                x,y = int(p[0]-width/2),int(p[1])-2
                if not (left+2<=x and x+width+2<left+pw and top+2<=y and y+7<top+ph):
                    continue
                pa,pb = project(a),project(b)
                if pa is not None and pb is not None and (pa[0]-pb[0])**2+(pa[1]-pb[1])**2<(width+4)**2:
                    continue
                seen.add(edge)
                candidates.append((p[2],x,y,text,middle))
            if len(candidates)>=128:
                break
        if self.xray_vertices or not candidates:
            visible = None
        else:
            from .visibility import visible_vertices
            visible = visible_vertices(self.records,self.center,basis,distance,box,screen,ortho,
                                       near=near,samples=[c[4] for c in candidates])
        ordered = sorted(range(len(candidates)),key=lambda i:candidates[i][0])
        labels = []
        for i in ordered:
            if visible is not None and not visible[i]:
                continue
            _,x,y,text,_ = candidates[i]
            width = label_width(text)
            if any(x<ox+label_width(ot)+3 and x+width+3>ox and y<oy+8 and y+8>oy for ox,oy,ot in labels):
                continue
            labels.append((x,y,text))
            if len(labels)>=(48 if viewport is None else 24):
                break
        if box not in self.edge_label_cache and len(self.edge_label_cache)>=4:
            del self.edge_label_cache[next(iter(self.edge_label_cache))]
        self.edge_label_cache[box] = (key,labels)
        return labels

    def draw_edge_lengths(self,draw,viewport=None,basis=None,distance=None):
        if self._camera_pending:
            return
        if not self.show_edge_lengths or not self.records:
            return
        try:
            for x,y,text in self.edge_labels(viewport,basis,distance):
                small_number(draw,x,y,text)
        except MemoryError:
            self.edge_label_cache.clear()
            self.status = 'Edge labels: not enough memory'
