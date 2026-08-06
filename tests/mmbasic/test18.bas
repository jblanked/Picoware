'Burning ship fractal
CLS
w=320
h=320
ni=40'iterations
For x=0 To w-1
For y=0 To h-1
zr=0
zi=0
cr=0.002*x/w-1.9085
ci=-0.0045*y/h+0.0005
i=0
Do While (i<ni) And Sqr(zr*zr+zi*zi)<3
i=i+1
zr=Abs(zr)
zi=Abs(zi)
zr2=zr*zr
zi2=zi*zi
zi=2*zr*zi+ci
zr=zr2-zi2+cr
Loop
t=i/ni
r=Int(9*(1-t)*t*t*t*255)
g=Int(15*(1-t)*(1-t)*t*t*255)
b=Int(8.5*(1-t)*(1-t)*(1-t)*t*255)
Pixel x,h-y,RGB(r,g,b)
Next y
Next x