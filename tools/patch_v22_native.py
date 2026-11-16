#!/usr/bin/env python3
"""Integration-branch-only native TAT game dispatcher for Frog Pond V21."""
from pathlib import Path
import sys
files=list(Path(sys.argv[1]).rglob("*.ino"))
if len(files)!=1:raise RuntimeError("expected one .ino")
p=files[0];s=p.read_text()
def swap(old,new,label):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{label}: expected one match, found {n}")
 s=s.replace(old,new,1)

swap('#include "frogpond_pause.h"',
     '#include "frogpond_pause.h"\n#include "src/pondtat_runtime.h"',
     "host header")
swap('constexpr Screen POCKET_WATCH=static_cast<Screen>(44);',
     'constexpr Screen POCKET_WATCH=static_cast<Screen>(44);\n'
     'constexpr Screen TAT_ORIGINAL=static_cast<Screen>(45);',
     "original game screen")
native=r"""
// Original Tilt-a-Tron game host bridge. V21 style, pond and watch remain untouched.
void tatPresentBitmap(const uint16_t* pixels){
  gfx->draw16bitRGBBitmap(0,0,(uint16_t*)pixels,466,466);
}
void tatExitToCatalog(){
  tiltMenuPage=pondtat::page();
  openScreen(GAMES);
}
void tatStartOriginal(uint8_t index){
  pondtat::init(tatPresentBitmap,nullptr,tatExitToCatalog);
  if(pondtat::start(index))openScreen(TAT_ORIGINAL);
  else {tiltUnportedNotice=index;tiltNoticeUntil=millis()+1800;}
}
"""
swap('void drawTiltCatalog(){',native+'\nvoid drawTiltCatalog(){',"host launch bridge")
old='''if(item==0){
          echoPrepare();tiltPause.startGame(0,tiltMenuPage);
          openScreen(ECHO_GAME);
        }else{
          tiltUnportedNotice=item;tiltNoticeUntil=millis()+1700;
        }'''
swap(old,'tatStartOriginal((uint8_t)item);',"replace placeholder launches")
# Native input must bypass generic tap/swipe dispatch.
swap('if(screen==ECHO_GAME){echoTouchHandler(now,down,x,y);return;}',
'''if(screen==TAT_ORIGINAL){pondtat::touch(now,down,x,y);return;}
 if(screen==ECHO_GAME){echoTouchHandler(now,down,x,y);return;}''',"game touch intercept")
swap('  if(screen==ECHO_GAME)return;',
     '  if(screen==ECHO_GAME||screen==TAT_ORIGINAL)return;',
     "native swipe restriction")
# Add native rendering near old Echo redraw, original game controls its own frame.
anchor='  } else if (screen == ECHO_GAME) {\n    interval=85; redraw=changedScreen||now-prevFrameAt>=85;'
if s.count(anchor)!=1:raise RuntimeError("game refresh anchor not unique")
s=s.replace(anchor,'''  } else if (screen == TAT_ORIGINAL) {
    interval=50; redraw=changedScreen||now-prevFrameAt>=50;
  } else if (screen == ECHO_GAME) {
    interval=85; redraw=changedScreen||now-prevFrameAt>=85;''',1)
swap('    else if (screen == ECHO_GAME) echoDraw(now);',
'''    else if (screen == TAT_ORIGINAL) {
      pondtat::frame(now);
      if(pondtat::paused())echoDrawPause();
    }
    else if (screen == ECHO_GAME) echoDraw(now);''',"native game frame dispatch")
# A paused game intercepts the 3 menu actions via the shared host.
for token in ('pondtat::frame(now)','pondtat::touch(now,down,x,y)','TAT_ORIGINAL','tatStartOriginal((uint8_t)item)'):
 if token not in s:raise RuntimeError("missing "+token)
p.write_text(s)
print("Native original games linked into V21 catalog on experimental branch.")
