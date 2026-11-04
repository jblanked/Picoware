"""Modal, registry-driven editor preferences; never modifies the document."""
from .preferences import check_step

# Section, attribute (or transform kind), title, type, default, choices, help.
OPTIONS = (
    ('Editing','move_on_create','Move on create','toggle',True,(), 'Place each new primitive with Move.'),
    ('Editing','move_on_duplicate','Move on duplicate','toggle',True,(), 'Move only the newly duplicated faces.'),
    ('Editing','auto_fit_creation','Auto-fit after creation','toggle',True,(), 'Fit the camera after adding a mesh.'),
    ('Editing','move_step_mode','Move step mode','choice','Automatic',('Automatic','Custom'), 'Automatic uses one tenth of the grid.'),
    ('Editing','Move','Custom move step','number',1.0,(), 'Used when Move step mode is Custom.'),
    ('Editing','Rotate','Rotate step','number',5.0,(), 'Degrees per rotation key press.'),
    ('Editing','Scale','Scale step','number',.1,(), 'Scale change per key press.'),
    ('Editing','snap','Snap','toggle',False,(), 'Snap transforms to the grid or step.'),
    ('Editing','linked_vertices','Linked vertices','toggle',True,(), 'Manual edits include coincident vertices.'),
    ('Navigation','orbit_speed','Orbit speed','choice','Normal',('Slow','Normal','Fast'), 'Camera rotation per arrow key press.'),
    ('Navigation','zoom_speed','Zoom speed','choice','Normal',('Slow','Normal','Fast'), 'Camera zoom per arrow key press.'),
    ('Appearance','shading','Shading','choice','Asset',('Asset','Solid','Wireframe','Solid + Wireframe'), 'Choose how model surfaces are drawn.'),
    ('Appearance','backface_culling','Backface culling','toggle',True,(), 'Hide faces pointing away from the camera.'),
    ('Appearance','show_grid','Grid','toggle',True,(), 'Show the ground grid.'),
    ('Appearance','show_orientation','Orientation indicator','toggle',True,(), 'Show the XYZ orientation guide.'),
    ('Appearance','show_vertex_info','Vertex info','toggle',True,(), 'Show information for the active vertex.'),
    ('Appearance','show_normals','Normals','toggle',False,(), 'Show face normal direction guides.'),
    ('Appearance','show_edge_lengths','Edge lengths','toggle',False,(), 'Show measured edge lengths.'),
    ('Appearance','xray_vertices','X-Ray selection','toggle',False,(), 'Allow selecting hidden components.'),
    ('Appearance','color_rgb','Color selector mode','toggle',False,(), 'Open Color in Palette or RGB mode.'),
    ('Reset','reset','Restore defaults','action',None,(), 'Reset these options; keep your model and view.'),
)


def wrapped(text, columns):
    line = ''
    for word in text.split():
        if line and len(line)+len(word)+1 > columns:
            yield line
            line = word
        else:
            line += (' ' if line else '')+word
    if line:
        yield line


class SettingsTools:
    def begin_settings(self):
        self.menu,self.submenu = -1,False
        self.settings_state = {'row':0,'top':0,'numeric':None,'confirm':False,'drawn':None}
        self.status = ''
        self.draw_settings()

    def setting_value(self, option):
        return self.steps[option[1]] if option[3]=='number' else getattr(self,option[1])

    def change_setting(self, option, value):
        from .rendercache import clear
        name,kind = option[1],option[3]
        old = self.setting_value(option)
        try:
            if kind == 'number':
                check_step(name,value)
                self.steps[name] = value
            else:
                setattr(self,name,value)
            if name in ('shading','backface_culling') and self.mesh is not None:
                self.refresh_previews()
            if option[0] == 'Appearance':
                clear(self)
            self.status = ''
            self.persist_preferences()
            return True
        except (ValueError,OSError,MemoryError) as exc:
            if kind == 'number':
                self.steps[name] = old
            else:
                setattr(self,name,old)
            self.status = str(exc) or 'Not enough memory'
            return False

    def restore_settings(self):
        """Prepare display changes first so a failed reset keeps prior values."""
        from .rendercache import clear
        old_shading,old_culling = self.shading,self.backface_culling
        try:
            self.shading,self.backface_culling = 'Asset',True
            if self.mesh is not None:
                self.refresh_previews()
        except (ValueError,OSError,MemoryError) as exc:
            self.shading,self.backface_culling = old_shading,old_culling
            self.status = 'Reset failed: '+(str(exc) or 'Not enough memory')
            return
        for option in OPTIONS:
            if option[3] == 'number':
                self.steps[option[1]] = option[4]
            elif option[3] != 'action':
                setattr(self,option[1],option[4])
        clear(self)
        self.status = 'Defaults restored'
        self.persist_preferences()

    def run_settings(self, inputs):
        from picoware.system.buttons import (BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,
            BUTTON_RIGHT,BUTTON_CENTER,BUTTON_ESCAPE,BUTTON_BACK)
        state = self.settings_state
        if state['numeric'] is not None:
            keyboard = self.vm.keyboard
            if inputs.button in (BUTTON_BACK,BUTTON_ESCAPE):
                keyboard.reset()
                state['numeric'] = None
            elif keyboard.is_finished:
                response = keyboard.response.strip()
                option = OPTIONS[state['numeric']]
                keyboard.reset()
                state['numeric'] = None
                try:
                    self.change_setting(option,float(response))
                except (ValueError,OverflowError):
                    self.status = 'Enter a valid finite number'
            elif not keyboard.run():
                keyboard.reset()
                state['numeric'] = None
            else:
                return
            state['drawn'] = None
            inputs.reset()
        else:
            button = inputs.button
            inputs.reset()
            if state['confirm']:
                if button == BUTTON_CENTER:
                    state['confirm'] = False
                    self.restore_settings()
                elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                    state['confirm'] = False
            elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                self.persist_preferences(force=True)
                self.settings_state = None
                from .rendercache import clear
                clear(self)
                self._frame_drawn = False
                self.draw_frame()
                return
            elif button in (BUTTON_UP,BUTTON_DOWN):
                state['row'] = (state['row']+(1 if button==BUTTON_DOWN else -1))%len(OPTIONS)
                self.status = ''
            elif button in (BUTTON_CENTER,BUTTON_LEFT,BUTTON_RIGHT):
                option = OPTIONS[state['row']]
                kind = option[3]
                if kind == 'action':
                    if button == BUTTON_CENTER:
                        state['confirm'] = True
                elif kind == 'number':
                    if button == BUTTON_CENTER:
                        keyboard = self.vm.keyboard
                        keyboard.reset()
                        keyboard.title = option[2]
                        keyboard.response = str(self.setting_value(option))
                        state['numeric'] = state['row']
                        keyboard.run(force=True)
                        keyboard.run(force=True)
                        return
                else:
                    value = self.setting_value(option)
                    if kind == 'toggle':
                        value = not value
                    else:
                        choices = option[5]
                        value = choices[(choices.index(value)+(-1 if button==BUTTON_LEFT else 1))%len(choices)]
                    self.change_setting(option,value)
        self.draw_settings()

    def draw_settings(self):
        state = self.settings_state
        if state['numeric'] is not None:
            return
        key = (state['row'],state['confirm'],self.status,tuple(
            self.setting_value(o) for o in OPTIONS if o[3]!='action'))
        if key == state['drawn']:
            return
        draw = self.vm.draw
        width,height = int(draw.size.x),int(draw.size.y)
        rows,section = [],None
        chosen = 0
        for index,option in enumerate(OPTIONS):
            if option[0] != section:
                section = option[0]
                rows.append((section,None))
            if index == state['row']:
                chosen = len(rows)
            rows.append((option[2],index))
        capacity = max(1,(height-100)//16)
        top = min(state['top'],chosen)
        if chosen >= top+capacity:
            top = chosen-capacity+1
        state['top'] = top
        draw.clear(color=0x1082)
        draw._fill_rectangle(0,0,width,22,0x2945)
        draw._text(6,5,'Settings',0xFFFF)
        draw._text(width-66,5,'%d / %d'%(state['row']+1,len(OPTIONS)),0xBDF7)
        for line,(label,index) in enumerate(rows[top:top+capacity]):
            y = 26+line*16
            if index is None:
                draw._text(6,y,label,0x07FF)
                continue
            option = OPTIONS[index]
            selected = index==state['row']
            if selected:
                draw._fill_rectangle(2,y-1,width-4,16,0x4208)
            if option[3] == 'action':
                value = '...'
            else:
                value = self.setting_value(option)
                if option[1] == 'color_rgb':
                    value = 'RGB' if value else 'Palette'
                elif option[3] == 'toggle':
                    value = 'On' if value else 'Off'
                elif option[3] == 'number':
                    value = '%g'%value
                if value == 'Solid + Wireframe':
                    value = 'Solid + Wire'
            draw._text(8,y,label,0xFFFF if selected else 0xBDF7)
            draw._text(max(8,width-8-len(value)*8),y,value,0xFFE0 if selected else 0xFFFF)
        message = 'Restore defaults? Enter confirms, Esc cancels.' if state['confirm'] else self.status or OPTIONS[state['row']][6]
        for line,text in enumerate(wrapped(message,max(1,(width-12)//8))):
            if line == 3:
                break
            draw._text(6,height-68+line*14,text,0xFFE0 if self.status or state['confirm'] else 0xBDF7)
        draw._text(6,height-18,'Up/Down  Enter: change  Esc: back',0xFFFF)
        draw.swap()
        state['drawn'] = key
