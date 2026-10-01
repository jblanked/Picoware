"""Keyboard transform tools, precision steps, and grid snapping."""

from math import isfinite, floor
from .assets import transformed_records, record_bounds
from time import ticks_ms
from .ui import display_number
from .meshes import apply_updates


from .preferences import check_step


def snap_value(value, spacing, origin=0):
    units = (value-origin)/spacing
    nearest = floor(units+.5) if units >= 0 else -floor(-units+.5)
    return origin+nearest*spacing


class TransformTools:
    """Preview edits from original geometry until Apply or Cancel."""

    def transform_axes(self):
        """Move stays in the active view plane; other tools retain all axes."""
        if self.transform is None or self.transform["kind"] != "Move":
            return (0,1,2)
        name = self.panes[self.active_pane][0] if self.four_view else self.view_name
        return {"Front":(0,1),"Back":(0,1),"Top":(0,2),
                "Bottom":(0,2),"Side":(2,1)}.get(name,(0,1,2))

    def ensure_transform_axis(self):
        if self.transform is not None:
            axes = self.transform_axes()
            if self.transform["axis"] not in axes:
                self.transform["axis"] = axes[0]

    def begin_transform(self, kind):
        backup = None
        try:
            if not self.records:
                raise ValueError("Create geometry first")
            mask = self.selection_mask()
            low,high = self.selected_bounds(mask)
            backup = (None,len(self.records),0,self.records)
            self.transform = {"kind": kind, "source": backup,
                "original": self.records, "buffer": None, "gizmo": {},
                "values": [1.0 if kind == "Scale" else 0.0]*3,
                "axis": 0, "pivot": 0, "uniform": True, "low": low, "high": high,
                "step": self.steps[kind], "snap": self.snap, "mask": mask}
            self.ensure_transform_axis()
        except (ValueError, OSError, MemoryError) as exc:
            if backup is not None:
                self.history.release(backup)
            self.dialog = ("Cannot start edit", str(exc) or "Not enough memory")
            return
        self.status = ""


    def cycle_transform(self):
        """Apply the current adjustment and start the next tool without losing selection."""
        previous = self.transform
        if previous is None:
            self.begin_transform("Move")
            return
        kinds = ("Move","Scale","Rotate")
        self.begin_transform(kinds[(kinds.index(previous["kind"])+1)%3])
        following = self.transform
        if following is previous:
            if self.dialog is not None:
                self.status = self.dialog[1]
                self.dialog = None
            return
        try:
            self.commit_transform(previous)
        except Exception:
            self.history.release(following["source"])
            self.transform = previous
            raise
        following["axis"] = previous["axis"]
        following["pivot"] = previous["pivot"]
        self.ensure_transform_axis()

    def preview_transform(self):
        t = self.transform
        pivot = [(t["low"][i]+t["high"][i])*.5 for i in range(3)]
        if t["pivot"] == 1:
            pivot[1] = t["low"][1]
        elif t["pivot"] == 2:
            pivot = [0,0,0]
        if t["kind"] == "Scale" and any(v <= 0 or v > 1e6 for v in t["values"]):
            raise ValueError("Scale must be > 0 and <= 1000000")
        original = t["original"]
        records = t["buffer"]
        if records is None:
            records = bytearray(len(original))
        transformed_records(original,t["kind"],t["values"],pivot,t["mask"],
                            result=records)
        bounds = record_bounds(records)
        if records == self.records:
            t["buffer"] = records
            return
        old = self.records
        pending = self._transform_pending
        self._transform_pending = self._interactive_visibility
        try:
            self.replace_records(records,preview=True,bounds=bounds)
        except Exception:
            self._transform_pending = pending
            raise
        # Keep at most two working buffers; the source is never modified.
        t["buffer"] = old if old is not original else None
        self._transform_finished = ticks_ms()

    def commit_transform(self,t):
        """Store Undo before updating the canonical mesh on Apply."""
        if self.records == t["original"]:
            return
        update = self._model_buffer.prepare(self.records)
        snapshot = None
        updates = (update,)
        try:
            snapshot = self.history.store(t['original'])
            self.history.commit(snapshot,t['kind'],lambda _: apply_updates(updates))
        except Exception:
            update.discard()
            if snapshot is not None:
                self.history.release(snapshot)
            raise
        old = self.mesh
        self.mesh = update.mesh
        if old is not self.mesh:
            old.clear_triangles()


    def run_transform(self, inputs):
        from picoware.system.buttons import (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT,
            BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ESCAPE, BUTTON_BACK, BUTTON_E,
            BUTTON_P, BUTTON_U, BUTTON_S, BUTTON_T, BUTTON_MINUS, BUTTON_PLUS, BUTTON_EQUAL,
            BUTTON_B, BUTTON_J, BUTTON_K, BUTTON_W, BUTTON_G)
        self.ensure_transform_axis()
        t = self.transform
        old_values, old_pivot, old_uniform = t["values"][:], t["pivot"], t["uniform"]
        old_step = t["step"]
        update = False
        try:
            if self.numeric:
                self._scene_keys.clear()
                keyboard = self.vm.keyboard
                if keyboard.is_finished:
                    response = keyboard.response.strip()
                    unchanged = response == t.get("numeric_text")
                    value = t["numeric_value"] if unchanged else float(response)
                    if not isfinite(value):
                        raise ValueError("Enter a finite number")
                    keyboard.reset()
                    self.numeric = False
                    if self.numeric_target == "step":
                        check_step(t["kind"], value)
                        t["step"] = value
                        self.status = ""
                    else:
                        t["values"][t["axis"]] = value
                        update = not unchanged
                elif not keyboard.run():
                    keyboard.reset()
                    self.numeric = False
                else:
                    return
            else:
                button = inputs.button
                inputs.reset()
                if button == BUTTON_G:
                    self.cycle_transform()
                elif button == BUTTON_W:
                    self.set_shading()
                elif self.selection_mode == "Vertices" and button in (BUTTON_B,BUTTON_J,BUTTON_K):
                    self.selection_control(button)
                elif self.pane_control(button):
                    self.ensure_transform_axis()
                elif button in (BUTTON_BACK, BUTTON_ESCAPE):
                    if self.records != t['original']:
                        self.replace_records(t['original'],preview=True,
                                             bounds=record_bounds(t['original']))
                    self._transform_pending = False
                    self.transform = None
                    self.status = "Transform cancelled"
                elif button == BUTTON_CENTER:
                    self.commit_transform(t)
                    self._transform_pending = False
                    self.transform = None
                    self.status = "Transform applied"
                elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                    axes = self.transform_axes()
                    t["axis"] = axes[(axes.index(t["axis"])+(1 if button == BUTTON_RIGHT else -1))%len(axes)]
                elif button in (BUTTON_E, BUTTON_T):
                    keyboard = self.vm.keyboard
                    keyboard.reset()
                    self.numeric_target = "step" if button == BUTTON_T else "value"
                    keyboard.title = t["kind"] + (" step" if button == BUTTON_T else " " + "XYZ"[t["axis"]]) + (" degrees" if t["kind"] == "Rotate" else " value")
                    t["numeric_value"] = t["step"] if button == BUTTON_T else t["values"][t["axis"]]
                    t["numeric_text"] = display_number(t["numeric_value"])
                    keyboard.response = t["numeric_text"]
                    keyboard.run(force=True)
                    keyboard.run(force=True)
                    self.numeric = True
                    return
                elif button == BUTTON_S:
                    t["snap"] = not t["snap"]
                    self.status = ""
                elif button in (BUTTON_MINUS, BUTTON_PLUS, BUTTON_EQUAL):
                    value = t["step"] * (.1 if button == BUTTON_MINUS else 10)
                    check_step(t["kind"],value)
                    t["step"] = value
                    self.status = ""
                elif button == BUTTON_P:
                    t["pivot"] = (t["pivot"]+1) % (2 if t["kind"] == "Move" else 3)
                    update = t["kind"] != "Move"
                elif button == BUTTON_U and t["kind"] == "Scale":
                    t["uniform"] = not t["uniform"]
                    update = t["uniform"]
                elif button in (BUTTON_UP, BUTTON_DOWN):
                    axis = t["axis"]
                    direction = 1 if button == BUTTON_UP else -1
                    step = max(t["step"],self.grid_step) if t["snap"] and t["kind"] == "Move" else t["step"]
                    value = t["values"][axis] + direction*step
                    if t["snap"]:
                        if t["kind"] == "Move":
                            anchor = (t["low"][axis]+t["high"][axis])*.5
                            if axis == 1 and t["pivot"] == 1:
                                anchor = t["low"][1]
                            origin = self.ground if axis == 1 else 0
                            value = snap_value(anchor+value, self.grid_step, origin)-anchor
                        else:
                            value = snap_value(value, step, 1 if t["kind"] == "Scale" else 0)
                    t["values"][axis] = value
                    update = True
            if update:
                if t["kind"] == "Scale" and t["uniform"]:
                    t["values"] = [t["values"][t["axis"]]]*3
                self.preview_transform()
                self.status = ""
        except (ValueError, OverflowError, MemoryError, OSError) as exc:
            t["values"], t["pivot"], t["uniform"] = old_values, old_pivot, old_uniform
            t["step"] = old_step
            if self.numeric:
                self.vm.keyboard.reset()
                self.numeric = False
            self.status = str(exc) or "Not enough memory"
        self.steps[t["kind"]] = t["step"]
        self.snap = t["snap"]
        self.draw_frame()
