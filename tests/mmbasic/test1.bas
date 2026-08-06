'scrambler fractal,Processing
'press +/- for size
'spacebar for generation
'arrows to move
'Esc quits

FRAMEBUFFER create
Dim integer gen=0,rad=80,thick=2,xb=160,yb=160
drw()

Do
k$=Inkey$

If k$="+" Then
rad=rad+1
drw()
EndIf

If k$="-" Then
rad=rad-1
drw()
EndIf

If k$=" " Then
gen=gen+1
drw()
EndIf

If k$=Chr$(128) Then'UP
yb=yb-10
drw()
EndIf

If k$=Chr$(129) Then'DOWN
yb=yb+10
drw()
EndIf

If k$=Chr$(130) Then'LEFT
xb=xb-10
drw()
EndIf

If k$=Chr$(131) Then'RIGHT
xb=xb+10
drw()
EndIf

Loop Until k$=Chr$(27)
FRAMEBUFFER write n
'Save image "sf.bmp"

Sub drw()
FRAMEBUFFER write f
CLS
f=0
gr=100*(gen+1)
For f=0 To 2*Pi Step Pi/gr
x=xb
y=yb
last=1
For i=0 To gen
fa=2^i
x=x+Cos(fa*f)*rad/fa
y=y+last*Sin(fa*f)*rad/fa
last=-last
Next i
Box x,y,thick,thick
Next f
FRAMEBUFFER write n
FRAMEBUFFER wait
FRAMEBUFFER copy f,n
End Sub