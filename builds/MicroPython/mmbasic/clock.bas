' Clock for PicoCalc MMBasic

CLS

'=== present time
Dim hh As integer
Dim mm As integer
Dim ss As integer

'=== parameters of clock hands
Const x0=160
Const y0=160
Const lh=70
Const lm=130
Const ls=130
Const l_=-10
Const th=-8
Const tm=-3
Const ts=-1

'=== draw clock hands
Sub DrawHour hour%,minute%,second%,c%
  hour_=hour%+minute%/60.0+second%/3600.0
  theta=Pi/6.0*hour_
  Line x0+l_*Sin(theta),y0-l_*Cos(theta),x0+lh*Sin(theta),y0-lh*Cos(theta),th,c%
End Sub

Sub DrawMinute hour%,minute%,second%,c%
  minute_=minute%+second%/60.0
  theta=Pi/30.0*minute_
  Line x0+l_*Sin(theta),y0-l_*Cos(theta),x0+lm*Sin(theta),y0-lm*Cos(theta),tm,c%
End Sub

Sub DrawSecond hour%,minute%,second%,c%
  theta=Pi/30.0*second%
  Line x0+l_*Sin(theta),y0-l_*Cos(theta),x0+ls*Sin(theta),y0-ls*Cos(theta),ts,c%
End Sub

'=== parameters of clock face
Const l1=150
Const l2=140
Const t1=-2
Const t2=-4

'=== draw clock face (numbers)
Sub DrawClockFace
  Font 3
  Color RGB(white)
  For i=1 To 12
    Text x0+l2*Sin(Pi/6.0*i),y0-l2*Cos(Pi/6.0*i),Str$(i),cm
  Next i
End Sub

'=== draw clock face (markers)
Sub DrawClockFace2
  '1,2,4,5,7,8,10,11
  For i=1 To 10 Step 3
    x=Sin(Pi/6.0*i)
    y=Cos(Pi/6.0*i)
    Line x0+l1*x,y0-l1*y,x0+l2*x,y0-l2*y,t1,RGB(grey)
    Line x0-l1*x,y0-l1*y,x0-l2*x,y0-l2*y,t1,RGB(grey)
  Next i
  '3,9,6
  Line x0+l1,y0,x0+l2,y0,t2,RGB(grey)
  Line x0-l1,y0,x0-l2,y0,t2,RGB(grey)
  Line x0,y0+l1,x0,y0+l2,t2,RGB(grey)
  '12
  Line x0+t2,y0-l1,x0+t2,y0-l2,t2,RGB(grey)
  Line x0-t2,y0-l1,x0-t2,y0-l2,t2,RGB(grey)
End Sub

'=== draw new clock hands
Sub DrawClockHands
  DrawHour   hh,mm,ss,RGB(lightgrey)
  DrawMinute hh,mm,ss,RGB(lightgrey)
  DrawSecond hh,mm,ss,RGB(red)
  Pixel x0,y0,RGB(black)
End Sub

'=== read Time$
Sub ReadTime
  hh=Val(Left$(Time$,2))
  mm=Val(Mid$(Time$,4,2))
  ss=Val(Right$(Time$,2))
End Sub

'=== time signal (1 shot)
Sub TimeSignal
  If mm=0 And ss=0 Then
    Play tone 998,1002
    Pause 500
    Play stop
  End If
End Sub

'=== time signal (2 shots)
Sub TimeSignal2
  If mm=0 And ss=0 Then
    Play tone 2000,0
    Pause 70
    Play stop
    Pause 130
    Play tone 2000,0
    Pause 70
    Play stop
  End If
End Sub

'=== clock process
Sub ClockProc
  CLS
  ReadTime
  DrawClockFace2
  DrawClockHands
  TimeSignal2
  FRAMEBUFFER copy f,n
End Sub

'***** MainProgram from here

FRAMEBUFFER create
FRAMEBUFFER write f
ClockProc
SetTick 1000,ClockProc,1

Do While Inkey$ = "":Loop
FRAMEBUFFER close
CLS
