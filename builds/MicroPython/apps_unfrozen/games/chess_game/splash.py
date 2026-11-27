"""Small RGB565 loading illustration displayed before the chess modules load."""
PATH = 'picoware/apps/games/chess_game/assets/loading.bin'


def show(vm):
    from picoware.system.boards import BOARD_ID
    d=vm.draw; width,height=int(d.size.x),int(d.size.y)
    x=y=0
    if BOARD_ID in (4,5):
        size=int(min(width,height)*0.70)
        x,y=(width-size)//2,(height-size)//2
        width=height=size
    compact=height<180
    bg,fg,accent=0x10C4,0xEF5D,0x6657
    d.fill_screen(bg)
    font=0 if compact else 2
    title='PicoChess'
    d._text(x+max(0,(width-d.len(title,font))//2),y+3 if compact else y+12,title,fg,font)
    side=min(192,width-12,height-(32 if compact else 80))
    left=x+(width-side)//2; top=y+(height-side)//2
    try:
        data=vm.storage.read(PATH,'rb')
        if len(data)!=192*192*2: raise ValueError('Invalid splash')
        row=bytearray(side*2)
        for yy in range(side):
            src_y=yy*192//side
            for xx in range(side):
                src=(src_y*192+xx*192//side)*2
                row[xx*2]=data[src]; row[xx*2+1]=data[src+1]
            d._bytearray(left,top+yy,side,1,row)
    except (OSError,ValueError,TypeError,MemoryError):
        # Text still communicates startup if the optional illustration is absent.
        pass
    label='Loading...'
    d._text(x+max(0,(width-d.len(label,0))//2),y+height-13,label,fg,0)
    d._fill_rectangle(x+width//4,y+height-3,width//2,2,accent)
    d.swap()
