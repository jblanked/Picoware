'celtic knot from just basic
CLS
Option angle radians
th%=14
xc%=160
yc%=160
d%=th%*5
r%=th%*4
r1%=th%*3
hex!=Pi/3
hd2!=hex!/2

Color &Hffffff
For nh%=1 To 6
x0%=xc%+d%*Cos(nh%*hex!-hd2!)
y0%=yc%+d%*Sin(nh%*hex!-hd2!)
s!=nh%*hex!
'outer radius
arc_ x0%,y0%,r%,s!-0.37,s!+1.2
arc_ x0%,y0%,r%,s!+1.47,s!+2.77
'inner eye
arc_ x0%,y0%,r%,s!+3.05,s!+4.3
arc_ x0%,y0%,r%,s!+4.55,s!+5.6

'inner radius
arc_ x0%,y0%,r1%,s!-0.1,s!+1.15
arc_ x0%,y0%,r1%,s!+1.51,s!+2.73
'inner eye
arc_ x0%,y0%,r1%,s!+3.1,s!+4.25
arc_ x0%,y0%,r1%,s!+4.58,s!+5.32

'outside origins
x0%=xc%+(2*d%-1.5*th%)*Cos(s!)
y0%=yc%+(2*d%-1.5*th%)*Sin(s!)
'outer radius
arc_ x0%,y0%,r%,s!+1.68,s!+3.25
arc_ x0%,y0%,r%,s!+3.51,s!+4.6
'inner radius
arc_ x0%,y0%,r1%,s!+1.98,s!+3.2
arc_ x0%,y0%,r1%,s!+3.56,s!+4.3
Next nh%


Sub arc_  x%,y%,r%,start!,stop!

If stop!<0 Then stop!=stop!+2*Pi
If start!<0 Then start!=start!+2*Pi

If stop!<start! Then
t!=stop!
stop!=start!
start!=t!
End If

ast!=10*Pi/(r%*r%*(stop!-start!))
a!=start!
Do While a!<stop!
 Pixel x%+r%*Cos(a!),y%+r%*Sin(a!)
a!=a!+ast!
Loop

End Sub