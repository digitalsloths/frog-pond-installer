#!/usr/bin/env python3
"""Frog Pond V8: swipe-to-jump, Frog Hop, power key, and reliable personalization."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); paths=list(root.rglob("*.ino"))
assert len(paths)==1,paths
path=paths[0]; s=path.read_text()
def replace(a,b,why):
 global s
 n=s.count(a)
 if n!=1: raise RuntimeError(f"{why}: expected 1 instance, got {n}")
 s=s.replace(a,b,1)
def function(name,body):
 global s
 start=s.find(name)
 if start<0:raise RuntimeError("Missing function "+name)
 pos=s.find('{',start);depth=0
 for i in range(pos,len(s)):
  if s[i]=='{':depth+=1
  elif s[i]=='}':
   depth-=1
   if depth==0:
    s=s[:start]+body+s[i+1:];return
 raise RuntimeError("Malformed braces "+name)
replace('#include "frog_croak_audio.h"','#include "frog_croak_audio.h"\n#include "froghop_sprites.h"', 'frog hop sprites')
replace('enum Screen : uint8_t { FACE, APPS, CLOCK, COUNTER_APP, TIMER_APP, GAMES, PERSONALIZE, SETTINGS, APPS_HUB };',
'enum Screen : uint8_t { FACE, APPS, CLOCK, COUNTER_APP, TIMER_APP, GAMES, PERSONALIZE, SETTINGS, APPS_HUB, FROG_HOP };',
'add Frog Hop screen')
replace('uint8_t selectedFrogColor = 0, selectedFrogHat = 0;','uint8_t selectedFrogColor = 0, selectedFrogHat = 0;', 'style selection anchor') if False else None
# Persistent game state, PWM-free CO5300 brightness and TCA9554 PWR key.
needle='Screen screen = FACE;'
replace(needle,needle+'''
uint32_t frogHopHigh = 0, frogHopScore = 0, frogHopLastMs = 0;
float frogHopHeight = 0.0f, frogHopVelocity = 0.0f, frogHopObstacle = 500.0f;
bool frogHopRunning = false, frogHopGameOver = false, frogHopAirborne = false;
bool frogSoftwareSleep = false, frogDimmed = false;
bool frogPowerWasPressed = false, frogPowerLongHandled = false;
uint32_t frogPowerPressedAt = 0, frogPowerPolledAt = 0;
constexpr uint8_t FROG_POWER_EXPANDER_ADDR = 0x20;
constexpr uint8_t FROG_POWER_INPUT_REG = 0x00;
constexpr uint8_t FROG_POWER_BIT = 4;
constexpr uint32_t FROG_POWER_LONG_MS = 1750;
void saveFrogState() {
  prefs.putUInt("frogSteps",frogSteps);
  prefs.putUChar("frogColor",selectedFrogColor);
  prefs.putUChar("frogHat",selectedFrogHat);
  prefs.putUInt("frogHopBest",frogHopHigh);
}
bool frogPowerKeyIsPressed() {
  Wire.beginTransmission(FROG_POWER_EXPANDER_ADDR);
  Wire.write(FROG_POWER_INPUT_REG);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(FROG_POWER_EXPANDER_ADDR,(uint8_t)1) != 1) return false;
  return (Wire.read() & (1U << FROG_POWER_BIT)) != 0;
}
void pollFrogPower(uint32_t now) {
  if ((uint32_t)(now-frogPowerPolledAt)<40) return;
  frogPowerPolledAt=now;
  bool down = frogPowerKeyIsPressed();
  if (down && !frogPowerWasPressed) {
    frogPowerPressedAt=now;
    frogPowerLongHandled=false;
  }
  if (down && !frogPowerLongHandled && (uint32_t)(now-frogPowerPressedAt)>=FROG_POWER_LONG_MS) {
    frogPowerLongHandled=true;
    saveFrogState();
    frogSoftwareSleep=true;
    panel->setBrightness(0);
    Serial.println("FROG: PWR long press -> saved standby");
  }
  if (!down && frogPowerWasPressed && !frogPowerLongHandled) {
    if (frogSoftwareSleep) {
      frogSoftwareSleep=false;
      frogDimmed=false;
      panel->setBrightness(110);
      Serial.println("FROG: PWR short press -> wake");
    } else {
      frogDimmed=!frogDimmed;
      panel->setBrightness(frogDimmed?28:110);
      Serial.printf("FROG: display %s\\n",frogDimmed?"dimmed":"normal");
    }
  }
  frogPowerWasPressed=down;
}
void startFrogHop(uint32_t now) {
  frogHopRunning=true; frogHopGameOver=false;
  frogHopScore=0;frogHopHeight=0;frogHopVelocity=0;
  frogHopObstacle=490.0f;frogHopAirborne=false;frogHopLastMs=now;
}
void frogHopJump() {
  if (!frogHopRunning || frogHopAirborne) return;
  frogHopAirborne=true;frogHopVelocity=11.5f;
}
void updateFrogHop(uint32_t now) {
  if (!frogHopRunning) return;
  if (!frogHopLastMs) {frogHopLastMs=now;return;}
  float dt=(now-frogHopLastMs)/16.6667f;
  frogHopLastMs=now;
  dt=constrain(dt,0.0f,2.5f);
  frogHopHeight+=frogHopVelocity*dt;
  frogHopVelocity-=0.64f*dt;
  if (frogHopHeight<=0) {frogHopHeight=0; frogHopVelocity=0;frogHopAirborne=false;}
  frogHopObstacle-=(3.7f+min(frogHopScore/80.0f,4.5f))*dt;
  if (frogHopObstacle < -35) {frogHopObstacle=470+random(0,95);frogHopScore+=10;}
  if (frogHopObstacle<168 && frogHopObstacle+30>92 && frogHopHeight<43) {
    frogHopRunning=false;frogHopGameOver=true;
    if(frogHopScore>frogHopHigh){frogHopHigh=frogHopScore;prefs.putUInt("frogHopBest",frogHopHigh);}
  }
}
void drawFrogHopCharacter(int which,int left,int top,int scale) {
  const uint8_t *px=FROGHOP_DATA[which];
  for(int yy=0;yy<FROGHOP_H;yy++){
    int xx=0;
    while(xx<FROGHOP_W){
      uint8_t c=pgm_read_byte(px+yy*FROGHOP_W+xx);
      if(!c){++xx;continue;}
      int first=xx++;
      while(xx<FROGHOP_W && pgm_read_byte(px+yy*FROGHOP_W+xx)==c)xx++;
      uint16_t rgb=pgm_read_word(FROGHOP_PALETTE+c);
      gfx->fillRect(left+first*scale,top+yy*scale,(xx-first)*scale,scale,rgb);
    }
  }
}
void drawFrogHop(uint32_t now) {
  gfx->fillScreen(0xCFDF);
  gfx->fillRect(0,345,466,121,0x5BE6);
  gfx->fillRect(0,343,466,5,0x33E4);
  for(int i=0;i<6;i++) {
    int x=55+i*77;
    gfx->drawFastHLine(x,362+(i%2)*18,18,0x2AC5);
  }
  centered("FROG HOP",233,37,3,0x03C0);
  centered("SCORE "+String(frogHopScore),122,84,2,0x0320);
  centered("BEST "+String(frogHopHigh),339,84,2,0x0320);
  if (!frogHopGameOver) {
    int frame=frogHopAirborne ? ((frogHopHeight>45)?7:6):((now/130)%6);
    drawFrogHopCharacter(frame,73,232-(int)frogHopHeight,2);
    int ox=(int)frogHopObstacle;
    gfx->fillRoundRect(ox,304,28,40,5,0x61C6);
    gfx->fillRect(ox+4,298,20,10,0x4243);
  }
  if(!frogHopRunning) {
    gfx->fillRoundRect(88,153,290,108,16,0x2105);
    centered(frogHopGameOver?"GAME OVER":"READY TO HOP?",233,170,2,WHITE);
    centered("TAP TO START",233,211,2,0xAFD0);
  }
  centered("TAP TO JUMP - SWIPE RIGHT TO EXIT",233,410,1,0x1320);
}
''','V8 power and game logic')
# Power/state functions are declared above globals frogSteps/selectedFrogColor/prefs, so place after those declarations instead.
start=s.index('void saveFrogState() {')
end=s.index('void startFrogHop(',start)
powerHelpers=s[start:end]
s=s[:start]+s[end:]
anchor='uint32_t frogSteps = 0; // Physical walking steps from QMI8658 accelerometer.'
replace(anchor,anchor+'\n'+powerHelpers,'power helper placement')
# Loop power guard, needed to preserve all NVS and avoid drawing in standby
replace('  pollPhysicalSteps(now);\n  pollTouch(now);',
'''  pollFrogPower(now);
  if (frogSoftwareSleep) { delay(50);return; }
  pollPhysicalSteps(now);
  pollTouch(now);
  if (screen == FROG_HOP) updateFrogHop(now);''',
'poll power and update runner')
# Avoid reading input during device power state transitions.
replace('  if (uploadMode) uploadServer.handleClient();','  if (uploadMode) uploadServer.handleClient();','unchanged') if False else None
# Swipe up on Home replaces the double-tap gesture.
a=s.index('    frogDoubleTapHandled = false;',s.index('void pollTouch('))
b=s.index('  } else if (down && fingerDown) {',a)
s=s[:a]+'''    frogDoubleTapHandled = false;
''' + s[b:]
replace('''    } else if (abs(dx) >= SWIPE_THRESHOLD && abs(dx) > abs(dy) * 1.3f) {''',
'''    } else if (screen == FACE && dy <= -SWIPE_THRESHOLD &&
               abs(dy) > abs(dx) * 1.2f) {
      frogTapPending=false;
      frogCurrentAction=FROG_JUMP_ACTION;
      frogActionAt=now;
      frogActionNumber++;
      frogLastRenderedFrame=-1;
      Serial.println("FROG: swipe up -> jump");
    } else if (abs(dx) >= SWIPE_THRESHOLD && abs(dx) > abs(dy) * 1.3f) {''',
'swipe up before horizontal navigation')
# Remove redundant queued/double-tap handling in center frog reaction.
replace('    // First release: hold for a possible second press.','    // A tap croaks; upward swipe performs jump.', 'tap semantics')
# Reserve screen GAMES for Frog Hop selector.
function('void drawEmptyGames() {','''void drawEmptyGames() {
  gfx->fillScreen(0x0883);
  centered("GAMES",233,70,3,WHITE);
  gfx->fillRoundRect(97,167,272,118,20,0x3C6A);
  gfx->drawRoundRect(97,167,272,118,20,0xAFF6);
  centered("FROG HOP",233,188,3,WHITE);
  centered("TAP TO PLAY",233,237,1,0xBFF9);
  centered("SWIPE RIGHT TO RETURN",233,419,1,GRAY);
}''')
replace('''  } else if (screen == SETTINGS || screen == GAMES) {
    // Intentional blank placeholder pages: swipe right to return.''',
'''  } else if (screen == GAMES) {
    if (inside(x,y,95,160,278,135)) {
      openScreen(FROG_HOP);
      frogHopRunning=false;
      frogHopGameOver=false;
      frogHopScore=0;
      frogHopLastMs=0;
    }
  } else if (screen == FROG_HOP) {
    if(!frogHopRunning) startFrogHop(millis());
    else frogHopJump();
  } else if (screen == SETTINGS) {
    // Settings placeholder; swipe right to return.''',
'Frog Hop launch and tap gameplay')
replace('''  } else if (screen == GAMES || screen == SETTINGS || screen == APPS_HUB) {
    if (direction > 0) openScreen(APPS);
''','''  } else if (screen == FROG_HOP) {
    if (direction > 0) openScreen(GAMES);
  } else if (screen == GAMES || screen == SETTINGS || screen == APPS_HUB) {
    if (direction > 0) openScreen(APPS);
''','Frog Hop exit swipe')
replace('''  } else if (screen == GAMES && selectedGame < 0) {''',
'''  } else if (screen == FROG_HOP) {
    interval=65;
    redraw=changedScreen || now-prevFrameAt>=interval;
  } else if (screen == GAMES && selectedGame < 0) {''',
'runner scheduled drawing') if '  } else if (screen == GAMES && selectedGame < 0) {' in s else None
# V7 renderer has GAMES in static screen branch, so above condition must be prior to static branch.
replace('''  } else if (screen == APPS || screen == SETTINGS || screen == APPS_HUB || screen == GAMES) {''',
'''  } else if (screen == FROG_HOP) {
    interval=65;
    redraw=changedScreen || now-prevFrameAt>=interval;
  } else if (screen == APPS || screen == SETTINGS || screen == APPS_HUB || screen == GAMES) {''',
'runner redraw branch')
replace('''    else if (screen == GAMES) drawEmptyGames();''','''    else if (screen == GAMES) drawEmptyGames();
    else if (screen == FROG_HOP) drawFrogHop(now);''',
'game rendering')
# Clear input accident from V7: prevent a swipe from also firing the tap.
# Replace personalize input with trigger on first DOWN, handle once per contact.
a=s.index('  } else if (screen == PERSONALIZE) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == GAMES) {',a)
s=s[:a]+'''  } else if (screen == PERSONALIZE) {
    // Tap bounds follow the visible arrows; Save is not rate-limited.
    if (inside(x,y,55,190,100,80)) previewFrogColor=(previewFrogColor+4)%5;
    else if (inside(x,y,310,190,100,80)) previewFrogColor=(previewFrogColor+1)%5;
    else if (inside(x,y,55,292,100,84)) previewFrogHat=(previewFrogHat+6)%7;
    else if (inside(x,y,310,292,100,84)) previewFrogHat=(previewFrogHat+1)%7;
    else if (inside(x,y,145,380,176,58)) {
      selectedFrogColor=previewFrogColor;
      selectedFrogHat=previewFrogHat;
      size_t c=prefs.putUChar("frogColor",selectedFrogColor);
      size_t h=prefs.putUChar("frogHat",selectedFrogHat);
      personalizeSavedUntil=millis()+2400;
      personalizeDirty=true;
      Serial.printf("FROG STYLE SAVE color=%u hat=%u bytes=%u,%u\\n",
                    selectedFrogColor,selectedFrogHat,(unsigned)c,(unsigned)h);
      return;
    } else return;
    personalizeDirty=true;
    personalizeSavedUntil=0;
    Serial.printf("FROG STYLE preview color=%u hat=%u\\n",
                  previewFrogColor,previewFrogHat);
''' + s[b:]
# In case source contains second GAMES branch preceding settings (as V7), handle without duplicate.
# Ensure a stable call in UI, also draw a full preview plus visible centered hat icon.
function('void drawPersonalize() {','''void drawPersonalize() {
  gfx->fillScreen(0x0883);
  centered("Personalize your frog",233,32,2,WHITE);
  drawFrogSpriteStyled(0,185,75,4,previewFrogColor,previewFrogHat);
  centered("Frog Color",233,171,2,0xB737);
  gfx->fillRoundRect(65,197,78,53,12,0x2C6A);
  gfx->fillRoundRect(323,197,78,53,12,0x2C6A);
  centered("<",103,205,3,WHITE);
  centered(">",362,205,3,WHITE);
  gfx->fillRoundRect(190,204,86,43,11,frogColorSwatches[previewFrogColor]);
  gfx->drawRoundRect(190,204,86,43,11,WHITE);
  centered(frogColorNames[previewFrogColor],233,253,2,WHITE);
  centered("Accessories",233,275,2,0xB737);
  gfx->fillRoundRect(65,301,78,50,12,0x2C6A);
  gfx->fillRoundRect(323,301,78,50,12,0x2C6A);
  centered("<",103,309,3,WHITE);
  centered(">",362,309,3,WHITE);
  if(previewFrogHat==0) centered("NO HAT",233,324,1,GRAY);
  else drawFrogHat(previewFrogHat,216,300,3);
  centered(frogHatNames[previewFrogHat],233,359,2,WHITE);
  centeredButton(150,385,166,48,
    personalizeSavedUntil>millis()?"SAVED!":"SAVE",GREEN);
  if(personalizeSavedUntil>millis()) centered("SAVED TO DEVICE",233,438,1,WHITE);
  else centered("SWIPE RIGHT TO RETURN",233,438,1,GRAY);
}''')
# Ensure saved status refresh after 2.4 seconds
replace('''  } else if (screen == PERSONALIZE) {
    redraw = changedScreen || personalizeDirty || (personalizeSavedUntil > 0 && now >= personalizeSavedUntil);''',
'''  } else if (screen == PERSONALIZE) {
    redraw = changedScreen || personalizeDirty || (personalizeSavedUntil > 0 && now >= personalizeSavedUntil);''',
'unmodified') if False else None
# Persist high score loaded on boot
replace('  frogSteps = prefs.getUInt("frogSteps", 0);',
'''  frogHopHigh = prefs.getUInt("frogHopBest",0);
  frogSteps = prefs.getUInt("frogSteps", 0);''',
'game high-score load')
# Stop old double tap simulation; single tap still delayed slightly but always croaks.
replace('constexpr uint32_t FROG_DOUBLE_TAP_MS = 485;','constexpr uint32_t FROG_DOUBLE_TAP_MS = 120;', 'single-tap confirmation delay')
path.write_text(s)
print("V8 patch completed",path,len(s))
