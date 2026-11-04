"""Validated SD preferences with debounced, recoverable replacement."""
import json
from math import isfinite
from time import ticks_ms,ticks_diff

PATH = '/picoware/settings/sprite3d_editor.json'
FLAGS = ('backface_culling','show_grid','show_orientation','show_vertex_info','show_normals',
         'show_edge_lengths','xray_vertices','linked_vertices','selection_camera','snap','color_rgb',
         'move_on_create','move_on_duplicate','auto_fit_creation')
CHOICES = (('move_step_mode',('Automatic','Custom')),
           ('orbit_speed',('Slow','Normal','Fast')),('zoom_speed',('Slow','Normal','Fast')))
EXTRA = tuple(name for name,_ in CHOICES)
VIEWS = ('Orbit','Perspective','Front','Side','Back','Top','Bottom','4 View')
from .modes import MODES


def check_step(kind, value):
    maximum = {"Move": 1e12, "Scale": 1e6, "Rotate": 360}[kind]
    if not isfinite(value) or not 1e-9 <= value <= maximum:
        raise ValueError("Step must be 1e-9 to %g" % maximum)


def validated(data):
    if not isinstance(data,dict) or data.get('version')!=1:
        raise ValueError('Invalid editor preferences')
    result = {'version':1}
    for name in FLAGS:
        if type(data.get(name)) is bool:
            result[name] = data[name]
    for name,choices in (('shading',('Asset','Solid','Wireframe','Solid + Wireframe')),('selection_mode',MODES))+CHOICES:
        if data.get(name) in choices:
            result[name] = data[name]
    color = data.get('paint_color')
    if type(color) is int and 0<=color<=65535:
        result['paint_color'] = color
    directory = data.get('directory')
    if isinstance(directory,str) and directory.startswith('/') and len(directory)<=256:
        result['directory'] = directory
    steps = data.get('steps',{})
    if isinstance(steps,dict):
        good = {}
        for kind in ('Move','Scale','Rotate'):
            value = steps.get(kind)
            if type(value) in (int,float):
                try:
                    check_step(kind,value)
                    good[kind] = value
                except ValueError:
                    pass
        result['steps'] = good
    if 'move_step_mode' not in result:
        result['move_step_mode'] = 'Custom' if 'Move' in result.get('steps',{}) else 'Automatic'
    view = data.get('view',{})
    if isinstance(view,dict) and view.get('name') in VIEWS:
        good = {'name':view['name']}
        for name,low,high in (('angle',-1e6,1e6),('pitch',-1.571,1.571),('four_angle',-1e6,1e6),('zoom',1/128,8)):
            value = view.get(name)
            if type(value) in (int,float) and isfinite(value) and low<=value<=high:
                good[name] = value
        zooms = view.get('pane_zooms')
        if isinstance(zooms,list) and len(zooms)==4 and all(
                type(z) in (int,float) and isfinite(z) and 1/128<=z<=8 for z in zooms):
            good['pane_zooms'] = list(zooms)
        if type(view.get('active')) is int and 0<=view['active']<4:
            good['active'] = view['active']
        if type(view.get('maximized')) is bool:
            good['maximized'] = view['maximized']
        result['view'] = good
    return result


def preference_bytes(storage,path):
    size=storage.size(path)
    if not 0<size<=8192:
        raise ValueError('Invalid preferences size')
    # Native positional reads allocate the requested count, even past EOF.
    # An empty/short read must not masquerade as corrupt JSON.
    data=storage.read_chunked(path,0,size)
    if len(data)!=size:raise OSError('Incomplete settings read: %d of %d bytes'%(len(data),size))
    return data


def read_preferences(storage,path):
    return validated(json.loads(preference_bytes(storage,path)))


def write_preferences(storage,data):
    for directory in ('/picoware','/picoware/settings'):
        if not storage.exists(directory) and not storage.mkdir(directory):
            raise OSError('Cannot create settings directory')
    # Recreating a long .json.tmp name after rename fails on some Pico SD
    # drivers. Keep staging within 8.3 while retaining the existing backup.
    temporary,backup = PATH.rsplit('/',1)[0]+'/s3prefs.tmp',PATH+'.bak'
    if storage.exists(temporary) and not storage.remove(temporary):
        raise OSError('Cannot clear temporary preferences')
    encoded = json.dumps(data).encode()
    if not storage.write(temporary,encoded,'wb'):
        raise OSError('Could not write temporary preferences')
    if preference_bytes(storage,temporary)!=encoded:
        raise OSError('Settings verification mismatch')
    # Recover a previous interrupted replacement before preparing another one.
    if storage.exists(backup):
        try:
            read_preferences(storage,PATH)
        except (ValueError,OSError):
            if storage.exists(PATH):
                storage.remove(PATH)
            if not storage.rename(backup,PATH):
                raise OSError('Cannot recover preferences')
        else:
            if not storage.remove(backup):
                raise OSError('Cannot replace preferences backup')
    moved = storage.exists(PATH)
    if moved and not storage.rename(PATH,backup):
        raise OSError('Cannot back up preferences')
    if not storage.rename(temporary,PATH):
        if moved:
            storage.rename(backup,PATH)
        raise OSError('Cannot install preferences')
    if moved:
        storage.remove(backup)


class PreferenceTools:
    def orbit_increment(self):
        return (.06,.12,.24)[('Slow','Normal','Fast').index(self.orbit_speed)]

    def zoom_factor(self):
        return (1.075,1.15,1.30)[('Slow','Normal','Fast').index(self.zoom_speed)]

    def load_preferences(self):
        self._prefs_saved = None
        self._prefs_error = None
        self._prefs_pending = None
        self._prefs_since = ticks_ms()
        self._startup_preferences = None
        loaded_primary = False
        for path in (PATH,PATH+'.bak'):
            try:
                if not self.vm.storage.exists(path):
                    continue
                data = read_preferences(self.vm.storage,path)
                for name in FLAGS+EXTRA+('shading','paint_color','directory','selection_mode'):
                    if name in data:
                        setattr(self,name,data[name])
                self.steps.update(data.get('steps',{}))
                self._startup_preferences = data
                loaded_primary = path == PATH
                break
            except (ValueError,OSError,MemoryError):
                continue
        snapshot = self.preference_snapshot()
        if loaded_primary and snapshot == self._startup_preferences:
            self._prefs_saved = snapshot
        else:
            # Missing/incomplete settings and backup recovery still get repaired.
            self._prefs_pending = snapshot

    def preference_snapshot(self):
        data = {'version':1,'steps':dict(self.steps)}
        for name in FLAGS+EXTRA+('shading','paint_color','directory','selection_mode'):
            data[name] = getattr(self,name)
        if self.mesh is None:
            data['view'] = (self._startup_preferences or {}).get('view',{'name':'Orbit'})
        else:
            zoom = self.four_zoom if self.four_view else self.distance/self.fitted_distance()
            zooms = list(self.pane_zooms)
            if self.maximized:
                zooms[self.active_pane] = max(1/128,min(8,self.four_zoom*self.distance/self.maximized_distance))
            data['view'] = {'pane_zooms':zooms,'name':self.view_name,'angle':self.angle,'pitch':self.pitch,
                'active':self.active_pane,'four_angle':self.four_angle,
                'maximized':self.maximized,'zoom':max(1/128,min(8,zoom))}
        return data

    def persist_preferences(self,force=False,check=True):
        try:
            data = self.preference_snapshot() if check or force else self._prefs_pending
            if data is None:
                return
            if data==self._prefs_saved:
                self._prefs_pending = None
                return
            now = ticks_ms()
            if data!=self._prefs_pending:
                self._prefs_pending,self._prefs_since = data,now
            if not force and ticks_diff(now,self._prefs_since)<600:
                return
            # Back off after SD errors instead of retrying every frame.
            self._prefs_since = now
            write_preferences(self.vm.storage,data)
            self._prefs_saved = data
            self._prefs_pending = None
            self._prefs_error = None
        except (ValueError,OSError,MemoryError) as exc:
            detail = str(exc) or type(exc).__name__
            self.status = ('Not enough memory to save editor settings' if isinstance(exc,MemoryError)
                           else 'Could not save editor settings: '+detail)
            message = 'Sprite3D settings: '+type(exc).__name__+': '+detail
            # Keep the cause available in the system log, without flooding it
            # on debounced retries. Logging must never make save failure fatal.
            if message != self._prefs_error:
                self._prefs_error = message
                try:self.vm.log(message,2)
                except Exception:print(message)

    def restore_document_preferences(self):
        data = self._startup_preferences
        if data is None:
            return
        self._startup_preferences = None
        self.selection_mode_set(data.get('selection_mode','Model'))
        self.selection_camera = data.get('selection_camera',False)
        view = data.get('view',{})
        name,zoom = view.get('name','Orbit'),view.get('zoom',1)
        self.active_pane = view.get('active',1)
        self.four_angle = view.get('four_angle',-.7)
        self.pane_zooms = list(view.get('pane_zooms',[zoom]*4))
        if name=='4 View' or view.get('maximized',False):
            self.set_four(angle=self.four_angle,force=True)
            if view.get('maximized',False) and self.four_view:
                self.toggle_active_view()
        else:
            if name in ('Front','Side','Back','Top','Bottom'):
                self.set_view(name)
                angle,pitch = self.angle,self.pitch
            else:
                angle,pitch = view.get('angle',-.7),view.get('pitch',.32)
            self.orient(angle,pitch,name,self.fitted_distance(name)*zoom)
