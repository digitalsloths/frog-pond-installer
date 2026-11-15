#!/usr/bin/env python3
"""Apply Frog Pond V7 behavior and UI fixes after tools/patch_v6.py."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); sketches=list(root.rglob("*.ino"))
assert len(sketches)==1,sketches
path=sketches[0]; s=path.read_text()
def replace(old,new,desc):
    global s
    count=s.count(old)
    if count!=1:raise RuntimeError(f"{desc}: expected 1 match, found {count}")
    s=s.replace(old,new,1)
def function(name,new):
    global s
    a=s.find(name)
    if a<0:raise RuntimeError(f"Function not found {name}")
    br=s.find("{",a)
    depth=0
    for i in range(br,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:
                s=s[:a]+new+s[i+1:];return
    raise RuntimeError("Bad function braces "+name)
# Remove home HUD, preserve step counter variable and sensor sampling.
start=s.index('  // The physical display is circular: keep the entire counter')
end=s.index('\n}',start)
s=s[:start]+s[end:]
# Audio enabled by this patch; codec implementation is supplied from Waveshare's Arduino example.
replace('#include "frog_custom.h"','#include "frog_custom.h"\n#include "frog_croak_audio.h"\n#include "ESP_I2S.h"\n#include "es8311.h"', "audio includes")
replace('constexpr uint32_t FROG_DOUBLE_TAP_MS = 330;','constexpr uint32_t FROG_DOUBLE_TAP_MS = 485;\nbool frogDoubleTapHandled = false;',"double-tap window")
# Explicitly make the action clock start on second touch down, not a second touch release.
replace('''    fingerDown = true; downX = lastX = x; downY = lastY = y; downAt = now;''','''    fingerDown = true; downX = lastX = x; downY = lastY = y; downAt = now;
    frogDoubleTapHandled = false;
    const bool onFrog = screen == FACE && x >= 172 && x <= 293 && y >= 169 && y <= 305;
    if (onFrog && frogTapPending &&
        (uint32_t)(now-frogTapPendingAt) <= FROG_DOUBLE_TAP_MS) {
      frogTapPending = false;
      frogDoubleTapHandled = true; // second release is ignored
      frogCurrentAction = FROG_JUMP_ACTION;
      frogActionAt = now;
      frogActionNumber++;
      frogLastRenderedFrame = -1;
      Serial.println("FROG: double tap -> jump");
    }''',"detect second touch on press")
replace('''    } else if (abs(dx) < 65 && abs(dy) < 65 && now - downAt < 1300) {
      tapped(downX, downY);
    }''','''    } else if (!frogDoubleTapHandled && abs(dx) < 45 && abs(dy) < 45
               && now - downAt < 900) {
      tapped(downX, downY);
    }
    frogDoubleTapHandled = false;''',"ignore second tap release")
# Correct swipe map: right finger movement -> APPS hub, left -> PERSONALIZE.
function('void changeScreen(int direction) {','''void changeScreen(int direction) {
  if (screen == FACE) {
    if (direction < 0) openScreen(PERSONALIZE); // finger moves left
    else if (direction > 0) openScreen(APPS);  // finger moves right
  } else if (screen == PERSONALIZE) {
    if (direction > 0) openScreen(FACE);
  } else if (screen == APPS) {
    if (direction < 0) openScreen(FACE);
  } else if (screen == GAMES || screen == SETTINGS || screen == APPS_HUB) {
    if (direction > 0) openScreen(APPS);
  } else if (screen == CLOCK || screen == TIMER_APP || screen == COUNTER_APP) {
    if (direction > 0) openScreen(APPS_HUB);
  }
}''')
replace('enum Screen : uint8_t { FACE, APPS, CLOCK, COUNTER_APP, TIMER_APP, GAMES, PERSONALIZE, SETTINGS };',
        'enum Screen : uint8_t { FACE, APPS, CLOCK, COUNTER_APP, TIMER_APP, GAMES, PERSONALIZE, SETTINGS, APPS_HUB };',
        "apps hub screen enum")
# Frog-only response in central sprite; margin taps go to pages.
a=s.index('  if (screen == FACE) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == APPS) {',a)
s=s[:a]+'''  if (screen == FACE) {
    sleeping = false;
    if (x <= 158) { frogTapPending = false; openScreen(APPS); return; }
    if (x >= 308) { frogTapPending = false; openScreen(PERSONALIZE); return; }
    if (x < 172 || x > 293 || y < 169 || y > 305) return;
    // First release: hold for a possible second press.
    frogTapPending = true;
    frogTapPendingAt = millis();
    Serial.println("FROG: single tap queued");
''' + s[b:]
# Games/settings/apps hub selectors in current APPS menu
a=s.index('  } else if (screen == APPS) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == PERSONALIZE) {',a)
s=s[:a]+'''  } else if (screen == APPS) {
    if (inside(x,y,105,138,256,73)) openScreen(GAMES);
    else if (inside(x,y,105,230,256,73)) openScreen(SETTINGS);
    else if (inside(x,y,105,322,256,73)) openScreen(APPS_HUB);
  } else if (screen == APPS_HUB) {
    if (inside(x,y,105,160,256,92)) openScreen(CLOCK);
    else if (inside(x,y,105,276,256,92)) openScreen(TIMER_APP);
''' + s[b:]
# Personalization taps; no delay-related double actions, use release-state debounce.
a=s.index('  } else if (screen == PERSONALIZE) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == SETTINGS) {',a)
s=s[:a]+'''  } else if (screen == PERSONALIZE) {
    static uint32_t lastPickerAt = 0;
    const uint32_t t = millis();
    // Only throttle arrows, never block SAVE.
    if (inside(x,y,68,195,79,63) || inside(x,y,318,195,80,63) ||
        inside(x,y,55,300,94,71) || inside(x,y,317,300,94,71)) {
      if (lastPickerAt && (uint32_t)(t-lastPickerAt) < 180) return;
      lastPickerAt = t;
      if (inside(x,y,68,195,79,63)) previewFrogColor = (previewFrogColor+4)%5;
      else if (inside(x,y,318,195,80,63)) previewFrogColor = (previewFrogColor+1)%5;
      else if (inside(x,y,55,300,94,71)) previewFrogHat = (previewFrogHat+6)%7;
      else if (inside(x,y,317,300,94,71)) previewFrogHat = (previewFrogHat+1)%7;
      personalizeDirty = true;
      personalizeSavedUntil = 0;
      Serial.printf("FROG PREVIEW: color=%u hat=%u\\n",previewFrogColor,previewFrogHat);
    } else if (inside(x,y,148,376,169,62)) {
      selectedFrogColor = previewFrogColor;
      selectedFrogHat = previewFrogHat;
      size_t ca = prefs.putUChar("frogColor", selectedFrogColor);
      size_t ha = prefs.putUChar("frogHat", selectedFrogHat);
      personalizeSavedUntil = t+1800;
      personalizeDirty = true;
      Serial.printf("FROG SAVE: color=%u hat=%u bytes=%u,%u\\n",
                     selectedFrogColor,selectedFrogHat,(unsigned)ca,(unsigned)ha);
    }
''' + s[b:]
# Empty screen tap: no old buttons / game input from GAMES.
a=s.index('  } else if (screen == SETTINGS) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == CLOCK) {',a)
s=s[:a]+'''  } else if (screen == SETTINGS || screen == GAMES) {
    // Intentional blank placeholder pages: swipe right to return.
''' + s[b:]
replace('  } else if (screen == GAMES) gameTap(x,y);','  }','disable old game touch')
function('void drawAppMenu() {','''void drawAppMenu() {
  gfx->fillScreen(0x0863);
  centered("FROG POND",233,53,3,0xCF57);
  centered("STEPS",233,113,2,WHITE);
  centered(String(frogSteps),233,143,3,0xCFFF);
  const char* labels[] = {"GAMES","SETTINGS","APPS"};
  const int yy[] = {138,230,322};
  for(int i=0;i<3;i++) {
    gfx->fillRoundRect(105,yy[i],256,73,15,0x2467);
    gfx->drawRoundRect(105,yy[i],256,73,15,0x8F36);
    centered(labels[i],233,yy[i]+22,2,WHITE);
  }
}''')
# Note: steps placement y=113 overlaps games button (starts y138) only if 3x text from 143. Move larger step UI compact.
replace('centered(String(frogSteps),233,143,3,0xCFFF);','centered(String(frogSteps),233,105,3,0xCFFF);', "step position")
replace('  centered("STEPS",233,113,2,WHITE);','  centered("STEPS",233,78,1,WHITE);', "step label")
function('void drawSettingsMenu() {','''void drawSettingsMenu() {
  gfx->fillScreen(0x0863);
  centered("SETTINGS",233,83,3,WHITE);
  centered("COMING SOON",233,224,2,0x8F36);
  centered("SWIPE RIGHT TO RETURN",233,425,1,GRAY);
}
void drawEmptyGames() {
  gfx->fillScreen(0x0863);
  centered("GAMES",233,83,3,WHITE);
  centered("COMING SOON",233,224,2,0x8F36);
  centered("SWIPE RIGHT TO RETURN",233,425,1,GRAY);
}
void drawAppsHub() {
  gfx->fillScreen(0x0863);
  centered("APPS",233,80,3,WHITE);
  centeredButton(105,160,256,92,"CLOCK",CYAN);
  centeredButton(105,276,256,92,"TIMER",CYAN);
}''')
# Ensure hats visibly selected: draw the accessory preview as enlarged native pixels at a fixed y.
replace('  if (previewFrogHat) drawFrogHat(previewFrogHat, 211, 323, 2);','  if (previewFrogHat) drawFrogHat(previewFrogHat, 193, 307, 3);', "hat accessory preview")
# Avoid gameDraw called by GAMES. Force redraw only with current page.
replace('''  } else if (screen == APPS || screen == SETTINGS) {
    redraw = changedScreen;''','''  } else if (screen == APPS || screen == SETTINGS || screen == APPS_HUB || screen == GAMES) {
    redraw = changedScreen || (screen == APPS && frogStepsRendered != frogSteps);''', "safe placeholders redraw")
replace('''    else if (screen == SETTINGS) drawSettingsMenu();''','''    else if (screen == SETTINGS) drawSettingsMenu();
    else if (screen == GAMES) drawEmptyGames();
    else if (screen == APPS_HUB) drawAppsHub();''', "draw placeholders")
# Stop game processing in loop from touching non-game screens, and GAMES is now a placeholder.
replace('  if (screen == GAMES && selectedGame == G_TREX) {','  if (false && screen == GAMES && selectedGame == G_TREX) {','skip game loop')
replace('  if (screen == GAMES) gameUpdate(now);','  if (false && screen == GAMES) gameUpdate(now);','skip game update')
# Keep step counter screen refreshing after motion. Already tracked, in render path set only after render.
# Sound: queue only from confirmed single tap; no audio at all for a double tap.
replace('      frogCurrentAction = FROG_CROAK_ACTION;','      frogCurrentAction = FROG_CROAK_ACTION;\n      requestCroakSound();',"single croak sound")
# Initialize ES8311 with official Waveshare Arduino example and generated 16k PCM.
audio = r'''
I2SClass frogI2S;
volatile bool frogCroakRequested = false;
bool frogAudioReady = false;
void requestCroakSound() { frogCroakRequested = true; }
void frogAudioTask(void *param) {
  frogI2S.setPins(9,45,8,10,42); // Waveshare 1.75 ES8311 example pin wiring
  if (!frogI2S.begin(I2S_MODE_STD, 16000, I2S_DATA_BIT_WIDTH_16BIT,
                     I2S_SLOT_MODE_STEREO, I2S_STD_SLOT_BOTH)) {
    Serial.println("FROG AUDIO: I2S initialization failed");
    vTaskDelete(NULL);return;
  }
  es8311_handle_t codec = es8311_create(0, ES8311_ADDRRES_0);
  const es8311_clock_config_t clk={false,false,true,16000*256,16000};
  if (!codec || es8311_init(codec,&clk,ES8311_RESOLUTION_16,ES8311_RESOLUTION_16)!=ESP_OK) {
    Serial.println("FROG AUDIO: ES8311 initialization failed");
    vTaskDelete(NULL);return;
  }
  es8311_voice_volume_set(codec,72,NULL);
  frogAudioReady = true;
  while (true) {
    if (frogCroakRequested) {
      frogCroakRequested = false;
      // PCM is interleaved stereo 16-bit, 16kHz, already generated by build.
      frogI2S.write((uint8_t*)FROG_CROAK_PCM,FROG_CROAK_PCM_BYTES);
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}
'''
# Add audio code immediately before setup (after boot splash functions).
replace('bool uploadMode = false;',audio+'\nbool uploadMode = false;', "audio implementation")
replace('  panel->setBrightness(110);','  panel->setBrightness(110);\n  pinMode(46,OUTPUT); digitalWrite(46,HIGH); // speaker amp enable', "amp enable")
replace('  Serial.println("Ready: FROG POND -> APPS -> (CLOCK / TIMER / COUNTER / GAMES)");',
        '  xTaskCreatePinnedToCore(frogAudioTask,"frog_audio",6144,NULL,1,NULL,1);\n  Serial.println("Ready: Frog Pond V7");',"start audio task")
path.write_text(s)
print('Patched V7',path,'size',len(s))
