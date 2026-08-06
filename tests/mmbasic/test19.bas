'Orbits of a Dynamic System
'Lauerier,1991
Dim co(8)
co(0)=RGB(0,0,0)
co(1)=RGB(0,0,255)
co(2)=RGB(0,255,0)
co(3)=RGB(0,255,255)
co(4)=RGB(255,0,0)
co(5)=RGB(255,0,255)
co(6)=RGB(255,255,0)
co(7)=RGB(255,255,255)

CLS
zo=3'zoom
a=3.5
b=-3
x=3.21
y=6.54
GoSub 110
For n=0 To 10000
Color co((n Mod 64)/8)
Pixel x*zo+160,y*zo+160
z=x
x=y+w
GoSub 110
y=w-z
Next n
End
110
If x>1 Then w=a*x+b*(x-1):Return
If x<-1 Then w=a*x+b*(x+1):Return
w=a*x
Return
'alternatives for gosub
w=a*x+b*Sin(x):Return
w=a*x+b*Cos(x):Return
w=a+b*Sin(x):Return
w=a+b*Cos(x):Return

If Abs(x)<1 Then
w=a*x
Else
w=b*x+(a-b)/x
EndIf
Return