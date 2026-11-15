#!/usr/bin/env python3
"""V21: three-page game catalog, playable Echo adaptation, top-edge pause menu,
and RTC-powered Pocket Watch (swipe down from Frog Pond home).
Tilt-a-Tron game design © 2026 PartiallyFrozen, MIT licensed.
"""
from pathlib import Path
import sys
files=list(Path(sys.argv[1]).rglob("*.ino"))
if len(files)!=1:raise RuntimeError("Expected one Frog Pond sketch")
p=files[0];s=p.read_text()
def swap(old,new,label):
 global s
 if s.count(old)!=1:raise RuntimeError(f"{label}: expected 1 match, got {s.count(old)}")
 s=s.replace(old,new,1)
def span(sig):
 a=s.find(sig)
 if a<0:raise RuntimeError("Missing function "+sig)
 b=s.index("{",a); d=0
 for i in range(b,len(s)):
  if s[i]=="{":d+=1
  elif s[i]=="}":
   d-=1
   if d==0:return a,i+1
 raise RuntimeError("Unbalanced "+sig)
def function(sig,body):
 global s
 a,b=span(sig); s=s[:a]+body+s[b:]
# These enum values are deliberately disjoint from existing screens and TIME_SETTINGS (42).
swap('constexpr Screen TIME_SETTINGS=static_cast<Screen>(42);',
'''constexpr Screen TIME_SETTINGS=static_cast<Screen>(42);
constexpr Screen ECHO_GAME=static_cast<Screen>(43);
constexpr Screen POCKET_WATCH=static_cast<Screen>(44);''',"additional screens")
swap('#include "pond_idle_test.h"','#include "pond_idle_test.h"\n#include "frogpond_pause.h"',"pause header")
game=r"""
// The menu is ordered exactly as in PartiallyFrozen/tilt-a-tron/games.
// Only Echo is playable in this first port. Others report NOT PORTED.
static const char *const kTiltGameNames[11]={
 "ECHO","STARFALL","RADAR","MARBLE MAZE",
 "GRAND PRIX","TILT-A-TRIS","SLEEPY STAR","PIN DROP",
 "BREAKOUT","SKATER GIRLZ","SKY JUMP"
};
uint8_t tiltMenuPage=0, tiltUnportedNotice=255;
uint32_t tiltNoticeUntil=0;
frogpond::GamePauseController tiltPause;
bool tiltJustPaused=false;
enum EchoPhase:uint8_t { ECHO_READY,ECHO_SHOW,ECHO_INPUT,ECHO_CHEER,ECHO_LOST };
EchoPhase echoPhase=ECHO_READY;
uint8_t echoRun[256];
uint16_t echoLen=1, echoAt=0, echoBest=0;
uint32_t echoPhaseAt=0, echoLastInputAt=0;
void echoPrepare(){
 echoPhase=ECHO_READY;echoLen=1;echoAt=0;echoPhaseAt=millis();
 echoBest=(uint16_t)prefs.getUInt("echoBest",0);
}
uint32_t echoStepMs(){
 uint8_t tier=(echoLen-1)/4;
 return tier==0?800:tier==1?660:tier==2?540:440;
}
void echoBeginShow(uint32_t now){
 echoPhase=ECHO_SHOW;echoPhaseAt=now+300;echoAt=0;
}
void echoStart(uint32_t now){
 echoLen=1;echoAt=0;
 for(int i=0;i<256;i++)echoRun[i]=(uint8_t)random(4);
 echoBeginShow(now);
}
void echoUpdate(uint32_t now){
 if(tiltPause.isPaused())return;
 if(echoPhase==ECHO_SHOW){
  if(now<echoPhaseAt)return;
  uint32_t step=echoStepMs();
  if((uint32_t)(now-echoPhaseAt)>=(uint32_t)echoLen*step){
   echoPhase=ECHO_INPUT;echoAt=0;echoLastInputAt=now;
  }
 }else if(echoPhase==ECHO_CHEER && (uint32_t)(now-echoPhaseAt)>1150){
  if(echoLen<256)++echoLen;
  echoBeginShow(now);
 }else if(echoPhase==ECHO_INPUT && (uint32_t)(now-echoLastInputAt)>5*echoStepMs()){
  echoPhase=ECHO_LOST;echoPhaseAt=now;
 }
}
int echoPadAt(int x,int y){
 // Up/right/down/left, matching the upstream four-pad arrangement.
 if(x>=165&&x<=301&&y>=110&&y<=199)return 0;
 if(x>=261&&x<=405&&y>=195&&y<=295)return 1;
 if(x>=165&&x<=301&&y>=291&&y<=382)return 2;
 if(x>=61&&x<=205&&y>=195&&y<=295)return 3;
 return -1;
}
void echoTap(int x,int y,uint32_t now){
 if(echoPhase==ECHO_READY||echoPhase==ECHO_LOST){echoStart(now);return;}
 if(echoPhase!=ECHO_INPUT)return;
 int pad=echoPadAt(x,y);
 if(pad<0)return;
 echoLastInputAt=now;
 if((uint8_t)pad!=echoRun[echoAt]){
  echoPhase=ECHO_LOST;echoPhaseAt=now;return;
 }
 if(++echoAt>=echoLen){
  if(echoLen>echoBest){
   echoBest=echoLen;prefs.putUInt("echoBest",echoBest);
  }
  echoPhase=ECHO_CHEER;echoPhaseAt=now;
 }
}
void echoDrawPause(){
 gfx->fillRoundRect(78,98,310,320,18,0x1083);
 gfx->drawRoundRect(78,98,310,320,18,WHITE);
 centered("GAME PAUSED",233,108,2,WHITE);
 centeredButton(95,132,276,77,"RESUME GAME",0x2586);
 centeredButton(95,223,276,77,"RESTART GAME",0x3A68);
 centeredButton(95,314,276,82,"EXIT TO GAMES",0x89E4);
}
void echoDraw(uint32_t now){
 echoUpdate(now);
 gfx->fillScreen(0x0843);
 centered("ECHO",233,39,3,0x5EEC);
 const uint16_t bg[]={0x32E0,0x02AF,0xDA20,0xD9A4};
 int lit=-1;
 if(echoPhase==ECHO_SHOW && now>=echoPhaseAt){
  uint32_t elapsed=now-echoPhaseAt, step=echoStepMs();
  if(elapsed<(uint32_t)echoLen*step && elapsed%step<step/2)
   lit=echoRun[elapsed/step];
 }
 if(echoPhase==ECHO_CHEER && ((now/120)%3!=0))lit=-2;
 int xy[4][4]={{165,110,136,89},{261,195,144,100},{165,291,136,91},{61,195,144,100}};
 for(int i=0;i<4;i++){
  int x=xy[i][0],y=xy[i][1],w=xy[i][2],h=xy[i][3];
  uint16_t c=(lit==i||lit==-2)?WHITE:bg[i];
  gfx->fillRoundRect(x,y,w,h,16,c);
  gfx->drawRoundRect(x,y,w,h,16,0xBDF7);
 }
 gfx->fillCircle(233,246,43,0x0863);
 gfx->drawCircle(233,246,43,0xBDF7);
 centered(String((int)echoLen),233,235,3,WHITE);
 centered("BEST "+String((int)echoBest),233,398,1,WHITE);
 if(echoPhase==ECHO_READY)centered("TAP TO START",233,422,1,WHITE);
 else if(echoPhase==ECHO_SHOW)centered("WATCH THE PATTERN",233,422,1,WHITE);
 else if(echoPhase==ECHO_INPUT)centered("REPEAT THE PATTERN",233,422,1,WHITE);
 else if(echoPhase==ECHO_CHEER)centered("WELL DONE!",233,422,1,WHITE);
 else centered("TRY AGAIN - TAP",233,422,1,WHITE);
 if(tiltPause.isPaused())echoDrawPause();
}
void drawTiltCatalog(){
 gfx->fillScreen(0x0863);
 centered("GAMES",233,68,3,WHITE);
 for(int slot=0;slot<4;slot++){
  int item=(int)tiltMenuPage*4+slot;
  if(item>=11)break;
  int x=(slot%2)?244:105;
  int y=(slot/2)?244:128;
  gfx->fillRoundRect(x,y,117,91,14,item==0?0x2586:0x2467);
  gfx->drawRoundRect(x,y,117,91,14,0x8F36);
  // Compact lettering keeps long names within 117 pixels.
  String name=kTiltGameNames[item];
  if(name.length()>12){
   int pivot=name.lastIndexOf(' ');
   if(pivot>0){centered(name.substring(0,pivot),x+59,y+25,1,WHITE);
               centered(name.substring(pivot+1),x+59,y+43,1,WHITE);}
   else centered(name,x+59,y+34,1,WHITE);
  }else centered(name,x+59,y+35,name.length()<9?2:1,WHITE);
 }
 if(tiltMenuPage>0){
  gfx->fillRoundRect(23,351,80,50,12,0x2467);
  centered("<",63,358,3,WHITE);
 }
 if(tiltMenuPage<2){
  gfx->fillRoundRect(363,351,80,50,12,0x2467);
  centered(">",403,358,3,WHITE);
 }
 for(int pg=0;pg<3;pg++)gfx->fillCircle(208+pg*25,424,6,pg==tiltMenuPage?WHITE:0x5B6D);
 if(tiltUnportedNotice<11 && (int32_t)(tiltNoticeUntil-millis())>0){
  gfx->fillRoundRect(107,341,252,50,12,0x1083);
  centered("PORT COMING SOON",233,357,1,WHITE);
 }
 drawPageBackArrow();
}
void drawPocketWatch(){
 gfx->fillScreen(0x0843);
 pondReadClock();
 centered("POCKET WATCH",233,51,2,0xF7B7);
 gfx->fillRoundRect(216,96,34,27,9,0xCBA6);
 gfx->drawCircle(233,245,129,0xCBA6);
 gfx->drawCircle(233,245,123,0xF7B7);
 gfx->fillCircle(233,245,115,0x2104);
 for(int h=0;h<12;h++){
  float a=h*6.2831853f/12.0f-1.5707963f;
  int x1=233+(int)(cosf(a)*94),y1=245+(int)(sinf(a)*94);
  int x2=233+(int)(cosf(a)*109),y2=245+(int)(sinf(a)*109);
  gfx->drawLine(x1,y1,x2,y2,0xF7B7);
 }
 int hh=realDate.hour,mm=realDate.minute;
 float am=(mm/60.0f)*6.2831853f-1.5707963f;
 float ah=((hh%12+mm/60.0f)/12.0f)*6.2831853f-1.5707963f;
 gfx->drawLine(233,245,233+(int)(cosf(am)*84),245+(int)(sinf(am)*84),WHITE);
 gfx->drawLine(233,245,233+(int)(cosf(ah)*61),245+(int)(sinf(ah)*61),0xF7B7);
 gfx->fillCircle(233,245,6,0xF7B7);
 int shown=clock24h?hh:(hh%12?hh%12:12);
 char stamp[25];snprintf(stamp,sizeof(stamp),"%02d:%02d",shown,mm);
 centered(stamp,233,353,2,WHITE);
 if(!clock24h)centered(hh>=12?"PM":"AM",233,381,1,WHITE);
 drawPageBackArrow();
}
void echoTouchHandler(uint32_t now,bool down,int x,int y){
 if(down&&!fingerDown){
  fingerDown=true;downX=lastX=x;downY=lastY=y;downAt=now;
  tiltPause.touchDown(x,y);
  tiltJustPaused=false;
  return;
 }
 if(down&&fingerDown){
  lastX=x;lastY=y;
  if(tiltPause.touchMove(x,y)==frogpond::GamePauseController::PAUSE)
   tiltJustPaused=true;
  return;
 }
 if(!down&&fingerDown){
  fingerDown=false;
  if(tiltJustPaused){tiltJustPaused=false;return;}
  if(tiltPause.isPaused()){
   frogpond::GamePauseController::Action action=tiltPause.touchUp(lastX,lastY);
   if(action==frogpond::GamePauseController::RESTART)echoStart(now);
   else if(action==frogpond::GamePauseController::EXIT_TO_GAMES){
    tiltMenuPage=tiltPause.returnPage();openScreen(GAMES);
   }
   return;
  }
  // Top-edge swipe is an exit shortcut, not gameplay input.
  if(downY<=frogpond::GamePauseController::TOP_EDGE)return;
  if(abs(lastX-downX)<45&&abs(lastY-downY)<45)echoTap(downX,downY,now);
 }
}
"""
swap('void drawEmptyGames() {',game+'\nvoid drawEmptyGames() {',"game engine insertion")
function('void drawEmptyGames() {','void drawEmptyGames(){drawTiltCatalog();}')
# New screen selection and per-page controls in the existing tap handler.
start=s.index('  } else if (screen == GAMES) {',s.index('void tapped(int x, int y) {'))
end=s.index('  } else if (screen == FROGHOP_GAME) {',start)
s=s[:start]+'''  } else if (screen == GAMES) {
    if(y>=338&&y<=413&&x<=104&&tiltMenuPage>0) {
      tiltMenuPage--;tiltUnportedNotice=255;return;
    }
    if(y>=338&&y<=413&&x>=360&&tiltMenuPage<2) {
      tiltMenuPage++;tiltUnportedNotice=255;return;
    }
    int slot=-1;
    if(y>=122&&y<=225){if(x>=103&&x<=231)slot=0;else if(x>=241&&x<=367)slot=1;}
    else if(y>=240&&y<=337){if(x>=103&&x<=231)slot=2;else if(x>=241&&x<=367)slot=3;}
    if(slot>=0){
      int item=tiltMenuPage*4+slot;
      if(item<11){
        if(item==0){
          echoPrepare();tiltPause.startGame(0,tiltMenuPage);
          openScreen(ECHO_GAME);
        }else{
          tiltUnportedNotice=item;tiltNoticeUntil=millis()+1700;
        }
      }
    }
  } else if (screen == ECHO_GAME) {
    // Active-game touches handled before generic taps for reliable pause gestures.
  } else if (screen == POCKET_WATCH) {
    if(inside(x,y,15,210,88,60))openScreen(FACE);
''' + s[end:]
# Route left/right swipes on the game menu; in-game swipe handled by the pause controller.
swap('void changeScreen(int direction) {', '''void changeScreen(int direction) {
  if(screen==GAMES){
    if(direction<0&&tiltMenuPage<2)tiltMenuPage++;
    else if(direction>0&&tiltMenuPage>0)tiltMenuPage--;
    return;
  }
  if(screen==POCKET_WATCH){openScreen(FACE);return;}
  if(screen==ECHO_GAME)return;
''',"game catalog swipes")
# Intercept native touch before the generic screen dispatch (including swipe and tap).
anchor=' if(down&&!fingerDown){'
start=s.index('void pollTouch(uint32_t now){')
point=s.find(anchor,start)
if point<0:raise RuntimeError("touch state machine not found")
s=s[:point]+''' if(screen==ECHO_GAME){echoTouchHandler(now,down,x,y);return;}
'''+s[point:]
# Downward swipe from the pond opens the pocket watch. Upward frog jump untouched.
swap('  if(frogSwipeJumpConsumed){frogSwipeJumpConsumed=false;return;}',
'''  if(screen==FACE && dy>=SWIPE_THRESHOLD && abs(dy)>abs(dx)*1.2f) {
    frogTapPending=false;openScreen(POCKET_WATCH);return;
  }
  if(frogSwipeJumpConsumed){frogSwipeJumpConsumed=false;return;}''',"pocket watch downward swipe")
# Screens need periodic refresh to show Echo playback/pause, and analog watch time.
anchor='  } else if (screen == FROGHOP_GAME) {\n    interval=65;'
if s.count(anchor)<1:raise RuntimeError("Missing old game redraw branch")
s=s.replace(anchor,'''  } else if (screen == ECHO_GAME) {
    interval=85; redraw=changedScreen||now-prevFrameAt>=85;
  } else if (screen == POCKET_WATCH) {
    interval=1000; redraw=changedScreen||now-prevFrameAt>=1000;
  } else if (screen == FROGHOP_GAME) {
    interval=65;''',1)
swap('    else if (screen == GAMES) drawEmptyGames();',
'''    else if (screen == GAMES) drawEmptyGames();
    else if (screen == ECHO_GAME) echoDraw(now);
    else if (screen == POCKET_WATCH) drawPocketWatch();''',"new draw screens")
# A redraw on game-page arrow tap is required even if screen identity has not changed.
anchor='  } else if (screen == APPS || screen == SETTINGS || screen == APPS_HUB || screen == GAMES) {'
swap(anchor,'''  } else if (screen == APPS || screen == SETTINGS || screen == APPS_HUB || screen == GAMES) {
    // The catalog has three pages and transient unavailable-game notices.
    if(screen==GAMES && now-prevFrameAt>=125)changedScreen=true;''',"catalog redraw")
for marker in ['echoDraw(now);','drawTiltCatalog();','drawPocketWatch();',
               'tiltPause.returnPage()','openScreen(POCKET_WATCH)',
               'frogpond::GamePauseController','TILT-A-TRIS','SKATER GIRLZ']:
 if marker not in s:raise RuntimeError("Missing feature "+marker)
p.write_text(s)
print("V21 playable Echo, 11-name three-page catalog, top-edge pause, temporary RTC Pocket Watch.")
