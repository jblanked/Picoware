'Circle Fractal
Dim scalev1!=5
Dim scalev2!=2
Dim vp!=0.2

Dim scaleh1!=2
Dim scaleh2!=1.4
Dim hp!=0.2

Dim depth%=0

CLS
drawf(320,320,Pi-0.9,50,0)
Save image "fracc.bmp"
Sub drawf x,y,a!,s!,w
Local x1,y1,c,ns!
depth%=depth%+1
If s!<0.2 Then
GoTo l1
EndIf

If depth% And 1 Then
c=&Hffffff
Else
c=&H00ff00
EndIf

Circle x/2,y/2,s!/2,1,1,c,c

If w<>1 Then
x1=Sin(a!)*s!*2.5+x
y1=Cos(a!)*s!*2.5+y
If w=3 Then
ns!=s!/scalev2!
Else
ns!=s!/scalev1!
EndIf
drawf(x1,y1,a!+vp!,ns!,3)
EndIf

If w<>2 Then
x1=Sin(a!-Pi/2)*s!*2.5+x
y1=Cos(a!-Pi/2)*s!*2.5+y
If w=4 Then
ns!=s!/scaleh2!
Else
ns!=s!/scaleh1!
EndIf
drawf(x1,y1,a!+hp!,ns!,4)

EndIf

If w<>3 Then
x1=Sin(a!-Pi)*s!*2.5+x
y1=Cos(a!-Pi)*s!*2.5+y
If w=1 Then
ns!=s!/scalev2!
Else
ns!=s!/scalev1!
EndIf
drawf(x1,y1,a!+vp!,ns!,1)
EndIf

If w<>4 Then
x1=Sin(a!-Pi*1.5)*s!*2.5+x
y1=Cos(a!-Pi*1.5)*s!*2.5+y
If w=2 Then
ns!=s!/scaleh2!
Else
ns!=s!/scaleh1!
EndIf
drawf(x1,y1,a!+hp!,ns!,2)
EndIf
l1:
depth%=depth%-1
End Sub