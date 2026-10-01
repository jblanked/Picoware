"""Model-only, time-based turntables with independent fitted camera state."""
from math import pi, sqrt
from time import ticks_ms, ticks_diff
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_SPACE, BUTTON_ESCAPE, BUTTON_BACK
from picoware.engine.camera import Camera, CAMERA_THIRD_PERSON
from .viewport import preview_mesh, view_basis
from .meshes import MeshBuffer

FRAME_MS = 50
TURN_MS = 20000
BACKGROUND = 0x1082


class Turntable:
    def __init__(self, editor, isometric=False):
        if not editor.records:
            raise ValueError("Create or open a model first")
        self.buffer = MeshBuffer()
        self.editor = editor
        self.records = editor.records
        self.isometric = isometric
        self.paused = False
        self.phase = 0
        self.last_ms = ticks_ms()
        self.camera = None
        self.saved_camera = None
        low, high = editor.bounds
        self.center = tuple((low[i]+high[i])*.5 for i in range(3))
        radius = max(1e-9, sqrt(sum((high[i]-low[i])**2 for i in range(3)))*.5)
        width, height = editor.vm.draw.size.x, editor.vm.draw.size.y
        space = max(1, min(width,height)*.42)
        self.distance = radius*(height/space+(0 if isometric else 1))
        self.scale = max(1.0,.15/radius)
        self.culling = editor.backface_culling
        # Game.camera copies into its native camera, which may be editor.camera.
        # Keep a separate snapshot so every frame restores all camera fields.
        original = editor.camera
        self.saved_camera = Camera(position=original.position, direction=original.direction,
            plane=original.plane, height=original.height, distance=original.distance,
            perspective=original.perspective)
        self.camera = Camera(position=Vector(-max(.22,self.distance) if isometric
                                            else -self.distance*self.scale,0),
                             height=.5, perspective=CAMERA_THIRD_PERSON)

    def draw(self):
        editor = self.editor
        angle = -pi/4+self.phase*(2*pi/TURN_MS)
        basis = view_basis(angle,.6154797086703874 if self.isometric else .32)
        # Retain native storage between frames when the clipped count matches.
        old = self.buffer.mesh
        mesh = preview_mesh(self.records,self.center,basis,
            ortho_distance=self.distance if self.isometric else None,
            wireframe=0,perspective_scale=self.scale,culling=self.culling,
            camera_distance=self.distance,buffer=self.buffer)
        try:
            editor.entity.sprite_3d = mesh
            editor.game.camera = self.camera
            draw = editor.vm.draw
            draw.clear(color=BACKGROUND)
            editor.engine.run_async(False)
            draw.swap()
        finally:
            editor.entity.sprite_3d = editor.render_mesh
            editor.game.camera = self.saved_camera
            editor.game.camera = editor.camera
            if old is not None and old is not mesh:
                old.clear_triangles()

    def run(self, button):
        if button in (BUTTON_ESCAPE,BUTTON_BACK):
            return False
        if button == BUTTON_SPACE:
            self.paused = not self.paused
            self.last_ms = ticks_ms()
            return True
        if self.paused:
            return True
        now = ticks_ms()
        elapsed = ticks_diff(now,self.last_ms)
        if elapsed < FRAME_MS:
            return True
        self.phase = (self.phase+elapsed)%TURN_MS
        self.last_ms = now
        self.draw()
        return True

    def close(self):
        if self.buffer.mesh is not None:
            self.buffer.mesh.clear_triangles()
        self.buffer = MeshBuffer()
        # Camera wrappers release their native objects through GC finalisers.
        # They have already been detached from Game before reaching this point.
        self.camera = self.saved_camera = None
        self.records = self.editor = None


class ViewerTools:
    def begin_viewer(self, isometric=False):
        candidate = None
        try:
            candidate = Turntable(self,isometric)
            candidate.draw()
        except (ValueError,MemoryError,OSError,RuntimeError) as exc:
            if candidate is not None:
                candidate.close()
            self.dialog = ("Viewer unavailable",str(exc) or "Not enough memory")
            return
        self.viewer = candidate

    def end_viewer(self, redraw=True):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
        # The viewer overwrote the screen, but editor geometry/cameras are intact.
        self._scene_keys.clear()
        self._scene_layout = None
        self._hud_keys = [None,None,None]
        self._frame_drawn = False
        if redraw:
            self.draw_frame()

    def run_viewer(self):
        inputs = self.vm.input_manager
        button = inputs.button
        inputs.reset()
        try:
            if not self.viewer.run(button):
                self.end_viewer()
        except (ValueError,MemoryError,OSError,RuntimeError) as exc:
            self.end_viewer(False)
            self.dialog = ("Viewer stopped",str(exc) or "Not enough memory")
            self.draw_frame()
