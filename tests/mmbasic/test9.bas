'sin paths
CLS
df%=0
Option angle radians

For th!=0 To 4*Pi Step 0.04
rad!=(1.05+Sin(th!*4.5))*80
an!=th!-Cos(th!*10)/8
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