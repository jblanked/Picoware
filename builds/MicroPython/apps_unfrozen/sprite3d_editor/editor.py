"""Document state, editor input, transforms, and app lifecycle."""

from math import sqrt, floor, log10
from time import ticks_ms,ticks_diff
from picoware.system.vector import Vector
from .ui import EditorUI
from .history import History
from .preferences import PreferenceTools
from .tools import LazyTools
from .meshes import MeshBuffer, prepare_mesh, apply_updates, discard_updates


def load_sprite(*args, **kwargs):
    from .assets import load_sprite as load
    return load(*args, **kwargs)


def record_bounds(*args, **kwargs):
    from .assets import record_bounds as bounds
    return bounds(*args, **kwargs)


def save_sprite(*args, **kwargs):
    from .assets import save_sprite as save
    return save(*args, **kwargs)


def preview_mesh(*args, **kwargs):
    from .viewport import preview_mesh as build
    return build(*args, **kwargs)

_app = None


class SpriteEditor(LazyTools, EditorUI, PreferenceTools):
    """Own the document, file selector, and editing tools."""

    def __init__(self, vm):
        from gc import collect
        collect()
        self._initialize(vm)

    def _initialize(self, vm):
        from .quads import Faces
        self.quads = Faces(b"")
        self.quad_job = None
        self.vm = vm
        self._closed = False
        self._framed_camera = None
        self._camera_pending = False
        self._quad_display_mode = False
        self._camera_job = None
        self._camera_requested = None
        self._defer_camera = False
        self._transform_pending = False
        self._transform_finished = 0
        self._geometry_revision = 0
        self._transform_hud = None
        self._camera_finished = 0
        self._frame_drawn = False
        self._pixels = None
        self._hud_keys = [None,None,None]
        self._frame_info = None
        self._scene_keys = {}
        self._scene_stamps = {}
        self._selection_blank = {}
        self._visibility_geometry = None
        self._selection_recover = False
        self._scene_layout = None
        self._scene_popup = None
        self._overlay_pending = {}
        self._overlay_worker = None
        self._drawn_status = None
        self._last_frame_ms = 0
        self._line_cache = {}
        self._normal_cache = None
        self._vertex_groups = None
        self._wire_topology = None
        self._wire_scratch = None
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
        self._model_buffer = MeshBuffer()
        self._preview_buffer = MeshBuffer()
        self._pane_buffers = []
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
        self.four_pitch = .32
        self._pane_centers = None
        self.maximized = False
        self.path = ""
        self.path_saved = False
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
        self.pivot_edit = None
        self.custom_pivot = None
        self._pivot_hud = None
        self.viewer = None
        self.numeric = False
        self.isolation = None
        self.model_tool = None
        self.pane_targets = [None]*4
        self.pane_radii = [None]*4
        self.history = History(vm.storage)
        self.history.replace_context = self.history_replace
        self.history.metadata_records = self.history_metadata_records
        from .quads import history_encode
        self.history.encode_document = lambda: history_encode(self)
        self.steps = {"Move": 1.0, "Scale": .1, "Rotate": 5.0}
        self.snap = False
        self.pending_action = None
        self.unsaved_choice = None
        self.save_action = None
        self.selection_mode = "Model"
        self.selection = bytearray()
        self.selection_cursor = 0
        self.selection_camera = False
        self.mode_chooser = None
        self.chooser_tools = False
        self.linked_vertices = True
        self.paint_color = 0x7BEF
        self.color_rgb = False
        self.edit_prompt = None
        self.color_picker = None
        self.boolean_workflow = None
        self.boolean_operands = [None,None]
        self.boolean_preview = None
        self.decimation_job = None
        self.boolean_job = None

        self.settings_state = None
        self.move_on_create = True
        self.move_on_duplicate = True
        self.auto_fit_creation = True
        self.move_step_mode = "Automatic"
        self.orbit_speed = "Normal"
        self.zoom_speed = "Normal"
        self.load_preferences()

    @property
    def four_zoom(self):
        """Zoom of the highlighted pane; other panes retain their own values."""
        return self.pane_zooms[self.active_pane]

    @four_zoom.setter
    def four_zoom(self, value):
        self.pane_zooms[self.active_pane] = value

    @property
    def dirty(self):
        return self.history.dirty

    def history_action(self, redo=False):
        try:
            label = self.history.travel(self.records, self.replace_records, redo)
            if label is not None:
                self.status = ("Redid " if redo else "Undid ") + label
        except (MemoryError, OSError, ValueError) as exc:
            self.dialog = ("Redo failed" if redo else "Undo failed", str(exc) or "Not enough memory")


    def browse(self):
        """Select an asset from SD storage."""
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

        self.browser = FileBrowser(self.vm, FILE_BROWSER_SELECTOR,
                                   self.directory, ["sprite3d"])


    def prepare_document_memory(self):
        """Drop disposable caches while retaining the document and native views."""
        from gc import collect,mem_free
        if mem_free()<262144:
            from .rendercache import clear
            clear(self,geometry_only=True)
            self.vertex_visibility_cache.clear();self.edge_label_cache.clear()
            collect()


    def open(self, path, cooperative=False):
        self.prepare_document_memory()
        from .quadfile import recover,load_steps
        recover(self.vm.storage,path)
        records=bytearray();mesh,low,high=load_sprite(self.vm.storage,path,records)
        pivot_out=[]
        worker=load_steps(self.vm.storage,path,records,prepared=True,pivot_out=pivot_out)
        if cooperative:
            self.quad_job=(worker,mesh,records,low,high,path,pivot_out)
            self.status='Preparing logical faces... Esc cancels';self._frame_drawn=False
            return
        try:
            try:
                while True:next(worker)
            except StopIteration as done:pairs,message=done.value
            self.install_document(mesh,records,low,high,path,pairs,pivot_out[0])
            if message:self.status=message
        except Exception:
            if self.mesh is not mesh:mesh.clear_triangles()
            raise
        finally:worker.close()

    def run_quad_job(self,inputs):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_ESCAPE
        worker,mesh,records,low,high,path,pivot_out=self.quad_job
        button=inputs.button;inputs.reset()
        if button in (BUTTON_BACK,BUTTON_ESCAPE):
            worker.close();mesh.clear_triangles();self.quad_job=None
            self.status='Open cancelled';self.draw_frame();return
        started=ticks_ms()
        try:
            while ticks_diff(ticks_ms(),started)<8:next(worker)
        except StopIteration as done:
            self.quad_job=None
            pairs,message=done.value
            try:
                self.install_document(mesh,records,low,high,path,pairs,pivot_out[0])
                if message:self.status=message
            except (ValueError,OSError,MemoryError) as exc:
                mesh.clear_triangles();self.dialog=('Open failed',str(exc) or 'Not enough memory')
        except (ValueError,OSError,MemoryError) as exc:
            worker.close();mesh.clear_triangles();self.quad_job=None
            self.dialog=('Open failed',str(exc) or 'Not enough memory')
        if self.quad_job is None or not self._frame_drawn or ticks_diff(ticks_ms(),self._last_frame_ms)>=100:self.draw_frame()

    def new_document(self, path=""):
        from picoware.engine.sprite3d import Sprite3D
        records = bytearray()
        mesh = Sprite3D()
        mesh.set_active(True)
        low,high = record_bounds(records)
        self.install_document(mesh,records,low,high,path)
        self.path_saved = False
        self.status = "Create a shape to start"

    def install_document(self, mesh, records, low, high, path, quads=None, custom_pivot=None):
        """Install a prepared document for both Open and New."""
        self.prepare_document_memory()
        from .camera import cancel
        cancel(self)
        from .viewport import view_basis, PreviewInput
        from picoware.engine.camera import Camera, CAMERA_THIRD_PERSON
        from picoware.engine.game import Game
        from picoware.engine.level import Level
        from picoware.engine.engine import GameEngine
        from picoware.engine.entity import Entity, ENTITY_TYPE_3D_SPRITE, SPRITE_3D_CUSTOM

        from .quads import Faces
        quad_state=quads if isinstance(quads,Faces) else Faces(records,quads or ())
        center = [(low[i] + high[i]) * 0.5 for i in range(3)]
        basis = view_basis(-0.7, 0.32)
        radius = max(1e-9, sqrt(sum((high[i]-low[i])**2 for i in range(3)))*.5)
        width,height=self.vm.draw.size.x,self.vm.draw.size.y
        space=max(10,min(width*.42,height*.5-64))
        fit_distance=radius*(1+height/space)
        scale=max(1.0,.15/radius)
        distance=max(radius+.15/scale,fit_distance)
        model_buffer = MeshBuffer(mesh, records)
        preview_buffer = MeshBuffer()
        try:
            try:
                rendered = preview_mesh(records, center, basis, wireframe=self.shading_wireframe(),
                                        perspective_scale=scale,buffer=preview_buffer,
                                        culling=self.backface_culling,camera_distance=distance)
            except MemoryError:
                from .viewport import initial_preview_mesh
                rendered=initial_preview_mesh(records,center,basis,self.shading_wireframe(),
                                              scale,preview_buffer,self.backface_culling,distance)
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
        if self.quad_job is not None:
            self.quad_job[0].close();self.quad_job[1].clear_triangles();self.quad_job=None
        previous = self.mesh
        old_preview = self.render_mesh
        self.entity.sprite_3d = rendered
        self.entity.sprite_3d_type = SPRITE_3D_CUSTOM
        self.mesh = mesh
        self.mode_chooser = None
        self.chooser_tools = False
        self._model_buffer = model_buffer
        self._preview_buffer = preview_buffer
        self.render_mesh = rendered
        self.islands = None
        from .rendercache import clear
        clear(self)
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        self._edge_reps = None
        self.records = records
        self.quads = quad_state
        self._quad_display_mode = self.selection_mode=="Quads"
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
        self.path_saved = bool(path)
        self.custom_pivot = tuple(custom_pivot) if custom_pivot is not None else None
        self.pivot_edit = None
        self._pivot_hud = None
        # The new document has no fitted camera yet. Reset selection without
        # rendering the transition; reset_camera below builds its first view.
        self.selection_mode_set("Model", refresh=False)
        if self.boolean_workflow is not None or self.boolean_job is not None:
            self.end_boolean_workflow(restore=False)
        self.isolation = None
        self.pane_targets = [None]*4
        self.pane_radii = [None]*4
        if self.model_tool is not None:self.end_model_tool(False)
        self.history.reset()
        self.boolean_operands = [None,None]
        self.boolean_preview = None
        self.decimation_job = None
        self.boolean_job = None
        self.status = ""
        self.error = ""
        self.reset_camera()
        self.restore_document_preferences()


    def request_action(self, action, confirmed=False):
        if self.dirty and not confirmed:
            self.pending_action = action
            self.unsaved_choice = 0
            self.update_unsaved_dialog()
        elif action == "open":
            self.browse()
        elif action == "new":
            try:
                self.begin_name("New")
            except MemoryError:
                self.dialog = ("New failed","Not enough memory")
        else:
            self.vm.back()


    def update_unsaved_dialog(self):
        choices = ("Save", "Discard", "Cancel")
        self.dialog = ("Save unsaved changes?", "\n".join(
            ("> " if i == self.unsaved_choice else "  ")+label
            for i,label in enumerate(choices)))

    def save_and_continue(self, path, confirmed=False):
        """Consume the deferred action even on failure; only success may continue."""
        try:
            if not confirmed and not self.path_saved and path==self.path and self.vm.storage.exists(path):
                self.pending_save = path
                self.dialog = ("Replace existing file?",path)
                return
        except (OSError,MemoryError) as exc:
            self.save_action = None
            self.dialog = ("Save failed",str(exc) or "Not enough memory")
            return
        action = self.save_action
        self.save_action = None
        if self.save(path) and action is not None:
            self.request_action(action, confirmed=True)

    def replace_records(self, records, preview=False, bounds=None, prepared=None, quads=None, metadata_only=False):
        """Prepare all views before updating any existing native triangles."""
        from .camera import cancel
        cancel(self)
        if prepared is not None:
            prepared.commit(self);return
        from .quads import Faces,unchanged
        quad_state = quads if isinstance(quads,Faces) else Faces(records,unchanged(self.records,records,self.quads.pairs) if quads is None else quads)
        if metadata_only and records==self.records and self._quad_display_mode==(self.selection_mode=='Quads'):
            from .rendercache import clear
            clear(self);self.quads=quad_state;self._frame_drawn=False
            return
        from picoware.engine.sprite3d import Sprite3D
        if len(records)%40 or len(records)//40 > self.document_capacity():
            raise ValueError("Triangle limit exceeded")
        from .rendercache import clear
        # Discard derived caches before the transaction; a failed edit may
        # rebuild them, but must not fail an allocation after native commit.
        clear(self,geometry_only=preview)
        preview_angles = (self.angle,self.pitch,self.distance,self.shading,
                          self.perspective_scale(),self.backface_culling)
        vertex_visibility_cache, edge_label_cache = {}, {}
        updates = []
        mesh = self.mesh
        rendered = None
        try:
            if bounds is None:
                bounds = record_bounds(records)
            if not preview:
                mesh = prepare_mesh(self._model_buffer, records, updates)
            if mesh.triangle_count != len(records)//40:
                raise MemoryError("Could not build transformed model")
            if self.four_view:
                self.set_four(force=True, records=records, updates=updates)
            else:
                if self.shading != 'Wireframe':
                    rendered = preview_mesh(records, self.center, self.basis,
                        ortho_distance=self.distance if self.is_ortho() else None,
                        wireframe=self.shading_wireframe(),
                        perspective_scale=self.perspective_scale(),
                        culling=self.backface_culling, camera_distance=self.distance,
                        buffer=self._preview_buffer, updates=updates)
                apply_updates(updates)
        except Exception:
            discard_updates(updates)
            raise
        old, old_view = self.mesh, self.render_mesh
        self.islands = None
        self.vertex_visibility_cache = vertex_visibility_cache
        self.edge_label_cache = edge_label_cache
        if self.selection_mode != "Edges" or len(records)!=len(self.records):
            self._edge_reps = None
        self.mesh, self.records = mesh, records
        self.quads = quad_state
        self._quad_display_mode = self.selection_mode=="Quads"
        self.bounds = bounds
        self._preview_angles = None
        if rendered is not None:
            self.render_mesh = rendered
            self.entity.sprite_3d = rendered
            self._preview_angles = preview_angles
            if old_view is not rendered:
                old_view.clear_triangles()
        if old is not mesh:
            old.clear_triangles()


    def begin_save_as(self):
        """Ask for a basename in the current editor folder."""
        self.begin_name("Save As")


    def save(self, path):
        """Save the model and change the document path only after success."""
        try:
            if not self.records and not (self.isolation and self.isolation["hidden"][1]):
                raise ValueError("Create geometry before saving")
            from .quadfile import save as save_pair
            if self.isolation is None:
                warning=save_pair(self.vm.storage,self.mesh,path,self.records,self.quads.pairs,self.custom_pivot)
            else:
                from .workspace import full_records,full_pairs
                buffer=MeshBuffer()
                complete=full_records(self,self.records,self.isolation)
                temporary=prepare_mesh(buffer,complete)
                try:warning=save_pair(self.vm.storage,temporary,path,complete,full_pairs(self.records,self.quads.pairs,self.isolation),self.custom_pivot)
                finally:temporary.clear_triangles()
        except (OSError, ValueError, MemoryError) as exc:
            self.dialog = ("Save failed", str(exc) or "Not enough memory")
            return False
        self.path = path
        self.directory = path.rsplit("/", 1)[0] or "/"
        self.path_saved = True
        self.history.mark_saved()
        self.status = warning or "Saved " + path.rsplit("/", 1)[-1]
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
            self.submenu = ("Camera", "Shading", "Overlays", "Selection")[self.menu_row] if self.menu == 1 else "Cleanup" if self.menu_row == 15 else "Mesh tools" if self.menu_row == 16 else True
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
            if child == "Mesh tools":
                from .modelops import TOOLS
                self.begin_model_tool(TOOLS[row])
            elif child == "Cleanup":
                if row == 0:
                    self.clean_degenerates()
                else:
                    self.clean_duplicates()
        elif menu == 0:
            if row == 0:
                self.request_action("new")
            elif row == 1:
                self.request_action("open")
            elif row == 2:
                if self.path:
                    self.save_and_continue(self.path)
                else:
                    self.begin_save_as()
            elif row == 3:
                self.begin_save_as()
            elif row == 4:
                self.begin_settings()
            elif row == 5:
                self.request_action("quit")
        elif menu == 1:
            if not child and row in (4,5):
                self.begin_viewer(isometric=row==5)
            elif row < 5:
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
            if row in (5,6):
                self.history_action(redo=row == 6)
            elif row < 3:
                self.begin_transform(("Move", "Scale", "Rotate")[row])
            elif row == 3:
                try:self.center_object()
                except (ValueError,OSError,MemoryError) as exc:self.dialog=('Center failed',str(exc) or 'Not enough memory')
            elif row == 4:
                self.begin_pivot_edit()
            elif row == 7:
                self.begin_color_picker()
            elif row < 12:
                self.edit_geometry(("Duplicate","Delete","Wireframe","Flip winding")[row-8])
            elif row == 12:
                self.begin_boolean_workflow()
            elif row == 13:
                self.recalculate_normals()
            elif row == 14:
                self.begin_edit_prompt("Decimate")
        elif menu == 3:
            from .modes import MODES
            if row<len(MODES):
                try:self.selection_mode_set(MODES[row])
                except (ValueError,OSError,MemoryError) as exc:self.dialog=('Selection failed',str(exc) or 'Not enough memory')
            elif row<len(MODES)+3:self.selection_fill(('All','None','Invert')[row-len(MODES)])
            elif row==len(MODES)+3:self.linked_vertices=not self.linked_vertices
            else:self.select_connected_solid()
        elif menu == 4:
            if row == 0:
                self.request_action("new")
            else:
                from .creation import PRIMITIVES
                self.create_geometry((PRIMITIVES+("Face from vertices",))[row-1])
        elif row == 0:
            self.dialog = ("Controls", "Tab: Camera/Edit (P alias)\nTool camera: Esc Edit, then cancel\nO: Modes (including Quads) G: Transform\nF10 or F/V/M/L/H: menus\nE: Mesh tools (Edit), Create (Camera)\nEnter: select  Esc/Back: cancel\nSpace Pick  , Prev . Next I Index\nA All N None  Del Delete\nArrows: orbit/pan  +/-: zoom  R: fit\n1-4: pane  F3: selection zoom\nF4: isolate  F5: full\nZ Undo  Y Redo  W Shading\nQuads: E tools > Join / Split\nIslands: B Boolean  File > Quit\nTools: E value T step S snap\n-/+: step size  Enter: Apply")
        elif row == 2:
            self.dialog = ("Model viewers", "View > Model viewer\nView > Isometric viewer\nSpace: pause/resume rotation\nEsc/Back: return to editor\nOne full turn every 20 seconds")
        else:
            self.dialog = ("Sprite3D Editor", "Sprite3D asset editor\nPico Game Engine\nOpen, Save and Save As\nGrid and XYZ orientation")


    def run(self):
        """Route input to the active dropdown, dialog, or preview."""
        if self._closed:
            return
        if self.viewer is not None:
            self.run_viewer()
            return
        from picoware.system.buttons import (
            BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT,
            BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN, BUTTON_R, BUTTON_TAB,
            BUTTON_F10, BUTTON_F5, BUTTON_F, BUTTON_V, BUTTON_M, BUTTON_L, BUTTON_C, BUTTON_B, BUTTON_E, BUTTON_H, BUTTON_Z, BUTTON_Y, BUTTON_W, BUTTON_G, BUTTON_O,
        )
        inputs = self.vm.input_manager
        if self.quad_job is not None:
            self.run_quad_job(inputs)
            return
        if self.settings_state is not None:
            self.run_settings(inputs)
            return
        self._interactive_visibility = True
        if self._camera_job is not None or self._camera_requested is not None:
            from .camera import poll, cancel, navigation_key
            if inputs.button<0:
                poll(self)
                if self._camera_job is None:self.draw_frame()
                return
            if not navigation_key(inputs.button):cancel(self)
        # Wait through the initial held-key repeat gap before starting work
        # that the next camera input would invalidate.
        if self._camera_pending and ticks_diff(ticks_ms(),self._camera_finished)>=350:
            self._camera_pending = False
            self._frame_drawn = False
        if self._transform_pending and ticks_diff(ticks_ms(),self._transform_finished)>=350:
            self._transform_pending = False
            self._frame_drawn = False
        if self._visibility_pending and inputs.button < 0 and not (self._camera_pending or self._transform_pending):
            from .visibilityjobs import poll
            poll(self)
        elif self._overlay_pending and inputs.button < 0 and not (self._camera_pending or self._transform_pending):
            from .overlayjobs import poll
            poll(self)
        if (inputs.button < 0 and self._frame_drawn and self.status == self._drawn_status
                and not self.error and self.browser is None and not self.save_as
                and not self.numeric and self.edit_prompt is None
                and self.color_picker is None and self.boolean_job is None
                and self.decimation_job is None and (self.model_tool is None or (self.model_tool["worker"] is None and not self.model_tool["numeric"]))):
            return
        if self.color_picker is not None:
            self._scene_keys.clear()
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
        if self.boolean_workflow is not None:
            self.run_boolean_workflow(inputs)
            return
        if self.pivot_edit is not None:
            self.run_pivot_edit(inputs)
            return
        if self.model_tool is not None:
            self.run_model_tool(inputs)
            return
        if self.transform is not None:
            self.run_transform(inputs)
            return
        if self.save_as:
            self.run_name(inputs)
            return
        if self.browser is not None:
            self._scene_keys.clear()
            if self.browser.run():
                return
            selected = self.browser.mode == self.browser.MODE_SELECT
            path = self.browser.path
            self.directory = self.browser.directory
            self.browser = None
            inputs.reset()
            if selected:
                try:
                    self.open(path,cooperative=True)
                    return
                except (ValueError, OSError, MemoryError) as exc:
                    self.dialog = ("Open failed", str(exc) or "Not enough memory")
        if self.mode_chooser is not None and self.dialog is None:
            from .modes import run_chooser
            run_chooser(self,inputs)
            return
        button = inputs.button
        inputs.reset()
        if self.error:
            self.dialog = ("Open failed", self.error)
            self.error = ""
        if self.dialog is not None:
            if self.unsaved_choice is not None:
                if button in (BUTTON_UP, BUTTON_LEFT, BUTTON_DOWN, BUTTON_RIGHT):
                    self.unsaved_choice = (self.unsaved_choice+(
                        -1 if button in (BUTTON_UP,BUTTON_LEFT) else 1))%3
                    self.update_unsaved_dialog()
                elif button in (BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE):
                    choice = self.unsaved_choice if button == BUTTON_CENTER else 2
                    action = self.pending_action
                    self.pending_action = None
                    self.unsaved_choice = None
                    self.dialog = None
                    if choice == 1:
                        self.request_action(action, confirmed=True)
                    elif choice == 0:
                        self.save_action = action
                        if self.path:
                            self.save_and_continue(self.path)
                        else:
                            try:
                                self.begin_save_as()
                            except (OSError,ValueError,MemoryError) as exc:
                                self.save_action = None
                                self.dialog = ("Save failed",str(exc) or "Not enough memory")
                            else:
                                return
            elif button in (BUTTON_CENTER, BUTTON_BACK, BUTTON_ESCAPE):
                pending = self.pending_save
                self.dialog = None
                self.pending_save = ""
                if pending and button == BUTTON_CENTER:
                    self.save_and_continue(pending, confirmed=True)
                else:
                    self.save_action = None
            self.draw_frame()
            return
        if button < 0:
            self.draw_frame()
            return
        if self.mesh is not None and (self.menu < 0 or button == BUTTON_F5) and self.pane_control(button):
            self.menu = -1
            self.submenu = False
            self.draw_frame()
            return
        if button == BUTTON_B and self.selection_mode == 'Islands':
            self.begin_boolean_workflow()
            self.draw_frame()
            return
        if button == BUTTON_C:
            self.menu = -1
            self.submenu = False
            self.begin_color_picker()
            self.draw_frame()
            return
        if button == BUTTON_E and self.mesh is not None and self.selection_mode != 'Model' and not self.selection_camera:
            from .modes import begin_chooser
            begin_chooser(self,tools=True)
            self.draw_frame()
            return
        if self.menu < 0 and button == BUTTON_O:
            from .modes import begin_chooser
            begin_chooser(self)
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
            if self.selection_camera:
                self.status="Tab to edit"
                self.draw_frame()
                return
            self.history_action(redo=button == BUTTON_Y)
            self.draw_frame()
            return
        if self.mesh is not None and self.menu < 0 and self.selection_control(button):
            if self.edit_prompt is None:
                self.draw_frame()
            return
        if self.menu < 0:
            from .modes import control
            if control(self,button):self.draw_frame();return
        if button == BUTTON_TAB:
            return
        if button == BUTTON_F10:
            self.submenu = False
            self.menu = 0 if self.menu < 0 else -1
            self.menu_row = -1
        elif button in (BUTTON_F, BUTTON_V, BUTTON_M, BUTTON_L, BUTTON_E, BUTTON_H):
            self.submenu = False
            self.menu = {BUTTON_F:0, BUTTON_V:1, BUTTON_M:2, BUTTON_L:3, BUTTON_E:4, BUTTON_H:5}[button]
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
            # Back belongs to the active editor layer, never to app exit.
            return
        elif button == BUTTON_CENTER:
            self.menu = 0
            self.submenu = False
            self.menu_row = -1
        elif self.mesh is not None:
            self.boolean_camera(button)
        self.draw_frame()


    def close(self):
        """Stop the preview and release its resources."""
        from .camera import cancel
        cancel(self)
        if self.quad_job is not None:
            self.quad_job[0].close();self.quad_job[1].clear_triangles();self.quad_job=None
        self.quads=None
        self._closed = True
        if self.model_tool is not None:self.end_model_tool(False)
        if self.pivot_edit is not None:self.end_pivot_edit(False)
        if self.settings_state is not None:
            if self.settings_state["numeric"] is not None:
                self.vm.keyboard.reset()
            self.settings_state = None
        self.persist_preferences(force=True)
        if self.viewer is not None:
            self.end_viewer(False)
        self.browser = None
        if self.boolean_workflow is not None or self.boolean_job is not None:
            self.end_boolean_workflow(restore=False)
        self.decimation_job = None
        self.boolean_job = None
        if self.save_as or self.numeric or self.edit_prompt is not None or (self.color_picker and self.color_picker["hex"]):
            self.vm.keyboard.reset()
        self.color_picker = None
        if self.panes:
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
        self.mode_chooser = None
        self.chooser_tools = False
        self.render_mesh = None
        self._model_buffer = MeshBuffer()
        self._preview_buffer = MeshBuffer()
        self._pane_buffers = []
        self.islands = None
        from .rendercache import clear
        clear(self)
        self.vertex_visibility_cache = {}
        self.edge_label_cache = {}
        self._edge_reps = None
        self.records = None
        self.history.reset()
        self.transform = None
        if self._pixels is not None:
            self._pixels.close()
            self._pixels = None


def start(view_manager):
    """Start the Sprite3D editor."""
    global _app
    _app = SpriteEditor(view_manager)
    return True


def run(_view_manager):
    """Run one editor frame."""
    if _app is not None:
        # Input and modal work can change settings; idle frames only flush an
        # already pending snapshot after its debounce expires.
        check = (_view_manager.input_manager.button >= 0 or _app.browser is not None
                 or _app.numeric or _app.edit_prompt is not None or _app.save_as
                 or _app.color_picker is not None or _app.boolean_job is not None
                 or _app.decimation_job is not None or _app.settings_state is not None)
        _app.run()
        if _app is not None:
            _app.persist_preferences(check=check)


def stop(_view_manager):
    """Close the editor."""
    from gc import collect
    global _app
    if _app is not None:
        _app.close()
        _app = None
    collect()
