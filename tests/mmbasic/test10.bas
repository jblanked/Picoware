' leaf QB program
CLS
ex%=220
sx%=50
sy%=160
x!=1
y1=0
r3!=Sqr(3)/6
Randomize Timer

Do
If Rnd()>0.5 Then
x0!=0.5*x!+r3!*y!
y0!=r3!*x!-0.5*y!

Else
x0!=0.66666666*x!+0.3333333
y0!=-0.66666666*y
End If
x!=x0!
y!=y0!

Pixel x!*ex%+sx%,sy%-y!*ex%
Loop Until Inkey$=Chr$(27)