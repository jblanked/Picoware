'sin paths
CLS
df%=0
Option angle radians


For th!=0 To 2*Pi Step 0.015
rad!=-(0.5*Sin(5*th!))*(0.5*Cos(4*th!))*600
an!=th!+Sin(rad!/60)
xp%=Int(160+rad!*Cos(an!))
yp%=Int(160+rad!*Sin(an!))

If df%=1 Then
Line x0%,y0%,xp%,yp%,1,&Hffffff
x0%=xp%
y0%=yp%
Else
df%=1
x0%=xp%
y0%=yp%
End If
Next th!