'Aabesque BASICODE3 program
CLS
Dim t(80) As float
Dim ho,ve,x0,y0,mx,my,rc,tt,aa,bb As float
Const km=0.104719755

aa=0
bb=0
For n=0 To 79
t(n+1)=Sin(n*km)
Next n
For n=5 To 60 Step 5
mx=0.5+0.31*t(n+1)
my=0.5-0.31*t(n+15+1)
rc=0.18
aa=n+45
bb=n+75
x0=0
y0=0
l3020()

rc=0.119
aa=n+10
bb=n+50
l3020()
Next n

Sub l3020()
tt=aa
l3110()
Pixel x0+ho,y+ve

If bb<=aa Then
bb=bb+0
End If

For z=aa To bb
hoo=ho
vee=ve
tt=z
l3110()
Line x0+ho,y0+ve,x0+hoo,y0+vee
Next z
End Sub

Sub l3110()
31
If tt>60 Then
tt=tt-60
GoTo 31
End If
ho=Int(300*(mx+rc*t(tt+1)))
ve=Int(300*(my-rc*t(tt+15+1)))

End Sub