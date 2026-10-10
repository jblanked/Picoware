"""SD operand captures and reversible Boolean previews."""
from time import ticks_ms, ticks_diff
from .csg import boolean_steps, MAX_INPUT


def close_job(editor, release=True):
    job = editor.boolean_job
    if job is not None:
        job['worker'].close()
        if release:
            editor.history.release(job['state'][1])
        editor.boolean_job = None


class BooleanTools:
    def clear_operands(self):
        for operand in self.boolean_operands:
            if operand is not None:
                self.history.release(operand[0])
        self.boolean_operands = [None,None]

    def capture_operand(self, slot):
        snapshot = None
        try:
            if self.selection_mode in ('Vertices','Edges'):
                raise ValueError('Choose Islands, Model or Triangles')
            indices = self.active_island() if self.boolean_workflow is not None else self.selected_triangles()
            if not 1<=len(indices)<=MAX_INPUT:
                raise ValueError('Select 1-%d faces for this solid' % MAX_INPUT)
            other = self.boolean_operands[1-slot]
            if other is not None and any(i in other[1] for i in indices):
                raise ValueError('A and B must use different faces')
            records = bytearray()
            for i in indices:
                records.extend(self.records[i*40:i*40+40])
            indices = tuple(indices)
            replacement = None
            if self.boolean_workflow is not None:
                from .assets import record_bounds
                low,high = record_bounds(records)
                center = tuple((low[i]+high[i])*.5 for i in range(3))
                island = next(i+1 for i,g in enumerate(self.get_islands()) if indices[0] in g)
                labels = list(self.boolean_workflow['labels'])
                labels[slot] = (center,island,len(indices))
                replacement = tuple(labels)
            snapshot = self.history.store(records)
            operand = (snapshot,indices)
            previous = self.boolean_operands[slot]
            self.boolean_operands[slot] = operand
            snapshot = None
            if replacement is not None:
                self.boolean_workflow['labels'] = replacement
            if previous is not None:
                self.history.release(previous[0])
            self.status = 'Operand %s: %d faces' % ('AB'[slot],len(indices))
            return True
        except (ValueError,OSError,MemoryError) as exc:
            if snapshot is not None:
                self.history.release(snapshot)
            self.dialog = ('Cannot set operand',str(exc) or 'Not enough memory')
            return False

    def select_connected_solid(self):
        """Select the edge-connected island under the triangle cursor."""
        try:
            if self.selection_mode != 'Triangles' or not self.selection:
                raise ValueError('Choose Triangles and browse to a face')
            selected = self.active_island()
            count = len(self.records)//40
            mask = bytearray(count)
            for i in selected:
                mask[i] = 1
            self.selection = mask
            self.status = 'Selected solid: %d faces' % len(selected)
        except (ValueError,MemoryError) as exc:
            self.dialog = ('Selection failed',str(exc) or 'Not enough memory')

    def begin_boolean(self, operation):
        backup = None
        try:
            automatic = not any(self.boolean_operands)
            if automatic:
                groups = self.get_islands()
                if len(groups) != 2:
                    raise ValueError('Found %d islands. Use Select > Islands, then set A and B' % len(groups))
                if self.selection_mode == 'Islands' and self.selection_cursor in groups[1]:
                    groups = [groups[1],groups[0]]
            elif not all(self.boolean_operands):
                raise ValueError('Set the other operand, or clear operands for automatic islands')
            captured = []
            removed = set()
            for slot,(snapshot,indices) in enumerate(self.boolean_operands if not automatic else [(None,g) for g in groups]):
                data = self.history.read(snapshot) if snapshot is not None else b''.join(self.records[i*40:i*40+40] for i in indices)
                for j,i in enumerate(indices):
                    if self.records[i*40:i*40+40] != data[j*40:j*40+40]:
                        raise ValueError('Operand %s changed; select it again' % 'AB'[slot])
                captured.append(data)
                removed.update(indices)
            backup = self.history.store_document(self.records)
            stats = []
            self.boolean_job = {
                'worker':boolean_steps(captured[0],captured[1],operation,stats),
                'state':(operation,backup,self.selection_mode,self.selection,self.selection_cursor),
                'removed':removed,'automatic':automatic,'stats':stats,
            }
            self.selection_camera = False
            self.status = operation+': preparing; Esc cancels'
        except (ValueError,OSError,MemoryError) as exc:
            if backup is not None:
                self.history.release(backup)
            self.dialog = ('Boolean failed',str(exc) or 'Not enough memory')
            self.status = ''

    def run_boolean_job(self, inputs):
        from picoware.system.buttons import BUTTON_BACK, BUTTON_ESCAPE
        job = self.boolean_job
        button = inputs.button
        inputs.reset()
        try:
            if button in (BUTTON_BACK,BUTTON_ESCAPE):
                close_job(self)
                self.status = 'Boolean cancelled'
            else:
                started = ticks_ms()
                for _ in range(16):
                    update = next(job['worker'])
                    if update[0] == 'done' or ticks_diff(ticks_ms(),started)>=12:
                        break
                if update[0] == 'done':
                    result = update[1]
                    records = bytearray()
                    for i in range(len(self.records)//40):
                        if i not in job['removed']:
                            records.extend(self.records[i*40:i*40+40])
                    start = len(records)//40
                    records.extend(result)
                    mask = bytearray(len(records)//40)
                    for i in range(start,len(mask)):
                        mask[i] = 1
                    self.replace_records(records)
                    self.boolean_preview = job['state']
                    self.selection_camera = False
                    self.selection_mode,self.selection,self.selection_cursor = ('Quads' if job['state'][2]=='Quads' else 'Triangles'),mask,start if result else 0
                    if self.selection_mode=='Quads':self.quads.expand(mask)
                    self.status = '%s%d -> %d tris (cleaned)' % (
                        'Auto A-B: ' if job['automatic'] else '',job['stats'][0],len(result)//40)
                    close_job(self,release=False)
                else:
                    self.status = job['state'][0]+': '+update[1]
        except (ValueError,OSError,MemoryError) as exc:
            close_job(self)
            self.dialog = ('Boolean failed',str(exc) or 'Not enough memory')
            self.status = ''
        self.draw_frame()


    def run_boolean(self, inputs):
        from picoware.system.buttons import BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE, BUTTON_W
        from .modes import control
        operation,backup,mode,mask,cursor = self.boolean_preview
        button = inputs.button
        inputs.reset()
        try:
            if control(self,button,tool=True):pass
            elif self.pane_control(button):
                if self.dialog is not None:
                    self.status = self.dialog[1]
                    self.dialog = None
            elif button == BUTTON_W:
                self.set_shading()
            elif button == BUTTON_CENTER:
                if not self.history.matches(backup,self.records):
                    self.history.commit(backup,operation if operation == 'Decimate' else 'Boolean '+operation)
                else:
                    self.history.release(backup)
                self.boolean_preview = None
                if self.boolean_workflow is not None:
                    self.end_boolean_workflow(restore=False)
                else:
                    self.clear_operands()
                self.status = operation+' applied'
            elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                records=self.history.read(backup)
                from .quads import history_decode
                data=self.history.document_data(backup)
                faces=history_decode(data,records)[0] if data is not None else None
                old_mode=self.selection_mode;self.selection_mode=mode
                try:self.replace_records(records,quads=faces)
                except Exception:self.selection_mode=old_mode;raise
                self.history.release(backup)
                self.selection_mode,self.selection,self.selection_cursor = mode,mask,cursor
                self.boolean_preview = None
                self.status = operation+' cancelled'
                if self.boolean_workflow is not None:
                    self.boolean_workflow['stage'] = 'operation'
                    self.boolean_workflow['row'] = self.boolean_workflow['operation']
                    self.status = ''

        except (ValueError,OSError,MemoryError) as exc:
            self.status = str(exc) or 'Not enough memory; retry'
        self.draw_frame()
