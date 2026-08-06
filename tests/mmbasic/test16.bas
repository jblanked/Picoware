'spider fractal
CLS

iter=50
max=16

For y=-160 To 160
For x=-160 To 160

n=0
zx!=x*0.01
zy!=y*0.01
cx!=zx!
cy!=zy!
Do While ((zx!*zx!+zy!*zy!)<max) And (n<iter)
z1x!=zx!
z1y!=zy!
c1x!=cx!
c1y!=cy!

zx!=z1x!*z1x!-z1y!z1y!+cx!
zy!=2z1x!*z1y!+cy!
cx!=c1x!/2+zx!
cy!=c1y!/2+zy!
n=n+1
Loop

If n<iter Then
co=n Mod 16
Color RGB(co*16,co*16,0)
Pixel 160+x,160+y
EndIf
Next x
Next y