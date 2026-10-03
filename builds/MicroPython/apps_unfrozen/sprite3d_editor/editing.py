"""Transactional component edits and creation commands."""

from struct import pack_into
from .creation import primitive, triangle
from .selection import vertex


class GeometryEditing:
    def apply_geometry(self, records, label, selected=None):
        from picoware.engine.sprite3d import Sprite3D
        if len(records)%40 or len(records)//40 > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
            raise ValueError("Triangle limit exceeded")
        if records == self.records:
            return
        # Prepare the small selection mask before changing geometry/history.
        mask = bytearray(len(records)//40)
        if selected is not None:
            for i in selected:
                mask[i] = 1
        backup = self.history.store(self.records)
        try:
            self.history.commit(backup,label,self.replace_records,records)
        except Exception:
            self.history.release(backup)
            raise
        self.selection_mode = "Triangles"
        self.selection = mask
        self.selection_cursor = next((i for i,v in enumerate(mask) if v),0)
        self.status = label

    def clean_degenerates(self):
        """Clean the whole document; valid disconnected components are retained."""
        from .meshcleanup import remove_degenerates
        try:
            records,removed = remove_degenerates(self.records or b"")
            if not removed:
                self.status = "No degenerate faces found"
                return
            self.apply_geometry(records,"Remove degenerates")
            self.status = "Removed %d degenerate faces" % removed
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Cleanup failed",str(exc) or "Not enough memory")

    def clean_duplicates(self):
        from .meshcleanup import remove_duplicates
        try:
            records,removed = remove_duplicates(self.records or b"")
            if not removed:
                self.status = "No duplicate faces found"
                return
            self.apply_geometry(records,"Remove duplicates")
            self.status = "Removed %d duplicate faces" % removed
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Cleanup failed",str(exc) or "Not enough memory")

    def edit_geometry(self, action, color=None):
        try:
            indices = self.selected_triangles()
            if not indices:
                raise ValueError("Select geometry first")
            if self.selection_mode in ("Vertices","Edges") and action != "Delete":
                raise ValueError("Choose Model or Triangles mode")
            if action == "Duplicate":
                from picoware.engine.sprite3d import Sprite3D
                if len(self.records)//40+len(indices) > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
                    raise ValueError("Triangle limit exceeded")
            records = bytearray(self.records)
            selected = indices
            if action == "Duplicate":
                start = len(records)//40
                for i in indices:
                    records.extend(self.records[i*40:i*40+40])
                selected = range(start,len(records)//40)
            elif action == "Delete":
                chosen = set(indices)
                records = bytearray()
                for i in range(len(self.records)//40):
                    if i not in chosen:
                        records.extend(self.records[i*40:i*40+40])
                selected = None
            else:
                for i in indices:
                    offset = i*40
                    if action == "Color":
                        if color is None or not 0 <= color <= 65535:
                            raise ValueError("Use an RGB565 color from 0000 to FFFF")
                        pack_into("<H",records,offset+36,color)
                    elif action == "Wireframe":
                        records[offset+38] = 1-records[offset+38]
                    elif action == "Flip winding":
                        records[offset+12:offset+36] = self.records[offset+24:offset+36]+self.records[offset+12:offset+24]
                    else:
                        raise ValueError("Unknown edit")
            self.apply_geometry(records,action,selected)
            if color is not None:
                self.paint_color = color
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Edit failed",str(exc) or "Not enough memory")

    def create_geometry(self, kind):
        try:
            if self.mesh is None:
                self.new_document()
            if kind == "Face from vertices":
                if self.selection_mode != "Vertices":
                    raise ValueError("Select three vertices first")
                points = []
                for i,selected in enumerate(self.selection):
                    if selected:
                        point = vertex(self.records,i)
                        if point not in points:
                            points.append(point)
                            if len(points)>3:
                                break
                if len(points) != 3:
                    raise ValueError("Select exactly three distinct vertices")
                addition = triangle(points,self.paint_color)
            else:
                addition = primitive(kind,self.grid_step*2,(self.center[0],self.ground,self.center[2]),self.paint_color)
            start = len(self.records)//40
            from picoware.engine.sprite3d import Sprite3D
            if start+len(addition)//40 > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
                raise ValueError("Triangle limit exceeded")
            records = bytearray(self.records)
            records.extend(addition)
            self.apply_geometry(records,"Create "+kind,range(start,len(records)//40))
            self.fit_view()
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Create failed",str(exc) or "Not enough memory")

    def begin_edit_prompt(self, kind):
        keyboard = self.vm.keyboard
        keyboard.reset()
        keyboard.title = "RGB565 color (0000-FFFF)" if kind == "Color" else "Component index (1-%d)" % len(self.selection)
        keyboard.response = "%04X" % self.paint_color if kind == "Color" else str(self.selection_cursor+1)
        if kind == "Decimate":
            keyboard.title = "Keep triangles % (1-100)"
            keyboard.response = "50"
        keyboard.run(force=True)
        keyboard.run(force=True)
        self.edit_prompt = kind

    def run_edit_prompt(self):
        self._scene_keys.clear()
        keyboard = self.vm.keyboard
        if keyboard.is_finished:
            text = keyboard.response.strip()
            kind = self.edit_prompt
            keyboard.reset()
            self.edit_prompt = None
            try:
                if kind == "Color":
                    self.edit_geometry("Color",int(text.lstrip("#"),16))
                elif kind == "Decimate":
                    self.begin_decimation(float(text))
                else:
                    index = int(text)-1
                    if not 0 <= index < len(self.selection):
                        raise ValueError("Component index is out of range")
                    self.selection_cursor = index
            except ValueError as exc:
                self.dialog = ("Invalid value",str(exc))
            self.draw_frame()
        elif not keyboard.run():
            keyboard.reset()
            self.edit_prompt = None
            self.draw_frame()
