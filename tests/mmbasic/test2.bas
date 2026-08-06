' ==========================================
' PicoCalc Blocks Game (with FRAMEBUFFER)
' - True double buffering using FRAMEBUFFER + LAYER
' - Static background on F, dynamic sprites on L
' - FRAMEBUFFER MERGE for flicker-free display
' ==========================================
OPTION EXPLICIT

' ---- Tunables ----
CONST PAD_ACCEL = 2.0
CONST PAD_DECAY = 0.88
CONST PAD_MAX   = 24
CONST BRADIUS   = 6
CONST BALL_SPEED_INIT = 3.0
CONST BALL_SPEED_ACCEL_PER_SEC = 0.03
CONST PADDLE_KICK = 0.2
CONST TICK_MS   = 38

' ---- Screen & colors ----
CONST W% = MM.HRES
CONST H% = MM.VRES
CONST HUDH% = 18

CONST COL_BG%     = RGB(BLACK)
CONST COL_TXT%    = RGB(WHITE)
CONST COL_BORDER% = RGB(MYRTLE)
CONST COL_PAD%    = RGB(GREEN)
CONST COL_BALL%   = RGB(RED)

' ---- Block layout ----
CONST LEVELS% = 10
CONST BLOCK_ROWS% = 5
CONST BLOCK_COLS% = 8
CONST BLOCK_W% = 35
CONST BLOCK_H% = 12
CONST BLOCK_GAP% = 4
CONST BLOCK_TOP% = 40

' ---- Block types ----
CONST BLOCK_RED% = 30        ' 30 points, 1 hit
CONST BLOCK_ORANGE% = 20     ' 20 points, 1 hit
CONST BLOCK_YELLOW_FULL% = 12   ' 10 points, 2 hits (full health)
CONST BLOCK_YELLOW_DMG% = 11    ' 10 points, 1 hit left (damaged)
CONST BLOCK_BLUE% = 99       ' Indestructible, no points

' ---- Editable board layout (R=Red, O=Orange, Y=Yellow, B=Blue/Indestructible, 0=Empty) ----
' Level 1 - Easy warmup
DATA "0","0","0","0","0","0","0","0"
DATA "0","0","0","0","0","0","0","0"
DATA "0","0","R","R","R","R","0","0"
DATA "0","R","R","Y","Y","R","R","0"
DATA "R","R","R","R","R","R","R","R"
' Level 2 - Getting harder
DATA "0","0","R","R","R","R","0","0"
DATA "0","O","O","O","O","O","O","0"
DATA "Y","Y","Y","Y","Y","Y","Y","Y"
DATA "Y","Y","Y","Y","Y","Y","Y","Y"
DATA "Y","Y","Y","Y","Y","Y","Y","Y"
' Level 3 - Mixed blocks
DATA "R","R","O","O","O","O","R","R"
DATA "R","O","Y","Y","Y","Y","O","R"
DATA "O","Y","Y","Y","Y","Y","Y","O"
DATA "O","Y","Y","Y","Y","Y","Y","O"
DATA "Y","Y","Y","Y","Y","Y","Y","Y"
' Level 4 - Pyramid
DATA "0","0","0","R","R","0","0","0"
DATA "0","0","O","O","O","O","0","0"
DATA "0","Y","Y","Y","Y","Y","Y","0"
DATA "Y","Y","Y","Y","Y","Y","Y","Y"
DATA "0","0","0","B","B","0","0","0"
' Level 5 - Box
DATA "R","R","R","R","R","R","R","R"
DATA "R","0","0","0","0","0","0","R"
DATA "R","0","B","B","B","B","0","R"
DATA "R","0","0","0","0","0","0","R"
DATA "R","R","R","R","R","R","R","R"
' Level 6 - Corners
DATA "R","R","0","0","0","0","O","O"
DATA "R","Y","0","Y","Y","0","Y","O"
DATA "0","0","B","Y","Y","B","0","0"
DATA "Y","Y","0","B","B","0","Y","Y"
DATA "O","O","0","0","0","0","R","R"
' Level 7 - Wings
DATA "R","0","0","Y","Y","0","0","R"
DATA "O","O","B","Y","Y","B","O","O"
DATA "Y","Y","Y","B","B","Y","Y","Y"
DATA "Y","Y","B","O","O","B","Y","Y"
DATA "0","0","0","R","R","0","0","0"
' Level 8 - Checkers
DATA "R","O","R","O","R","O","R","O"
DATA "Y","B","Y","B","Y","B","Y","B"
DATA "O","Y","O","Y","O","Y","O","Y"
DATA "B","Y","B","Y","B","Y","B","Y"
DATA "R","O","R","O","R","O","R","O"
' Level 9 - Cross
DATA "0","0","R","R","R","R","0","0"
DATA "0","0","O","B","B","O","0","0"
DATA "Y","Y","Y","B","B","Y","Y","Y"
DATA "Y","Y","Y","B","B","Y","Y","Y"
DATA "0","0","O","O","O","O","0","0"
' Level 10 - Final Challenge
DATA "R","B","O","B","O","B","O","R"
DATA "B","Y","Y","0","0","Y","Y","B"
DATA "O","Y","B","Y","Y","B","Y","O"
DATA "B","Y","Y","0","0","Y","Y","B"
DATA "R","B","O","B","O","B","O","R"

' ---- State ----
DIM INTEGER currentLevel%=1
DIM FLOAT bx!, by!
DIM INTEGER br%
DIM FLOAT vx!, vy!
DIM INTEGER lastAccelTime%
DIM px!, py!, pw%, ph%, pvx!
DIM INTEGER score%, lives%
DIM INTEGER ballLaunched%
DIM INTEGER frames%, t0%
DIM fps$
DIM k$
DIM INTEGER blocks%(BLOCK_ROWS%-1, BLOCK_COLS%-1)
DIM INTEGER totalBlocks%, blocksLeft%
DIM FLOAT hitPos!, angle!
DIM INTEGER explosionActive%, explosionX%, explosionY%, explosionFrame%, explosionColor%
DIM INTEGER oldScore%, oldLives%
DIM INTEGER lastHitRow%, lastHitCol%, hitTimeout%
DIM INTEGER screenshotNum%


' ---- Beeps ----
SUB BeepServe(): PLAY TONE 700,700 : PAUSE 40 : PLAY STOP : END SUB
SUB BeepPaddle(): PLAY TONE 800,800 : PAUSE 20 : PLAY STOP : END SUB
SUB BeepWall(): PLAY TONE 600,600 : PAUSE 20 : PLAY STOP : END SUB
SUB BeepBlock(): PLAY TONE 1200,1200 : PAUSE 25 : PLAY STOP : END SUB
SUB BeepMiss(): PLAY TONE 200,200 : PAUSE 80 : PLAY STOP : END SUB

SUB ResetBall()
  ' Reset ball to paddle position (not launched)
  ballLaunched% = 0
  bx! = px! + pw%/2 - br%
  by! = py! - 2*br% - 2
  IF RND > 0.5 THEN vx! = BALL_SPEED_INIT ELSE vx! = -BALL_SPEED_INIT
  vy! = -BALL_SPEED_INIT
  lastAccelTime% = TIMER
  hitTimeout% = 0
END SUB

SUB DestroyBlock(r%, c%, points%)
  ' Destroy a block with explosion and award points
  LOCAL bx%, by%
  bx% = GetBlockX(c%)
  by% = GetBlockY(r%)
  TriggerExplosion bx%, by%, BLOCK_W%, BLOCK_H%, GetBlockColor(blocks%(r%, c%))
  blocks%(r%, c%) = 0
  blocksLeft% = blocksLeft% - 1
  score% = score% + points%
  EraseBlock r%, c%
END SUB

SUB Draw3DHighlight(x%, y%, w%, h%)
  ' Draw white highlight on top and left edges for 3D effect
  LINE x%, y%, x%+w%-1, y%, , RGB(WHITE)  ' Top edge
  LINE x%, y%, x%, y%+h%-1, , RGB(WHITE)  ' Left edge
END SUB


' ---- Drawing helpers ----
SUB DrawHUD()
  LOCAL s$
  s$ = "L" + STR$(currentLevel%) + " Score " + STR$(score%) + " Lives " + STR$(lives%)
  TEXT 6, 3, s$, "LT", , , COL_TXT%, COL_BG%
  IF fps$ <> "" THEN
    TEXT W%-4, 3, fps$, "RT", , , COL_TXT%, COL_BG%
  END IF
END SUB

SUB DrawPaddleAt(x%, y%)
  ' Draw main paddle
  BOX x%, y%, pw%, ph%, 0, , COL_PAD%
  Draw3DHighlight x%, y%, pw%, ph%
END SUB

SUB DrawBallAt(x%, y%)
  LOCAL cx%, cy%
  cx% = x% + br%
  cy% = y% + br%
  ' Draw main ball
  CIRCLE cx%, cy%, br%, 0, 1.0, , COL_BALL%
  ' Draw small white highlight on top-left for 3D effect
  CIRCLE cx%-2, cy%-2, 1, 0, 1.0, , RGB(WHITE)
END SUB

SUB TriggerExplosion(x%, y%, w%, h%, blockColor%)
  ' Set explosion state - will be drawn in main loop
  explosionActive% = 1
  explosionX% = x% + w%/2
  explosionY% = y% + h%/2
  explosionFrame% = 0
  explosionColor% = blockColor%
END SUB

SUB DrawExplosion()
  LOCAL size%
  IF explosionActive% = 0 THEN EXIT SUB

  ' Draw explosion animation on layer
  size% = (explosionFrame% + 1) * 4

  ' Expanding circle
  CIRCLE explosionX%, explosionY%, size%, 0, 1.0, , explosionColor%

  ' Star burst lines that grow with frame
  LINE explosionX%-size%, explosionY%, explosionX%+size%, explosionY%, , explosionColor%
  LINE explosionX%, explosionY%-size%, explosionX%, explosionY%+size%, , explosionColor%

  IF explosionFrame% > 0 THEN
    LOCAL offset%
    offset% = size% * 0.7
    LINE explosionX%-offset%, explosionY%-offset%, explosionX%+offset%, explosionY%+offset%, , explosionColor%
    LINE explosionX%-offset%, explosionY%+offset%, explosionX%+offset%, explosionY%-offset%, , explosionColor%
  END IF

  ' Advance animation
  explosionFrame% = explosionFrame% + 1
  IF explosionFrame% > 2 THEN
    explosionActive% = 0  ' Animation done
  END IF
END SUB

SUB InitBlocks()
  LOCAL r%, c%, blockChar$, skipRows%, i%
  totalBlocks% = 0
  RESTORE  ' Reset DATA pointer to start

  ' Skip to current level's data
  skipRows% = (currentLevel% - 1) * BLOCK_ROWS% * BLOCK_COLS%
  FOR i% = 1 TO skipRows%
    READ blockChar$
  NEXT

  ' Read current level
  FOR r% = 0 TO BLOCK_ROWS%-1
    FOR c% = 0 TO BLOCK_COLS%-1
      READ blockChar$
      ' Convert character to block type
      SELECT CASE blockChar$
        CASE "R"
          blocks%(r%, c%) = BLOCK_RED%
          totalBlocks% = totalBlocks% + 1
        CASE "O"
          blocks%(r%, c%) = BLOCK_ORANGE%
          totalBlocks% = totalBlocks% + 1
        CASE "Y"
          blocks%(r%, c%) = BLOCK_YELLOW_FULL%
          totalBlocks% = totalBlocks% + 1
        CASE "B"
          blocks%(r%, c%) = BLOCK_BLUE%
          ' Don't count indestructible blocks in total
        CASE ELSE
          blocks%(r%, c%) = 0  ' Empty space
      END SELECT
    NEXT
  NEXT
  blocksLeft% = totalBlocks%
END SUB

FUNCTION GetBlockX(c%) AS INTEGER
  GetBlockX = c% * (BLOCK_W% + BLOCK_GAP%) + BLOCK_GAP%
END FUNCTION

FUNCTION GetBlockY(r%) AS INTEGER
  GetBlockY = BLOCK_TOP% + r% * (BLOCK_H% + BLOCK_GAP% + 3)
END FUNCTION

FUNCTION GetBlockColor(blockType%) AS INTEGER
  SELECT CASE blockType%
    CASE BLOCK_RED%
      GetBlockColor = RGB(RED)
    CASE BLOCK_ORANGE%
      GetBlockColor = RGB(RUST)
    CASE BLOCK_YELLOW_FULL%
      GetBlockColor = RGB(YELLOW)
    CASE BLOCK_YELLOW_DMG%
      GetBlockColor = RGB(BROWN)  ' Darker yellow for damaged
    CASE BLOCK_BLUE%
      GetBlockColor = RGB(BLUE)
    CASE ELSE
      GetBlockColor = RGB(CYAN)
  END SELECT
END FUNCTION

SUB DrawBlocks()
  LOCAL r%, c%, bx%, by%, blockType%
  FOR r% = 0 TO BLOCK_ROWS%-1
    FOR c% = 0 TO BLOCK_COLS%-1
      blockType% = blocks%(r%, c%)
      IF blockType% > 0 THEN
        bx% = GetBlockX(c%)
        by% = GetBlockY(r%)
        BOX bx%, by%, BLOCK_W%, BLOCK_H%, 0, , GetBlockColor(blockType%)
        BOX bx%, by%, BLOCK_W%, BLOCK_H%, 1, COL_BORDER%
        Draw3DHighlight bx%+1, by%+1, BLOCK_W%-2, BLOCK_H%-1
      END IF
    NEXT
  NEXT
END SUB

SUB EraseBlock(r%, c%)
  LOCAL bx%, by%
  bx% = GetBlockX(c%)
  by% = GetBlockY(r%)
  FRAMEBUFFER WRITE F
  BOX bx%, by%, BLOCK_W%, BLOCK_H%, 0, , COL_BG%
  FRAMEBUFFER WRITE L  ' Restore to layer
END SUB

FUNCTION CheckBlockCollision(ballX%, ballY%, ballR%) AS INTEGER
  LOCAL r%, c%, bx%, by%, bx2%, by2%, blockType%
  LOCAL ballLeft%, ballRight%, ballTop%, ballBot%

  ballLeft% = ballX%
  ballRight% = ballX% + 2*ballR%
  ballTop% = ballY%
  ballBot% = ballY% + 2*ballR%

  ' Decrement hit timeout
  IF hitTimeout% > 0 THEN hitTimeout% = hitTimeout% - 1

  FOR r% = 0 TO BLOCK_ROWS%-1
    FOR c% = 0 TO BLOCK_COLS%-1
      blockType% = blocks%(r%, c%)
      IF blockType% > 0 THEN
        bx% = GetBlockX(c%)
        by% = GetBlockY(r%)
        bx2% = bx% + BLOCK_W%
        by2% = by% + BLOCK_H%

        ' AABB collision test
        IF ballRight% >= bx% AND ballLeft% <= bx2% AND ballBot% >= by% AND ballTop% <= by2% THEN
          ' Check if this is the same block hit recently
          IF hitTimeout% > 0 AND r% = lastHitRow% AND c% = lastHitCol% THEN
            ' Still in timeout - ignore this block completely, check others
            ' Don't return, just continue to next block
          ELSE
            ' Record this hit for timeout
            lastHitRow% = r%
            lastHitCol% = c%
            hitTimeout% = 15
          ' Handle different block types
          IF blockType% = BLOCK_BLUE% THEN
            ' Blue block - indestructible, just bounce
            CheckBlockCollision = 1
            EXIT FUNCTION
          ELSE IF blockType% = BLOCK_YELLOW_FULL% THEN
            ' Yellow block at full health - damage it, no points yet
            blocks%(r%, c%) = BLOCK_YELLOW_DMG%
            FRAMEBUFFER WRITE F
            BOX bx%, by%, BLOCK_W%, BLOCK_H%, 0, , GetBlockColor(BLOCK_YELLOW_DMG%)
            BOX bx%, by%, BLOCK_W%, BLOCK_H%, 1, COL_BORDER%
            Draw3DHighlight bx%+1, by%+1, BLOCK_W%-2, BLOCK_H%-1
            FRAMEBUFFER WRITE L
          ELSE IF blockType% = BLOCK_YELLOW_DMG% THEN
            ' Yellow block damaged - destroy it, award 10 points
            DestroyBlock r%, c%, 10
          ELSE IF blockType% = BLOCK_ORANGE% THEN
            ' Orange block - destroy, award 20 points
            DestroyBlock r%, c%, 20
          ELSE IF blockType% = BLOCK_RED% THEN
            ' Red block - destroy, award 30 points
            DestroyBlock r%, c%, 30
          END IF
          CheckBlockCollision = 1
          EXIT FUNCTION
          END IF
        END IF
      END IF
    NEXT
  NEXT
  CheckBlockCollision = 0
END FUNCTION

' ---- Init ----
pw% = W% \ 6 : IF pw% < 30 THEN pw% = 30  ' (no MAX(); clamp via IF)
ph% = 6
px! = (W% - pw%) / 2
py! = H% - (ph% + 6)
pvx! = 0

br% = BRADIUS
bx! = W% \ 2 : by! = H% \ 2
vx! = BALL_SPEED_INIT
vy! = -BALL_SPEED_INIT

score% = 0 : lives% = 3
oldScore% = 0 : oldLives% = 3
ballLaunched% = 0
explosionActive% = 0
hitTimeout% = 0
lastHitRow% = -1
lastHitCol% = -1
screenshotNum% = 0

frames% = 0 : t0% = TIMER
fps$ = ""
lastAccelTime% = TIMER

InitBlocks

' ---- Setup Framebuffers ----
FRAMEBUFFER CREATE           ' Create framebuffer F
FRAMEBUFFER LAYER RGB(BLACK) ' Create layer L with black as transparent

' Draw static background to F
FRAMEBUFFER WRITE F
CLS COL_BG%
DrawBlocks

' Draw initial sprites to layer L
FRAMEBUFFER WRITE L
CLS RGB(BLACK)  ' Clear layer with transparent color
DrawPaddleAt INT(px!), INT(py!)
DrawBallAt INT(bx!), INT(by!)

' Draw HUD to framebuffer F
FRAMEBUFFER WRITE F
DrawHUD

' Start timed continuous merge (updates at TICK_MS rate)
FRAMEBUFFER MERGE RGB(BLACK), R, TICK_MS

BeepServe

' ---- Main loop ----
DO
  ' INPUT (Left=130, Right=131, ESC=27, Space=32, P/p=80/112; 1..8 tones)
  k$ = INKEY$
  IF k$ <> "" THEN
    SELECT CASE ASC(k$)
      CASE 130: pvx! = pvx! - PAD_ACCEL
      CASE 131: pvx! = pvx! + PAD_ACCEL
      CASE  32: IF ballLaunched% = 0 THEN ballLaunched% = 1 : BeepServe
      CASE  27: EXIT DO
      CASE 80, 112: ' P or p key - screenshot
        ' Pause rendering and capture full scene
        FRAMEBUFFER MERGE RGB(BLACK), A  ' Abort continuous merge
        PAUSE 50
        FRAMEBUFFER WRITE N
        CLS COL_BG%
        DrawBlocks
        DrawHUD
        DrawPaddleAt INT(px!), INT(py!)
        DrawBallAt INT(bx!), INT(by!)
        IF ballLaunched% = 0 THEN
          TEXT W%\2, H%\2, "Hit SPACE to start", "CT", , , COL_TXT%, RGB(BLACK)
        END IF
        PAUSE 50
        screenshotNum% = screenshotNum% + 1
        SAVE IMAGE "screen" + STR$(screenshotNum%) + ".bmp"
        PAUSE 50
        FRAMEBUFFER WRITE L
        FRAMEBUFFER MERGE RGB(BLACK), R, TICK_MS  ' Resume continuous merge
        PLAY TONE 1200,1200 : PAUSE 30 : PLAY STOP  ' Confirmation beep
      CASE  49 TO 56
        PLAY TONE 220 * (2 ^ ((ASC(k$)-48)/12.0)), 0 : PAUSE 60 : PLAY STOP
    END SELECT
  ENDIF

  ' ---- Paddle physics ----
  pvx! = pvx! * PAD_DECAY
  IF pvx! >  PAD_MAX THEN pvx! =  PAD_MAX
  IF pvx! < -PAD_MAX THEN pvx! = -PAD_MAX
  px! = px! + pvx!
  IF px! < 0 THEN px! = 0 : IF pvx! < 0 THEN pvx! = 0
  IF px! > (W% - pw%) THEN px! = W% - pw% : IF pvx! > 0 THEN pvx! = 0

  ' ---- Ball physics ----
  IF ballLaunched% = 0 THEN
    ' Ball follows paddle until launched
    bx! = px! + pw%/2 - br%
    by! = py! - 2*br% - 2
  ELSE
    ' Gradually increase speed over time (once per second)
    IF TIMER - lastAccelTime% >= 1000 THEN
      IF vy! > 0 THEN
        vy! = vy! + BALL_SPEED_ACCEL_PER_SEC
      ELSE
        vy! = vy! - BALL_SPEED_ACCEL_PER_SEC
      END IF
      lastAccelTime% = lastAccelTime% + 1000
    END IF

    bx! = bx! + vx!
    by! = by! + vy!
  END IF

  ' Elastic wall bounces
  IF INT(bx!) < 0 THEN
    bx! = 0
    vx! = -vx!
    hitTimeout% = 0
    BeepWall
  END IF
  IF INT(bx!) > W% - 2*br% THEN
    bx! = W% - 2*br%
    vx! = -vx!
    hitTimeout% = 0
    BeepWall
  END IF
  IF INT(by!) < HUDH% + 1 THEN
    by! = HUDH% + 1
    vy! = -vy!
    hitTimeout% = 0
    BeepWall
  END IF

  ' ---- Block collision (elastic) ----
  IF ballLaunched% = 1 AND CheckBlockCollision(INT(bx!), INT(by!), br%) = 1 THEN
    vy! = -vy!
    BeepBlock
  END IF

  ' ---- Paddle collision (angle variation based on hit position) ----
  IF ballLaunched% = 1 AND INT(by!) + 2*br% >= INT(py!) AND INT(by!) <= INT(py!) + ph% AND INT(bx!) + 2*br% >= INT(px!) AND INT(bx!) <= INT(px!) + pw% THEN
    by! = INT(py!) - 2*br%
    vy! = -vy!
    hitTimeout% = 0

    ' Calculate where on paddle ball hit (0=left edge, 1=right edge, 0.5=center)
    hitPos! = (bx! + br% - px!) / pw%
    IF hitPos! < 0 THEN hitPos! = 0
    IF hitPos! > 1 THEN hitPos! = 1

    ' Adjust horizontal velocity based on hit position
    ' Center hits = straighter, edge hits = sharper angle
    angle! = (hitPos! - 0.5) * 5.0  ' Range: -2.5 to +2.5
    vx! = vx! + angle! + pvx! * PADDLE_KICK

    score% = score% + 1
    BeepPaddle
  ENDIF

  ' ---- Miss (lose a life) ----
  IF ballLaunched% = 1 AND INT(by!) > H% - 2*br% THEN
    lives% = lives% - 1
    BeepMiss

    IF lives% > 0 THEN
      ' Reset ball to paddle (not launched)
      ResetBall
      BeepServe
    ELSE
      ' Game over
      FRAMEBUFFER MERGE RGB(BLACK), A
      FRAMEBUFFER CLOSE
      FRAMEBUFFER WRITE N
      CLS COL_BG%
      PRINT "GAME OVER!  Score="; score%
      END
    END IF
  ENDIF

  ' ---- Level complete / Win condition ----
  IF blocksLeft% = 0 THEN
    IF currentLevel% < LEVELS% THEN
      ' Advance to next level
      currentLevel% = currentLevel% + 1
      ResetBall

      ' Redraw static background with new level
      FRAMEBUFFER WRITE F
      CLS COL_BG%
      InitBlocks
      DrawBlocks
      DrawHUD
      oldScore% = score%  ' Force HUD update on next frame
      oldLives% = lives%

      BeepServe
    ELSE
      ' All levels complete!
      FRAMEBUFFER MERGE RGB(BLACK), A
      FRAMEBUFFER CLOSE
      FRAMEBUFFER WRITE N
      CLS COL_BG%
      PRINT "YOU WIN ALL LEVELS!  Score="; score%; "  Lives: "; lives%
      END
    END IF
  END IF

  ' ---- Redraw layer with new sprite positions ----
  FRAMEBUFFER SYNC
  FRAMEBUFFER WRITE L
  CLS RGB(BLACK)    ' Clear layer with transparent color
  DrawPaddleAt INT(px!), INT(py!)
  DrawBallAt INT(bx!), INT(by!)
  DrawExplosion     ' Draw explosion animation if active

  ' Show start message when ball not launched
  IF ballLaunched% = 0 THEN
    TEXT W%\2, H%\2, "Hit SPACE to start", "CT", , , COL_TXT%, RGB(BLACK)
  END IF

  ' ---- Update HUD only on score/lives change ----
  IF score% <> oldScore% OR lives% <> oldLives% THEN
    oldScore% = score%
    oldLives% = lives%
    FRAMEBUFFER WRITE F
    DrawHUD
  END IF

  ' ---- Update FPS display ----
  frames% = frames% + 1
  IF TIMER - t0% >= 1000 THEN
    fps$ = STR$(frames%) + " FPS"
    frames% = 0
    t0% = TIMER
    FRAMEBUFFER WRITE F
    DrawHUD
  END IF

  ' No PAUSE needed - continuous merge handles timing
LOOP

' ---- Cleanup ----
FRAMEBUFFER MERGE RGB(BLACK), A  ' Abort continuous merge
FRAMEBUFFER CLOSE
FRAMEBUFFER WRITE N  ' Back to normal screen
CLS COL_BG%
PRINT "Thanks for playing!  Final Score: "; score%
END