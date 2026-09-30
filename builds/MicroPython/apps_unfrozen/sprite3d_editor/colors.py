"""Palette and RGB controls with a non-destructive color preview."""
from struct import unpack_from

PALETTE = (0x0000,0x2104,0x4208,0x630C,0x8410,0xA514,0xC618,0xFFFF,
           0xF800,0xFC00,0xFFE0,0x07E0,0x07FF,0x001F,0x801F,0xF81F,
           0xFBEF,0xFDCF,0xFFF0,0x87F0,0x87FF,0x841F,0xC41F,0xFC1F,
           0x8000,0x8200,0x8400,0x0400,0x0410,0x0010,0x4010,0x8010)


def channels(color):
    return [color>>11,(color>>5)&63,color&31]


def rgb(color):
    r,g,b = channels(color)
    return (round(r*255/31),round(g*255/63),round(b*255/31))


def nearest(color):
    value = rgb(color)
    return min(range(len(PALETTE)),key=lambda i:sum((a-b)**2 for a,b in zip(value,rgb(PALETTE[i]))))


class ColorTools:
    def begin_color_picker(self):
        selected = self.selected_triangles()
        if not selected or self.selection_mode in ('Vertices','Edges'):
            self.dialog = ('Color','Select a model, island or triangles')
            return
        initial = unpack_from('<H',self.records,selected[0]*40+36)[0]
        self.color_picker = {'color':initial,'original':initial,'index':nearest(initial),
                             'channel':0,'rgb':self.color_rgb,'hex':False,'error':''}

    def run_color_picker(self,inputs):
        from picoware.system.buttons import (BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,
            BUTTON_RIGHT,BUTTON_TAB,BUTTON_CENTER,BUTTON_BACK,BUTTON_ESCAPE,BUTTON_H)
        state = self.color_picker
        if state['hex']:
            keyboard = self.vm.keyboard
            if inputs.button in (BUTTON_BACK,BUTTON_ESCAPE):
                inputs.reset()
                keyboard.reset()
                state['hex'] = False
            elif keyboard.is_finished:
                text = keyboard.response.strip().lstrip('#')
                keyboard.reset()
                state['hex'] = False
                try:
                    value = int(text,16)
                    if not 0<=value<=65535:
                        raise ValueError('Color out of range')
                    state['color'],state['index'] = value,nearest(value)
                    state['error'] = ''
                except ValueError:
                    state['error'] = 'Use hex 0000-FFFF'
            elif not keyboard.run():
                keyboard.reset()
                state['hex'] = False
            else:
                return
        else:
            button = inputs.button
            inputs.reset()
            if button >= 0:
                state['error'] = ''
            if button in (BUTTON_BACK,BUTTON_ESCAPE):
                self.color_picker = None
                self.status = 'Color cancelled'
            elif button == BUTTON_CENTER:
                self.color_picker = None
                self.edit_geometry('Color',state['color'])
            elif button == BUTTON_TAB:
                state['rgb'] = not state['rgb']
                self.color_rgb = state['rgb']
            elif button == BUTTON_H:
                keyboard = self.vm.keyboard
                keyboard.reset()
                keyboard.title = 'Hex color (RGB565: 0000-FFFF)'
                keyboard.response = '%04X' % state['color']
                keyboard.run(force=True)
                keyboard.run(force=True)
                state['hex'] = True
                return
            elif button in (BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,BUTTON_RIGHT):
                if state['rgb']:
                    if button in (BUTTON_UP,BUTTON_DOWN):
                        state['channel'] = (state['channel']+(1 if button==BUTTON_DOWN else -1))%3
                    else:
                        values = channels(state['color'])
                        channel = state['channel']
                        values[channel] = max(0,min((31,63,31)[channel],values[channel]+(1 if button==BUTTON_RIGHT else -1)))
                        state['color'] = (values[0]<<11)|(values[1]<<5)|values[2]
                        state['index'] = nearest(state['color'])
                else:
                    index = state['index']
                    if button in (BUTTON_UP,BUTTON_DOWN):
                        index = (index+(8 if button==BUTTON_DOWN else -8))%32
                    else:
                        index = index//8*8+(index+(1 if button==BUTTON_RIGHT else -1))%8
                    state['index'],state['color'] = index,PALETTE[index]
        if self.color_picker is None:
            self.draw_frame()
        else:
            self.draw_color_picker()

    def draw_color_picker(self):
        state = self.color_picker
        draw = self.vm.draw
        width,height = int(draw.size.x),int(draw.size.y)
        draw.clear(color=0x1082)
        draw._fill_rectangle(0,0,width,20,0x2945)
        draw._text(8,6,'Color - '+('RGB' if state['rgb'] else 'Palette'),0xFFFF)
        draw._text(16,25,'Before',0xFFFF)
        draw._text(88,25,'After',0xFFFF)
        for x,color in ((16,state['original']),(88,state['color'])):
            draw._fill_rectangle(x,37,60,26,color)
            draw._rectangle(x-1,36,62,28,0xFFFF)
        draw._text(166,31,'Hex %04X' % state['color'],0xFFFF)
        draw._text(166,48,'RGB %d %d %d' % rgb(state['color']),0xFFFF)
        draw._text(16,73,'Palette',0xFFE0 if not state['rgb'] else 0x7BEF)
        cell = (width-32)//8
        for i,color in enumerate(PALETTE):
            x,y = 16+(i%8)*cell,87+(i//8)*22
            draw._fill_rectangle(x+3,y+3,cell-6,16,color)
            if i == state['index']:
                draw._rectangle(x,y,cell,22,0xFFE0 if not state['rgb'] else 0x7BEF)
                if color == state['color']:
                    ink = 0x0000 if sum(rgb(color))>380 else 0xFFFF
                    draw._text(x+cell//2-3,y+7,'+',ink)
        values = channels(state['color'])
        for i,color in enumerate((0xF800,0x07E0,0x001F)):
            y = 188+i*24
            chosen = state['rgb'] and i==state['channel']
            draw._text(16,y+5,'RGB'[i],0xFFE0 if chosen else 0xFFFF)
            maximum = (31,63,31)[i]
            for step in range(32):
                parts = [0,0,0]
                parts[i] = round(step*maximum/31)
                shade = (parts[0]<<11)|(parts[1]<<5)|parts[2]
                draw._fill_rectangle(40+step*6,y+2,6,14,shade)
            x = 40+round(values[i]*191/maximum)
            draw._rectangle(x-2,y,5,18,0xFFE0 if chosen else 0xFFFF)
            draw._text(248,y+5,str(rgb(state['color'])[i]),0xFFFF)
        draw._text(8,height-49,state['error'] or 'Tab Palette/RGB   H Hex',0xFFE0 if state['error'] else 0xFFFF)
        draw._text(8,height-33,'Arrows Choose/Adjust',0xFFFF)
        draw._text(8,height-17,'Enter Apply   Esc Cancel',0xFFFF)
        draw.swap()
