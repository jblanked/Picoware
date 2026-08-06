'biomorph fractal by Mad Teddy
CLS

constreal!=0.5
constimag!=0
screenheight=321
screenwidth=321
aspectratio!=screenwidth/screenheight

ymax!=1.88
ymin!=-ymax!
xmax!=ymax!*aspectratio!
xmin!=-xmax!

jlimit=screenwidth-1
ilimit=screenheight-1

For i=0 To ilimit
For j=0 To jlimit
x0!=xmin!+(xmax!-xmin!)*j/jlimit
y0!=-ymin!-(ymax!-ymin!)*i/ilimit
x!=x0!
y!=y0!
For n=1 To 100
xx!=x!*(x!*x!-3*y!*y!)+constreal!
yy!=y!*(3*x!*x!-y!*y!)+constimag!
x!=xx!
y!=yy!
If Abs(x!)>10 Or Abs(y!)>10 Or x!*x!+y!*y!>100 Then
n=100
EndIf
Next n

If Abs(x!)>10 And Abs(y!)>10 Then
cc=0
ElseIf Abs(x!)>10 And Abs(y!)<=10 Then
cc=RGB(170,0,0)
ElseIf Abs(x!)<=10 And Abs(y!)>10 Then
cc=RGB(0,170,0)
Else
cc=RGB(255,255,85)
EndIf
Pixel j,i,cc
Next j
Next i