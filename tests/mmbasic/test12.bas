'Barry Martin fractal
CLS
x!=0
y!=0
Do
t!=x!
x!=y!-Sin(x!)
y!=3.14-t!
Pixel 4*x!+160,4*y!+160,&Hff00
Loop Until Inkey$=Chr$(27)