'polar rose
a0%=0
b0%=0
cc!=Pi/180
FRAMEBUFFER create
FRAMEBUFFER write f

Do
CLS
FRAMEBUFFER wait
a0%=a0%+5
b0%=b0%+3
For j=0 To 2
a%=a0%+j*120
For i=0 To 20
r%=100*Sin((a%+i)*3*cc!)
x%=r%*Cos((a%+i+b0%)*cc!)+160
y%=r%*Sin((a%+i+b0%)*cc!)+160
Circle x%,y%,i>>1,1,1,&Hffffff,&Hffffff)
Next i
Next j
FRAMEBUFFER copy f,n
Loop Until Inkey$=Chr$(27)