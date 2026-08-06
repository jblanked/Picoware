'dancing circles, TIC-80
Option default integer
n=6
Dim ang(n)
For i=1 To n-1
ang(i)=0
Next i
w=25

FRAMEBUFFER create
FRAMEBUFFER write f
Do
CLS

x=160
y=160
Circle x,y,n*w,1,1,&Hffffff,0
For i=1 To n-1
x=x+w*Cos(ang(i)/30)
y=y+w*Sin(ang(i)/30)
Circle x,y,(n-i)*w,1,1,&Hffffff,0
ang(i)=ang(i)+i
Next i
FRAMEBUFFER wait
FRAMEBUFFER copy f,n
Loop Until Inkey$=Chr$(27)