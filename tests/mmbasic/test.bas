'Spheres raytrace
CLS
Dim pal(256)
pal(0)=RGB(0,0,0)
pal(1)=RGB(0,0,128)
pal(2)=RGB(8,128,8)
pal(3)=RGB(0,128,128)
pal(4)=RGB(128,0,0)
pal(5)=RGB(128,0,128)
pal(6)=RGB(128,64,32)
pal(7)=RGB(168,168,168)
pal(8)=RGB(128,128,128)
pal(9)=RGB(84,84,252)
pal(10)=RGB(42,252,42)
pal(11)=RGB(0,220,220)
pal(12)=RGB(255,0,0)
pal(13)=RGB(255,84,255)
pal(14)=RGB(255,255,0)
pal(15)=RGB(255,255,255)

pal(16)=RGB(255,255,255)
pal(32)=RGB(0,192,255)
pal(255)=RGB(0,0,192)
rainbow(16,32)
rainbow(32,255)


Read spheres
Dim c(spheres,3),r(spheres)
Dim q(spheres),cl(5)
scrw=320
scrh=320' or 200
w=scrw/2
h=scrh/2
s=0
cl(1)=6
cl(2)=1
cl(3)=cl(1)+8
cl(4)=cl(2)+8
For k=1 To spheres
Read c1,c2,c3,rr
c(k,1)=c1
c(k,2)=c2
c(k,3)=c3
r(k)=rr
q(k)=rr*rr
Next k

Data 6
Data -0.3,-0.8,3,0.6

Data 0.9,-1.4,3.5,0.35
Data 0.7,-0.45,2.5,0.4
Data -0.5,-0.3,1.5,0.15
Data 1.0,-0.2,1.5,0.1
Data -0.1,-0.2,1.25,0.2

For i=1 To scrh
For j=0 To scrw-1
x=0.3
y=-0.5
z=0
ba=3
dx=j-w
dy=h-i
dz=scrh/480*600
dd=dx*dx+dy*dy+dz*dz

recurs:
n=0-(y>=0 Or dy<=0)
If n=0 Then s=0-y/dy

For k=1 To spheres
px=c(k,1)-x
py=c(k,2)-y
pz=c(k,3)-z
pp=px*px+py*py+pz*pz
sc=px*dx+py*dy+pz*dz
If sc<=0 Then GoTo contk
bb=sc*sc/dd
aa=q(k)-pp+bb
If aa<=0 Then GoTo contk
sc=(Sqr(bb)-Sqr(aa))/Sqr(dd)
If (sc<s) Or (n<0) Then n=k:s=sc
contk:
Next k

If n<0 Then
c_=Int(16+(dy*dy/dd)*240)
Color pal(c_)
Pixel j,scrh-i
GoTo contj
EndIf
dx=dx*s
dy=dy*s
dz=dz*s
dd=dd*s*s
x=x+dx
y=y+dy
z=z+dz
If n<>0 Then
nx=x-c(n,1)
ny=y-c(n,2)
nz=z-c(n,3)
nn=nx*nx+ny*ny+nz*nz
l=2*(dx*nx+dy*ny+dz*nz)/nn
dx=dx-nx*l
dy=dy-ny*l
dz=dz-nz*l
GoTo recurs
EndIf

For k=1 To spheres
u=c(k,1)-x
v=c(k,3)-z
If u*u+v*v<=q(k) Then
ba=1
Exit For
EndIf
Next k
'If (x Mod 1+(x<0)>0.5)=(z Mod 1+(z<0)>0.5) Then
If (x-Int(x)>0.5)=(z-Int(z)>0.5) Then
 ik=cl(ba)
 Else
 ik=cl(ba+1)
 EndIf
  Color pal(ik)
Pixel j,scrh-i
EndIf
contj:
Next j
Next i


Sub rainbow(startidx,stopidx)
r0=(pal(startidx)>>16) And 255
r1=(pal(stopidx)>>16) And 255

g0=(pal(startidx)>>8) And 255
g1=(pal(stopidx)>>8) And 255

b0=pal(startidx) And 255
b1=pal(stopidx) And 255

For i=startidx+1 To stopidx-1
a=1-(stopidx-i)/(stopidx-startidx)
r_=Int(r0*(1-a)+r1*a)
g_=Int(g0*(1-a)+g1*a)
b_=Int(b0*(1-a)+b1*a)
pal(i)=RGB(r_,g_,b_)
Next i
End Sub