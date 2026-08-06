'Monkey tree fractal
CLS
Dim dx(11)
Dim dy(11)
Dim sd(6)
Dim rd(6)
Dim sn(4)
Dim ln(6)
m=7/6
Restore l270
For n=0 To 6
Read xx
sd(n)=xx
Read xx
rd(n)=xx
ln(n)=1/3
Next n
ln(2)=Sqr(ln(1))
nc=4
x=300
y=220
tl=240

For c=0 To nc
sn(c)=0
Next c

Do While sn(0)=0
x0=x
y0=y
d=0
l=tl
ns=0
For c=1 To nc
i=sn(c)
l=l*ln(i)
j=sn(c-1)
ns=ns+sd(j)
k=Int(ns/2)
If k*2<>ns Then
d=d+12-rd(i)
Else
d=d+rd(i)
EndIf
d=d Mod 12
Next c

x=x+m*l*Cos(Pi/6*(d-6))
y=y-l*Sin(Pi/6*(d-6))

Line x0,y0,x,y,,&Hffffff

sn(nc)=sn(nc)+1

For c=nc To 1 Step -1
If sn(c)=7 Then
sn(c)=0
sn(c-1)=sn(c-1)+1
EndIf
Next c
Loop

l270:
Data 0,0,1,0,1,7
Data 0,10,0,0,0,2,1,2