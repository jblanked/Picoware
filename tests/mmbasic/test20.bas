Option BASE 0
' Recursive tree drawing routine
Sub Tree(len, ang, lim)
If lim < 1 Then Exit Sub
If len < 2 Then Exit Sub
Turtle FORWARD len
Turtle RIGHT ang
Tree len * 0.67, ang, lim - 1
Turtle LEFT ang * 2
Tree len * 0.67, ang, lim - 1
Turtle RIGHT ang
Turtle BACK len
End Sub

' Main program
len = 80
ang = 22
lim = 10
CLS
Turtle reset
Turtle HOME
Turtle PEN DOWN
' Move near bottom centre of screen
Turtle SET XY MM.HRES / 2, MM.VRES - 20
Turtle SET HEADING 0
Do
CLS
Turtle SET XY MM.HRES / 2, MM.VRES - 20
Turtle SET HEADING 0
Tree len, ang, lim
Text 0,0,"Len: " + Str$(len) +"  Ang: " + Str$(ang) +"  Lim: " + Str$(lim)
Do
k$ = Inkey$
Loop Until k$<>""
Select Case k$
Case Chr$(128)        ' Up arrow (may vary by firmware)
len = len + 5
Case Chr$(129)        ' Down arrow
len = len - 5
Case Chr$(130)        ' Left arrow
ang = ang - 2
Case Chr$(131)        ' Right arrow
ang = ang + 2
Case "+"
lim = lim + 1
Case "="
lim = lim + 1
Case "-"
lim = lim - 1
Case "_"
lim = lim - 1
Case "q","Q"
Exit Do
End Select
If ang < 2 Then ang = 2
If lim > 15 Then lim = 15
If lim < 1 Then lim = 1
If len < 5 Then len = 5
Loop