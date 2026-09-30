"""Document state, editor input, transforms, and app lifecycle."""

from math import sqrt, floor, log10
from struct import unpack_from
from time import ticks_ms,ticks_diff
from picoware.system.vector import Vector
from .assets import load_sprite, record_bounds, save_sprite
from .viewport import ViewportMixin, PreviewInput, preview_mesh, view_basis
from .ui import EditorUI
from .history import History
from .transforms import TransformTools
from .selection import SelectionTools
from .editing import GeometryEditing
from .booleans import BooleanTools
from .normals import NormalTools
from .decimate import DecimateTools
from .colors import ColorTools
from .edges import EdgeTools
from .edge_selection import EdgeSelection
from .preferences import PreferenceTools

_app = None


class SpriteEditor(ViewportMixin, EditorUI, TransformTools, SelectionTools, GeometryEditing, BooleanTools, NormalTools, DecimateTools, ColorTools, EdgeTools, EdgeSelection, PreferenceTools):
    """Own the document, file selector, and editing tools."""

    def __init__(self, vm):
        self.vm = vm
        self._camera_pending = False
        self._camera_finished = 0
        self._frame_drawn = False
        self._drawn_status = None
        self._last_frame_ms = 0
        self._line_cache = {}
        self._normal_cache = None
        self._vertex_groups = None
        self._visibility_pending = {}
        self._visibility_worker = None
        self._interactive_visibility = False
        self.browser = None
        self.engine = None
        self.game = None
        self.level = None
        self.entity = None
        self.camera = None
        self.mesh = None
        self.render_mesh = None
        self.islands = None
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        self._edge_reps = None
        self.records = None
        self.view_name = "Orbit"
        self.four_view = False
        self.panes = []
        self.pane_zooms = [1.0]*4
        self.active_pane = 1
        self.four_angle = -0.7
        self.maximized = False
        self.path = ""
        self.error = ""
        self.directory = "/picoware/apps/games"
        self.menu = -1
        self.menu_row = 0
        self.submenu = False
        self.show_normals = False
        self.submenu_row = 0
        self.backface_culling = True
        self.show_edge_lengths = False
        self.xray_vertices = False
        self.show_grid = True
        self.show_orientation = True
        self.show_vertex_info = True
        self.shading = "Asset"
        self.dialog = None
        self.save_as = False
        self.pending_save = ""
        self.status = ""
        self.transform = None
        self.numeric = False
        self.history = History(vm.storage)
        self.steps = {"Move": 1.0, "Scale": .1, "Rotate": 5.0}
        self.snap = False
        self.pending_action = None
        self.selection_mode = "Model"
        self.selection = bytearray()
        self.selection_cursor = 0
        self.selection_camera = False
        self.linked_vertices = True
        self.paint_color = 0x7BEF
        self.color_rgb = False
        self.edit_prompt = None
        self.color_picker = None
        self.boolean_operands = [None,None]
        self.boolean_preview = None
        self.decimation_job = None
        self.boolean_job = None

        self.load_preferences()

    @property
    def dirty(self):
        return self.history.dirty

    def history_action(self, redo=False):
        try:
            label = self.history.travel(self.records, self.replace_records, redo)
            if label is not None:
                self.selection_mode_set("Model")
                self.status = ("Redid " if redo else "Undid ") + label
        except (MemoryError, OSError) as exc:
            self.dialog = ("Redo failed" if redo else "Undo failed", str(exc) or "Not enough memory")


    def browse(self):
        """Select an asset from SD storage."""
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

        self.browser = FileBrowser(self.vm, FILE_BROWSER_SELECTOR,
                                   self.directory, ["sprite3d"])


    def open(self, path):
        records = bytearray()
        mesh, low, high = load_sprite(self.vm.storage,path,records)
        self.install_document(mesh,records,low,high,path)

    def new_document(self):
        from picoware.engine.sprite3d import Sprite3D
        records = bytearray()
        mesh = Sprite3D()
        mesh.set_active(True)
        low,high = record_bounds(records)
        self.install_document(mesh,records,low,high,"")
        self.status = "Create a shape to start"

    def install_document(self, mesh, records, low, high, path):
        """Install a prepared document for both Open and New."""
        from picoware.engine.camera import Camera, CAMERA_THIRD_PERSON
        from picoware.engine.game import Game
        from picoware.engine.level import Level
        from picoware.engine.engine import GameEngine
        from picoware.engine.entity import Entity, ENTITY_TYPE_3D_SPRITE, SPRITE_3D_CUSTOM

        center = [(low[i] + high[i]) * 0.5 for i in range(3)]
        basis = view_basis(-0.7, 0.32)
        radius = max(1e-9, sqrt(sum((high[i]-low[i])**2 for i in range(3)))*.5)
        try:
            rendered = preview_mesh(records, center, basis, wireframe=self.shading_wireframe(),
                                    perspective_scale=max(1.0,.15/radius))
        except Exception:
            mesh.clear_triangles()
            raise
        if self.engine is None:
            self.camera = Camera(perspective=CAMERA_THIRD_PERSON)
            self.game = Game("Sprite3D Editor", self.vm.draw.size, self.vm.draw,
                             PreviewInput(), 0xFFFF, 0x1082, self.camera)
            self.level = Level("Preview", self.vm.draw.size, self.game)
            self.level.clear_allowed = False
            self.entity = Entity("Asset", ENTITY_TYPE_3D_SPRITE, Vector(0, 0),
                                 Vector(1, 1))
            self.level.entity_add(self.entity)
            self.game.level_add(self.level)
            self.engine = GameEngine(self.game, 30)
            self.game.level_switch(0)
        previous = self.mesh
        old_preview = self.render_mesh
        self.entity.sprite_3d = rendered
        self.entity.sprite_3d_type = SPRITE_3D_CUSTOM
        self.mesh = mesh
        self.render_mesh = rendered
        self.islands = None
        from .rendercache import clear
        clear(self)
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        self._edge_reps = None
        self.records = records
        self.basis = basis
        self._preview_angles = (-0.7, 0.32)
        if old_preview is not None:
            old_preview.clear_triangles()
        if previous is not None:
            previous.clear_triangles()
        self.center = center
        self.bounds = (low, high)
        self.radius = radius
        width, height = self.vm.draw.size.x, self.vm.draw.size.y
        space = max(10, min(width * 0.42, height * 0.5 - 64))
        self.fit_distance = self.radius * (1 + height / space)
        self.ground = low[1]
        unit = 10 ** floor(log10(self.radius / 3))
        self.grid_step = unit * (1 if self.radius / 3 <= unit else
                                 2 if self.radius / 3 <= unit * 2 else
                                 5 if self.radius / 3 <= unit * 5 else 10)
        self.path = path
        self.selection_mode_set("Model")
        self.history.reset()
        self.boolean_operands = [None,None]
        self.boolean_preview = None
        self.decimation_job = None
        self.boolean_job = None
        self.steps = {"Move": self.grid_step/10, "Scale": .1, "Rotate": 5.0}
        self.snap = False
        self.status = ""
        self.error = ""
        self.reset_camera()
        self.restore_document_preferences()


    def request_action(self, action, confirmed=False):
        if self.dirty and not confirmed:
            self.pending_action = action
            self.dialog = ("Discard unsaved changes?", "Save from File to keep your edits.")
        elif action == "open":
            self.browse()
        elif action == "new":
            try:
                self.new_document()
            except MemoryError:
                self.dialog = ("New failed","Not enough memory")
        else:
            self.vm.back()


    def replace_records(self, records):
        """Prepare canonical and view meshes before committing a geometry edit."""
        from picoware.engine.sprite3d import Sprite3D
        if len(records)%40 or len(records)//40 > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
            raise ValueError("Triangle limit exceeded")
        mesh = Sprite3D()
        rendered = None
        try:
            bounds = record_bounds(records)
            for offset in range(0, len(records), 40):
                mesh.add_triangle(*unpack_from("<9fHB", records, offset))
            if mesh.triangle_count != len(records)//40:
                raise MemoryError("Could not build transformed model")
            mesh.set_active(True)
            if self.four_view:
                self.set_four(force=True, records=records)
            else:
                rendered = preview_mesh(records, self.center, self.basis,
                                        ortho_distance=self.distance if self.is_ortho() else None,
                                        wireframe=self.shading_wireframe(),
                                        perspective_scale=self.perspective_scale(),
                                        culling=self.backface_culling, camera_distance=self.distance)
        except Exception:
            mesh.clear_triangles()
            if rendered is not None:
                rendered.clear_triangles()
            raise
        old, old_view = self.mesh, self.render_mesh
        self.islands = None
        from .rendercache import clear
        clear(self)
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        if self.selection_mode != "Edges" or len(records)!=len(self.records):
            self._edge_reps = None
        self.mesh, self.records = mesh, records
        self.bounds = bounds
        self._preview_angles = None
        if rendered is not None:
            self.render_mesh = rendered
            self.entity.sprite_3d = rendered
            self._preview_angles = (self.angle,self.pitch,self.distance,self.shading,
                                    self.perspective_scale(),self.backface_culling)
            old_view.clear_triangles()
        old.clear_triangles()


    def begin_save_as(self):
        """Ask for a destination path using the standard keyboard."""
        keyboard = self.vm.keyboard
        keyboard.reset()
        keyboard.title = "Save As (.sprite3d path)"
        keyboard.response = self.path[:-9]+"-copy.sprite3d" if self.path else "untitled.sprite3d"
        keyboard.run(force=True)
        keyboard.run(force=True)
        self.save_as = True


    def save(self, path):
        """Save the model and change the document path only after success."""
        try:
            if not self.records:
                raise ValueError("Create geometry before saving")
            save_sprite(self.vm.storage, self.mesh, path)
        except (OSError, ValueError, MemoryError) as exc:
            self.dialog = ("Save failed", str(exc) or "Not enough memory")
            return False
        self.path = path
        self.directory = path.rsplit("/", 1)[0] or "/"
        self.history.mark_saved()
        self.status = "Saved " + path.rsplit("/", 1)[-1]
        return True


    def activate_menu(self):
        """Run the selected dropdown action."""
        if self.menu_row < 0:
            self.menu_row = 0
            return
        if not self.menu_items()[self.menu_row][1]:
            return
        if not self.submenu and self.has_submenu():
            self.submenu_row = self.menu_row
            self.submenu = ("Camera", "Shading", "Overlays", "Selection")[self.menu_row] if self.menu == 1 else "Cleanup" if self.menu_row == 13 else True
            self.menu_row = 0
            return
        child = self.submenu
        self.submenu = False
        menu, row = self.menu, self.menu_row
        self.menu = -1
        self.status = ""
        if menu == 1 and child:
            row = {"Camera":(0,1,2,3,4,5,6), "Shading":(10,11,12,13,17),
                   "Overlays":(7,8,9,14,16), "Selection":(15,)}[child][row]
        if child and menu == 2:
            if child == "Cleanup":
                if row == 0:
                    self.clean_degenerates()
                else:
                    self.clean_duplicates()
            elif row < 3:
                self.begin_boolean(("Union","Difference","Intersection")[row])
            elif row < 5:
                self.capture_operand(row-3)
            else:
                self.clear_operands()
        elif menu == 0:
            if row == 0:
                self.request_action("open")
            elif row == 1:
                if self.path:
                    self.save(self.path)
                else:
                    self.begin_save_as()
            elif row == 2:
                self.begin_save_as()
            elif row == 3:
                self.request_action("quit")
            else:
                self.request_action("new")
        elif menu == 1:
            if row < 5:
                self.set_view(("Front", "Side", "Back", "Top", "Bottom")[row])
            elif row == 5:
                if self.maximized:
                    self.toggle_active_view()
                else:
                    self.set_four()
            elif row == 6:
                self.fit_view()
            elif row == 7:
                self.show_grid = not self.show_grid
            elif row == 8:
                self.show_orientation = not self.show_orientation
            elif row == 9:
                self.show_vertex_info = not self.show_vertex_info
            elif row == 14:
                self.show_normals = not self.show_normals
            elif row == 16:
                self.show_edge_lengths = not self.show_edge_lengths
            elif row == 17:
                self.toggle_culling()
            elif row == 15:
                self.xray_vertices = not self.xray_vertices
                self.ensure_visible_vertex()
            else:
                self.set_shading(("Asset","Solid","Wireframe","Solid + Wireframe")[row-10])
        elif menu == 2:
            if row in (3,4):
                self.history_action(redo=row == 4)
            elif row < 3:
                self.begin_transform(("Move", "Scale", "Rotate")[row])
            elif row == 5:
                self.begin_color_picker()
            elif row < 10:
                self.edit_geometry(("Duplicate","Delete","Wireframe","Flip winding")[row-6])
            elif row == 11:
                self.recalculate_normals()
            else:
                self.begin_edit_prompt("Decimate")
        elif menu == 3:
            if row == 3:
                try:
                    self.selection_mode_set("Edges")
                except MemoryError:
                    self.dialog = ("Selection failed","Not enough memory")
                return
            if row > 3:
                row -= 1
            if row < 3:
                self.selection_mode_set(("Model","Triangles","Vertices")[row])
            elif row < 6:
                self.selection_fill(("All","None","Invert")[row-3])
            elif row == 7:
                self.select_connected_solid()
            elif row == 8:
                try:
                    self.selection_mode_set("Islands")
                except MemoryError:
                    self.dialog = ("Selection failed","Not enough memory")
            else:
                self.linked_vertices = not self.linked_vertices
                if self.selection_mode == "Vertices":
                    self.selection_fill("None")
        elif menu == 4:
            if row == 0:
                self.request_action("new")
            else:
                from .creation import PRIMITIVES
                self.create_geometry((PRIMITIVES+("Face from vertices",))[row-1])
        elif row == 0:
            self.dialog = ("Controls", "Enter/Tab/F10: menus\nF/V/M/L/C/H: menus\nArrows: navigate menus\nEnter: select  Esc: close\nComponents: arrows pick P camera\nSpace Pick  , Prev . Next I Index\nA All N None  Del Delete\nArrows: orbit/zoom  R: fit\n1-4: active pane  F5: full\nZ Undo  Y Redo  W Shading\nG: Transform  O: Selection mode\nTools: E value T step S snap\n-/+: step size  Enter: Apply")
        else:
            self.dialog = ("Sprite3D Editor", "Sprite3D asset editor\nPico Game Engine\nOpen, Save and Save As\nGrid and XYZ orientation")


    def run(self):
        """Route input to the active dropdown, dialog, or preview."""
        from picoware.system.buttons import (
            BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT,
            BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN, BUTTON_R, BUTTON_TAB,
            BUTTON_F10, BUTTON_F5, BUTTON_F, BUTTON_V, BUTTON_M, BUTTON_L, BUTTON_C, BUTTON_H, BUTTON_Z, BUTTON_Y, BUTTON_W, BUTTON_G, BUTTON_O,
        )
        inputs = self.vm.input_manager
        self._interactive_visibility = True
        # Wait through the initial keyboard repeat gap before rebuilding
        # visibility and disposable overlays. New input always takes priority.
        if self._camera_pending and ticks_diff(ticks_ms(),self._camera_finished)>=350:
            self._camera_pending = False
            self._frame_drawn = False
        if self._visibility_pending and inputs.button < 0 and not self._camera_pending:
            from .visibilityjobs import poll
            poll(self)
        if (inputs.button < 0 and self._frame_drawn and self.status == self._drawn_status
                and not self.error and self.browser is None and not self.save_as
                and not self.numeric and self.edit_prompt is None
                and self.color_picker is None and self.boolean_job is None
                and self.decimation_job is None):
            return
        if self.color_picker is not None:
            self.run_color_picker(inputs)
            return
        if self.edit_prompt is not None:
            self.run_edit_prompt()
            return
        if self.boolean_job is not None:
            self.run_boolean_job(inputs)
            return
        if self.decimation_job is not None:
            self.run_decimation(inputs)
            return
        if self.boolean_preview is not None:
            self.run_boolean(inputs)
            return
        if self.transform is not None:
            self.run_transform(inputs)
            return
        if self.save_as:
            keyboard = self.vm.keyboard
            if keyboard.is_finished:
                path = keyboard.response.strip()
                keyboard.reset()
                self.save_as = False
                if path:
                    if not path.startswith("/"):
                        path = self.directory.rstrip("/") + "/" + path
                    if "." not in path.rsplit("/", 1)[-1]:
                        path += ".sprite3d"
                    if self.vm.storage.exists(path):
                        self.pending_save = path
                        self.dialog = ("Replace existing file?", path)
                    else:
                        self.save(path)
            elif not keyboard.run():
                keyboard.reset()
                self.save_as = False
            return
        if self.browser is not None:
            if self.browser.run():
                return
            selected = self.browser.mode == self.browser.MODE_SELECT
            path = self.browser.path
            self.directory = self.browser.directory
            self.browser = None
            inputs.reset()
            if selected:
                try:
                    self.open(path)
                except (ValueError, OSError, MemoryError) as exc:
                    self.dialog = ("Open failed", str(exc) or "Not enough memory")
        button = inputs.button
        inputs.reset()
        if self.error:
            self.dialog = ("Open failed", self.error)
            self.error = ""
        if self.dialog is not None:
            if button in (BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE):
                action = self.pending_action
                self.pending_action = None
                pending = self.pending_save
                self.dialog = None
                self.pending_save = ""
                if action and button == BUTTON_CENTER:
                    self.request_action(action, confirmed=True)
                if pending and button == BUTTON_CENTER:
                    self.save(pending)
            self.draw_frame()
            return
        if (self.menu < 0 or button == BUTTON_F5) and self.pane_control(button):
            self.menu = -1
            self.submenu = False
            self.draw_frame()
            return
        if self.menu < 0 and button == BUTTON_O:
            self.cycle_selection()
            self.draw_frame()
            return
        if self.menu < 0 and button == BUTTON_G:
            self.cycle_transform()
            self.draw_frame()
            return
        if self.menu < 0 and button == BUTTON_W:
            self.set_shading()
            self.draw_frame()
            return
        if self.menu < 0 and button in (BUTTON_Z, BUTTON_Y):
            self.history_action(redo=button == BUTTON_Y)
            self.draw_frame()
            return
        if self.menu < 0 and self.selection_control(button):
            if self.edit_prompt is None:
                self.draw_frame()
            return
        if button in (BUTTON_TAB, BUTTON_F10):
            self.submenu = False
            self.menu = 0 if self.menu < 0 else -1
            self.menu_row = -1
        elif button in (BUTTON_F, BUTTON_V, BUTTON_M, BUTTON_L, BUTTON_C, BUTTON_H):
            self.submenu = False
            self.menu = (BUTTON_F, BUTTON_V, BUTTON_M, BUTTON_L, BUTTON_C, BUTTON_H).index(button)
            self.menu_row = -1
        elif self.menu >= 0:
            if self.menu_row < 0:
                if button in (BUTTON_LEFT,BUTTON_RIGHT):
                    self.menu = (self.menu+(1 if button == BUTTON_RIGHT else -1))%6
                elif button in (BUTTON_DOWN,BUTTON_CENTER):
                    self.menu_row = 0
                elif button == BUTTON_UP:
                    self.menu_row = len(self.menu_items())-1
                elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                    self.menu = -1
            elif self.submenu and button in (BUTTON_BACK,BUTTON_ESCAPE,BUTTON_LEFT):
                self.submenu = False
                self.menu_row = self.submenu_row
            elif self.submenu and button == BUTTON_RIGHT:
                pass
            elif button in (BUTTON_BACK, BUTTON_ESCAPE):
                self.menu = -1
            elif button == BUTTON_RIGHT and self.has_submenu():
                self.activate_menu()
            elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                self.menu = (self.menu + (1 if button == BUTTON_RIGHT else -1)) % 6
                self.menu_row = -1
            elif button in (BUTTON_UP, BUTTON_DOWN):
                self.menu_row = (self.menu_row + (1 if button == BUTTON_DOWN else -1)) % len(self.menu_items())
            elif button == BUTTON_CENTER:
                self.activate_menu()
                if self.browser is not None or self.save_as or self.edit_prompt is not None or _app is None:
                    return
        elif button in (BUTTON_BACK, BUTTON_ESCAPE):
            self.request_action("quit")
            return
        elif button == BUTTON_CENTER:
            self.menu = 0
            self.submenu = False
            self.menu_row = -1
        elif self.mesh is not None and self.four_view:
            camera_before = (self.angle,tuple(self.pane_zooms))
            if button == BUTTON_LEFT and self.active_pane == 1:
                self.set_four(angle=self.angle - 0.12)
            elif button == BUTTON_RIGHT and self.active_pane == 1:
                self.set_four(angle=self.angle + 0.12)
            elif button == BUTTON_UP:
                self.set_four(zoom=self.four_zoom / 1.15)
            elif button == BUTTON_DOWN:
                self.set_four(zoom=self.four_zoom * 1.15)
            elif button == BUTTON_R:
                self.fit_view()
            if camera_before != (self.angle,tuple(self.pane_zooms)):
                self._camera_pending = True
                self._camera_finished = ticks_ms()
        elif self.mesh is not None:
            camera_before = (self.angle,self.pitch,self.distance)
            if button == BUTTON_LEFT and (not self.maximized or self.active_pane == 1):
                self.orient(self.angle - 0.12, 0.32, "Perspective" if self.maximized else "Orbit", self.distance)
            elif button == BUTTON_RIGHT and (not self.maximized or self.active_pane == 1):
                self.orient(self.angle + 0.12, 0.32, "Perspective" if self.maximized else "Orbit", self.distance)
            elif button == BUTTON_UP:
                minimum = self.fit_distance / 128 if self.is_ortho() else self.radius + .15/self.perspective_scale()
                self.distance = max(minimum, self.distance / 1.15)
            elif button == BUTTON_DOWN:
                self.distance = min(self.fitted_distance() * 8, self.distance * 1.15)
            elif button == BUTTON_R:
                self.fit_view()
            self.update_camera()
            if camera_before != (self.angle,self.pitch,self.distance):
                self._camera_pending = True
                self._camera_finished = ticks_ms()
        self.draw_frame()


    def close(self):
        """Stop the preview and release its resources."""
        self.persist_preferences(force=True)
        self.browser = None
        self.decimation_job = None
        self.boolean_job = None
        if self.save_as or self.numeric or self.edit_prompt is not None or (self.color_picker and self.color_picker["hex"]):
            self.vm.keyboard.reset()
        self.color_picker = None
        self.clear_four()
        if self.engine is not None:
            self.engine.stop()
        self.engine = None
        self.entity = None
        self.level = None
        self.game = None
        self.camera = None
        if self.mesh is not None:
            self.mesh.clear_triangles()
        self.mesh = None
        self.render_mesh = None
        self.islands = None
        from .rendercache import clear
        clear(self)
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        self._edge_reps = None
        self.records = None
        self.history.reset()
        self.transform = None


def start(view_manager):
    """Start the Sprite3D editor."""
    global _app
    _app = SpriteEditor(view_manager)
    return True


def run(_view_manager):
    """Run one editor frame."""
    if _app is not None:
        _app.run()
        if _app is not None:
            _app.persist_preferences()


def stop(_view_manager):
    """Close the editor."""
    from gc import collect
    global _app
    if _app is not None:
        _app.close()
        _app = None
    collect()
