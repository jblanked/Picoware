"""SDL keyboard regression. Run on a disposable X server:

xvfb-run -a -s '-screen 0 800x600x24 -noreset' python tests/simulator_keyboard_layout.py
Requires Xvfb, xdotool, setxkbmap, and a built SDL viewer. Never changes the main desktop layout.
"""
import os,subprocess,time,sys,tempfile
from pathlib import Path
if not os.environ.get('DISPLAY') or 'xvfb-run.' not in os.environ.get('XAUTHORITY',''):
    raise SystemExit('Run this check with xvfb-run on a disposable X server')
root=Path(tempfile.mkdtemp(prefix='sprite-keyprobe-'))
frame=root/'frame'; keys=root/'keys'
frame.write_bytes(bytes(320*320*2))
subprocess.run(['setxkbmap','-layout','de'],check=True,capture_output=True)
p=subprocess.Popen([(sys.argv[1] if len(sys.argv)>1 else str(Path(__file__).resolve().parents[1]/'simulator/viewer/sdl_fb_viewer')),str(frame),str(keys),'1'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def xd(*args):
    r=subprocess.run(['xdotool',*args],capture_output=True,text=True,check=True)
    return r.stdout
try:
    for _ in range(100):
        r=subprocess.run(['xdotool','search','--pid',str(p.pid)],text=True,capture_output=True)
        wins=[v for v in r.stdout.splitlines() if v.isdigit()]
        if wins: break
        time.sleep(.05)
    xd('windowfocus','--sync',wins[-1]); time.sleep(.2)
    for label,combo in [('Shift7',['Shift_L','7']),('Ctrl7',['Control_L','7']),('AltGr8',['ISO_Level3_Shift','8']),('AltGr9',['ISO_Level3_Shift','9']),('Comma',['comma']),('Period',['period'])]:
        start=len(keys.read_text()) if keys.exists() else 0
        for key in combo: xd('keydown',key)
        time.sleep(.12)
        for key in reversed(combo): xd('keyup',key)
        time.sleep(.15)
        events=[line.split() for line in keys.read_text()[start:].splitlines()]
        expected={'Shift7':47,'Ctrl7':55,'AltGr8':91,'AltGr9':93,'Comma':44,'Period':46}[label]
        assert events==[['down',str(expected),'0'],['up',str(expected),'0']],(label,events)
        print('PASS',label,expected)
    # The release must still use the translated character after Shift lifts.
    start=len(keys.read_text())
    xd('keydown','Shift_L'); xd('keydown','7'); time.sleep(.12)
    xd('keyup','Shift_L'); xd('keyup','7'); time.sleep(.15)
    assert keys.read_text()[start:].splitlines()==['down 47 0','up 47 0']
    for key,code in (('a',97),('F5',133),('Up',181),('Return',13)):
        start=len(keys.read_text())
        xd('keydown',key); time.sleep(.12); xd('keyup',key); time.sleep(.15)
        assert keys.read_text()[start:].splitlines()==['down %d 0'%code,'up %d 0'%code],key
    subprocess.run(['setxkbmap','-layout','us'],check=True,capture_output=True)
    time.sleep(.2)
    for combo,code in ((('Shift_L','7'),38),(('bracketleft',),91),(('bracketright',),93)):
        start=len(keys.read_text())
        for key in combo: xd('keydown',key)
        time.sleep(.12)
        for key in reversed(combo): xd('keyup',key)
        time.sleep(.15)
        assert keys.read_text()[start:].splitlines()==['down %d 0'%code,'up %d 0'%code],combo
    print('PASS German/US translation, modifier release, plain letters, F5, arrows and Enter')
finally:
    p.terminate(); p.wait(timeout=3)
