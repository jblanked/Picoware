'DLA
CLS
Randomize &H123478
Option default integer
Dim s(319),c(319)
d=1
m=14
For i=0 To 319
s(i)=0
c(i)=0
Next i

Do While d<=319
x=1+Int(Rnd()*318)
f=x
If s(f)<s(x-1) Then f=x-1
If s(f)<s(x+1) Then f=x+1

If Int(Rnd()*2)=1 And s(f)=s(x+1) Then f=x+1
s(x)=s(f)
c(x)=c(f)

If c(x)=0 Then c(x)=1+(x Mod 14)
cc=c(x)
br=Choice(cc And 8,255,127)
rr=Choice(cc And 1,br,0)
gg=Choice(cc And 2,br,0)
bb=Choice(cc And 4,br,0)

Pixel x,319-s(x),RGB(rr,gg,bb)
s(x)=s(x)+1
If s(x)=d Then d=d+1
Loop