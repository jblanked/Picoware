'Mona 256b intro Atari XE/XL
CLS
Option default integer
Dim co(3)=(RGB(&Hff,&He2,&H89),RGB(&He9,&H9e,&H45),RGB(&Ha5,&H5a,&H00),0)

seed=&H7EC80000
XOR_MSK = &H04C11DB7
dir=0
carry=0
Restore BRUSH
  For part=0 To 63
    Read word
    seed = (seed And &HFFFF0000) Or word
    bx=word And 255
    by=(word>>8) And 255

For length = 0 To (64 - part) * 32 - 1
carry = seed And &H80000000
seed = (seed << 1) And &HFFFFFFFF
      If carry Then
        seed = seed Xor XOR_MSK
        dir = seed And 255
      EndIf
 If (dir And &H82) = 0 Then
          by = (by + 1) And 127
GoTo putd
EndIf
 If (dir And &H82) = 2 Then
          bx = (bx + 1) And 127
GoTo putd
     EndIf
 If (dir And &H82) = &H80 Then
          by = (by - 1)  And 127
 GoTo putd
 EndIf
 If (dir And &H82) = &H82 Then
          bx = (bx - 1) And 127
EndIf
putd:
      If (bx<128) And (by<96) Then
       Box 2*bx,2*by,2,2,0,co(part And 3),co(part And 3)
      EndIf
    Next length
  Next part



  BRUSH:
  Data        &H030A, &H37BE, &H2F9B, &H072B, &H0E3C, &HF59B, &H8A91, &H1B0B
  Data        &H0EBD, &H9378, &HB83E, &HB05A, &H70B5, &H0280, &HD0B1, &H9CD2
  Data        &H2093, &H209C, &H3D11, &H26D6, &HDF19, &H97F5, &H90A3, &HA347
  Data        &H8AF7, &H0859, &H29AD, &HA32C, &H7DFC, &H0D7D, &HD57A, &H3051
  Data        &HD431, &H542B, &HB242, &HB114, &H8A96, &H2914, &HB0F1, &H532C
  Data        &H0413, &H0A09, &H3EBB, &HE916, &H1877, &HB8E2, &HAC72, &H80C7
  Data        &H5240, &H8D3C, &H3EAF, &HAD63, &H1E14, &HB23D, &H238F, &HC07B
  Data        &HAF9D, &H312E, &H96CE, &H25A7, &H9E37, &H2C44, &H2BB9, &H2139