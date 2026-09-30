"""SD operand captures and reversible Boolean previews."""
from time import ticks_ms, ticks_diff
from .csg import boolean_steps, MAX_INPUT


class BooleanTools:
    def clear_operands(self):
        for operand in self.boolean_operands:
            if operand is not None:
                self.history.release(operand[0])
        self.boolean_operands = [None,None]

    def capture_operand(self, slot):
        try:
            if self.selection_mode in ('Vertices','Edges'):
                raise ValueError('Choose Islands, Model or Triangles')
            indices = self.selected_triangles()
            if not 1<=len(indices)<=MAX_INPUT:
                raise ValueError('Select 1-%d faces for this solid' % MAX_INPUT)
            other = self.boolean_operands[1-slot]
            if other is not None and any(i in other[1] for i in indices):
                raise ValueError('A and B must use different faces')
            records = bytearray()
            for i in indices:
                records.extend(self.records[i*40:i*40+40])
            snapshot = self.history.store(records)
            previous = self.boolean_operands[slot]
            self.boolean_operands[slot] = (snapshot,tuple(indices))
            if previous is not None:
                self.history.release(previous[0])
            self.status = 'Operand %s: %d faces' % ('AB'[slot],len(indices))
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ('Cannot set operand',str(exc) or 'Not enough memory')

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
            backup = self.history.store(self.records)
            stats = []
            self.boolean_job = {
                'worker':boolean_steps(captured[0],captured[1],operation,stats),
                'state':(operation,backup,self.selection_mode,self.selection,self.selection_cursor),
                'removed':removed,'automatic':automatic,'stats':stats,
            }
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
                self.history.release(job['state'][1])
                self.boolean_job = None
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
                    self.selection_mode,self.selection,self.selection_cursor = 'Triangles',mask,start if result else 0
                    self.status = '%s%d -> %d tris (cleaned)' % (
                        'Auto A-B: ' if job['automatic'] else '',job['stats'][0],len(result)//40)
                    self.boolean_job = None
                else:
                    self.status = job['state'][0]+': '+update[1]
        except (ValueError,OSError,MemoryError) as exc:
            self.history.release(job['state'][1])
            self.boolean_job = None
            self.dialog = ('Boolean failed',str(exc) or 'Not enough memory')
            self.status = ''
        self.draw_frame()


    def run_boolean(self, inputs):
        from picoware.system.buttons import BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE, BUTTON_W
        operation,backup,mode,mask,cursor = self.boolean_preview
        button = inputs.button
        inputs.reset()
        try:
            if self.pane_control(button):
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
                self.clear_operands()
                self.status = operation+' applied'
            elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                self.replace_records(self.history.read(backup))
                self.history.release(backup)
                self.selection_mode,self.selection,self.selection_cursor = mode,mask,cursor
                self.boolean_preview = None
                self.status = operation+' cancelled'
        except (ValueError,OSError,MemoryError) as exc:
            self.status = str(exc) or 'Not enough memory; retry'
        self.draw_frame()
