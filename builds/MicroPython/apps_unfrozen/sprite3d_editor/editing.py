"""Transactional component edits and creation commands."""

from struct import pack_into
from .creation import primitive, triangle
from .selection import vertex


class GeometryEditing:
    def apply_geometry(self, records, label, selected=None, quads=None):
        from picoware.engine.sprite3d import Sprite3D
        if len(records)%40 or len(records)//40 > self.document_capacity():
            raise ValueError("Triangle limit exceeded")
        if records == self.records and (quads is None or list(quads)==list(self.quads.pairs)):
            return
        # Prepare the small selection mask before changing geometry/history.
        mask = bytearray(len(records)//40)
        if selected is not None:
            for i in selected:
                mask[i] = 1
        mode='Quads' if self.selection_mode=='Quads' else 'Triangles'
        from .quads import Faces,unchanged
        faces=Faces(records,unchanged(self.records,records,self.quads.pairs) if quads is None else quads)
        if mode=='Quads':faces.expand(mask)
        backup = self.history.store_document(self.records,geometry=records!=self.records)
        try:
            self.history.commit(backup,label,lambda data:self.replace_records(data,quads=faces,metadata_only=records==self.records),records)
        except Exception:
            self.history.release(backup)
            raise
        self.selection_mode = mode
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
                if len(self.records)//40+len(indices) > self.document_capacity():
                    raise ValueError("Triangle limit exceeded")
            from .quads import remap
            from array import array
            pairs=array('I',self.quads.pairs)
            records = bytearray(self.records)
            selected = indices
            if action == "Duplicate":
                start = len(records)//40
                for i in indices:
                    records.extend(self.records[i*40:i*40+40])
                pairs.extend(remap(self.quads.pairs,{old:start+i for i,old in enumerate(indices)}))
                selected = range(start,len(records)//40)
            elif action == "Delete":
                chosen = set(indices)
                records = bytearray()
                for i in range(len(self.records)//40):
                    if i not in chosen:
                        records.extend(self.records[i*40:i*40+40])
                pairs=remap(self.quads.pairs,{old:i for i,old in enumerate(j for j in range(len(self.records)//40) if j not in chosen)})
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
            if action=='Flip winding':
                from .quads import valid_pairs
                pairs=valid_pairs(records,pairs)
            self.apply_geometry(records,action,selected,pairs)
            if color is not None:
                self.paint_color = color
            if action == "Duplicate" and self.move_on_duplicate:
                self.begin_transform("Move", selected_only=True)
                if self.transform is None and self.dialog is not None:
                    self.dialog = ("Mesh added; Move unavailable",self.dialog[1]+"\nThe new geometry was kept.")
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Edit failed",str(exc) or "Not enough memory")

    def create_geometry(self, kind):
        try:
            if self.mesh is None:
                self.new_document()
            from array import array
            addition_pairs=array("I")
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
                center=self.projection_center(self.panes[self.active_pane][3]) if self.four_view else self.center
                addition = primitive(kind,self.grid_step*2,(center[0],self.ground,center[2]),self.paint_color,addition_pairs)
            start = len(self.records)//40
            from picoware.engine.sprite3d import Sprite3D
            if start+len(addition)//40 > self.document_capacity():
                raise ValueError("Triangle limit exceeded")
            records = bytearray(self.records)
            records.extend(addition)
            self.apply_geometry(records,"Create "+kind,range(start,len(records)//40),
                                list(self.quads.pairs)+[start+i for i in addition_pairs])
            if self.auto_fit_creation or start == 0:
                self.fit_view()
            if kind != "Face from vertices" and self.move_on_create:
                self.begin_transform("Move", selected_only=True)
                if self.transform is None and self.dialog is not None:
                    self.dialog = ("Mesh added; Move unavailable",self.dialog[1]+"\nThe new geometry was kept.")
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ("Create failed",str(exc) or "Not enough memory")

    def begin_edit_prompt(self, kind):
        keyboard = self.vm.keyboard
        keyboard.reset()
        keyboard.title = "RGB565 color (0000-FFFF)" if kind == "Color" else "Component index (1-%d)" % (len(self.quads.reps) if self.selection_mode=="Quads" else len(self.selection))
        keyboard.response = "%04X" % self.paint_color if kind == "Color" else str((list(self.quads.reps).index(self.selection_cursor) if self.selection_mode=="Quads" else self.selection_cursor)+1)
        if kind == "Decimate":
            keyboard.title = "Keep triangles % (1-100)"
            keyboard.response = "50"
        keyboard.run(force=True)
        keyboard.run(force=True)
        self.edit_prompt = kind

    def run_edit_prompt(self):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_ESCAPE
        self._scene_keys.clear()
        keyboard = self.vm.keyboard
        if self.vm.input_manager.button in (BUTTON_BACK,BUTTON_ESCAPE):
            self.vm.input_manager.reset()
            keyboard.reset()
            self.edit_prompt = None
            self.draw_frame()
        elif keyboard.is_finished:
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
                    if not 0 <= index < (len(self.quads.reps) if self.selection_mode=="Quads" else len(self.selection)):
                        raise ValueError("Component index is out of range")
                    self.selection_cursor = self.quads.reps[index] if self.selection_mode=="Quads" else index
            except ValueError as exc:
                self.dialog = ("Invalid value",str(exc))
            self.draw_frame()
        elif not keyboard.run():
            keyboard.reset()
            self.edit_prompt = None
            self.draw_frame()
