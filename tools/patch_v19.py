#!/usr/bin/env python3
"""V19: remove Clock from Apps, two-page Time/Date editor, Save to pond, temporary uploaded idle strip."""
from pathlib import Path
import re,sys
p=next(Path(sys.argv[1]).rglob("*.ino"))
s=p.read_text()
def replace(old,new,what):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{what}: found {n} anchors")
 s=s.replace(old,new,1)
def span(sig):
 a=s.find(sig)
 if a<0:raise RuntimeError("Missing function "+sig)
 b=s.index("{",a);depth=0
 for i in range(b,len(s)):
  if s[i]=='{':depth+=1
  elif s[i]=='}':
   depth-=1
   if depth==0:return a,i+1
 raise RuntimeError("Unbalanced "+sig)
def function(sig,body):
 global s
 a,b=span(sig);s=s[:a]+body+s[b:]
# Restore the intended main HOME screen after a verified NVS Save, not the menu.
replace("openScreen(APPS); // Save returns to the main Games / Apps / Settings menu.",
        "openScreen(FACE); // A verified personalization Save returns to pond HOME.","save target")
# Remove the clock item; apps retain Timer and Counter.
function("void drawAppsHub() {",'''void drawAppsHub() {
 gfx->fillScreen(0x0863);
 centered("APPS",233,80,3,WHITE);
 centeredButton(105,160,256,92,"TIMER",CYAN);
 centeredButton(105,276,256,92,"COUNTER",CYAN);
 centered("SWIPE RIGHT TO RETURN",233,424,1,GRAY);
}''')
replace('if (inside(x,y,105,160,256,92)) openScreen(CLOCK);','if (inside(x,y,105,160,256,92)) openScreen(TIMER_APP);',"Timer route")
replace('else if (inside(x,y,105,276,256,92)) openScreen(TIMER_APP);','else if (inside(x,y,105,276,256,92)) openScreen(COUNTER_APP);',"Counter route")
# All clock/date settings remain in Settings, not Apps.
replace('bool clock24h=true, pondRtcReady=false, pondSD=false, dateSaveError=false;',
        'bool clock24h=true, pondRtcReady=false, pondSD=false, dateSaveError=false;\nuint8_t timeEditorPage=0;', "page state")
replace(' dateSaveError=false;openScreen(TIME_SETTINGS);',
        ' dateSaveError=false;timeEditorPage=0;openScreen(TIME_SETTINGS);',"open time first")
# Larger touch targets with a visible two-dot page indicator.
# Both pages edit the same RTC struct, and Save writes the full date/time atomically.
function('void pondTimeTap(int x,int y){',r'''void pondTimeTap(int x,int y){
 if(y>=63 && y<=114 && x<122){openScreen(SETTINGS);return;}
 if(y>=364&&y<=418){
  if(pondWriteClock()){
   prefs.putBool("24hour",clock24h);
   pondRtcReady=pondReadClock();rtcPollAt=0;dateSaveError=false;
   openScreen(SETTINGS);
  }else dateSaveError=true;
  return;
 }
 if(y>=314&&y<=361){
  if(timeEditorPage==0){
   if(x>=122&&x<=320){clock24h=!clock24h;return;}
   if(x>320){timeEditorPage=1;return;}
  }else{
   if(x<160){timeEditorPage=0;return;}
  }
 }
 if((y>=151&&y<=209)||(y>=246&&y<=304)){
  int delta=y<220?1:-1;
  if(timeEditorPage==0){
   if(x>=69&&x<=218)pondDateChange(3,delta);
   else if(x>=247&&x<=396)pondDateChange(4,delta);
  }else{
   if(x>=64&&x<174)pondDateChange(0,delta);
   else if(x>=176&&x<=290)pondDateChange(1,delta);
   else if(x>290&&x<=404)pondDateChange(2,delta);
  }
 }
}
void pondEditorIndicator(){
 gfx->fillCircle(218,431,6,timeEditorPage==0?WHITE:0x5B6D);
 gfx->fillCircle(248,431,6,timeEditorPage==1?WHITE:0x5B6D);
}
''')
# Draw each editor with large plus/minus controls accessible on the round display.
function('void pondDrawTime(){',r'''void pondDrawTime(){
 gfx->fillScreen(0x0863);
 centered(timeEditorPage==0?"TIME":"DATE",233,67,3,WHITE);
 gfx->fillRoundRect(55,68,61,43,10,0x2467);
 centered("<",85,75,2,WHITE);
 if(timeEditorPage==0){
   int hours=editDate.hour;
   if(!clock24h)hours=hours%12?hours%12:12;
   centered("HOUR",145,129,2,WHITE);
   centered("MINUTE",321,129,2,WHITE);
   for(int i=0;i<2;i++){
     int cx=i?321:145;
     gfx->fillRoundRect(cx-53,151,106,58,14,0x2467);
     gfx->fillRoundRect(cx-53,246,106,58,14,0x2467);
     centered("+",cx,163,3,WHITE);centered("-",cx,255,3,WHITE);
   }
   centered(String(hours),145,218,3,WHITE);
   char mm[4];snprintf(mm,sizeof(mm),"%02d",editDate.minute);
   centered(mm,321,218,3,WHITE);
   gfx->fillRoundRect(153,316,160,45,10,0x2C6A);
   centered(clock24h?"24 HOUR":(editDate.hour>=12?"12 HOUR PM":"12 HOUR AM"),233,329,1,WHITE);
   centered(">",348,325,2,WHITE);
 }else{
   const int xx[3]={116,233,350};
   const char* labels[3]={"MONTH","DAY","YEAR"};
   const int nums[3]={editDate.month,editDate.day,editDate.year};
   for(int i=0;i<3;i++){
     int cx=xx[i];
     centered(labels[i],cx,129,1,WHITE);
     gfx->fillRoundRect(cx-45,151,90,58,12,0x2467);
     gfx->fillRoundRect(cx-45,246,90,58,12,0x2467);
     centered("+",cx,163,3,WHITE);centered("-",cx,257,3,WHITE);
     centered(String(nums[i]),cx,221,i==2?2:3,WHITE);
   }
   centered("< TIME",121,329,1,WHITE);
 }
 centeredButton(145,366,176,49,dateSaveError?"RTC ERROR":"SAVE",0x07E0);
 pondEditorIndicator();
}''')
# Swiping Time -> Date or Date -> Time; outer-edge swipe returns to Settings.
replace('if(screen==TIME_SETTINGS){openScreen(SETTINGS);return;}',
        'if(screen==TIME_SETTINGS){\n    if(direction<0){if(timeEditorPage==0)timeEditorPage=1;else openScreen(SETTINGS);}\n    else {if(timeEditorPage==1)timeEditorPage=0;else openScreen(SETTINGS);}\n    return;\n  }',"swipe navigation")
replace('if(abs(dx)>SWIPE_THRESHOLD&&abs(dx)>abs(dy)*1.1f)openScreen(SETTINGS);',
        'if(abs(dx)>SWIPE_THRESHOLD&&abs(dx)>abs(dy)*1.1f)changeScreen(dx<0?-1:1);',"touch swipe between pages")
# Test-only new 22-frame idle, alpha-masked from user's exact sprite strip.
replace('#include "frog_isolated_hats.h"','#include "frog_isolated_hats.h"\n#include "pond_idle_test.h"',"test sprite include")
idle=r'''
void drawTestIdleFrogFrame(uint32_t now,int x,int y,int scale,uint8_t hat){
  const int frame=(now/140)%POND_IDLE_FRAMES;
  const uint8_t* pix=POND_IDLE_PIXELS[frame];
  // All transparent pixels have index zero; no pink or opaque background.
  for(int yy=0;yy<POND_IDLE_H;++yy){
    int xx=0;
    while(xx<POND_IDLE_W){
      uint8_t c=pgm_read_byte(pix+yy*POND_IDLE_W+xx);
      if(!c){++xx;continue;}
      int start=xx++;
      while(xx<POND_IDLE_W && pgm_read_byte(pix+yy*POND_IDLE_W+xx)==c)++xx;
      uint16_t color=pgm_read_word(POND_IDLE_PALETTE+c);
      gfx->fillRect(x+(start+1)*scale,y+yy*scale,(xx-start)*scale,scale,color);
    }
  }
  if(hat>0)drawIsolatedHatFrame(hat,0,x,y,scale);
}
'''
replace('void drawFace(uint32_t now) {',idle+'\nvoid drawFace(uint32_t now) {',"new idle renderer")
a,b=span('void drawFace(uint32_t now) {')
section=s[a:b]
calls=list(re.finditer(r'drawFrogSpriteStyled\s*\(([^;]+?)\)\s*;',section))
if len(calls)!=1:
 print("HOME_RENDER_DIAGNOSTIC_START\\n"+section[:7000]+"\\nHOME_RENDER_DIAGNOSTIC_END",flush=True)
 raise RuntimeError(f"Expected one home frog draw call, found {len(calls)}")
call=calls[0]
args=[v.strip() for v in call.group(1).split(',')]
if len(args)!=6:raise RuntimeError("Home sprite draw arguments changed: "+repr(args))
# Only green frog idle is replaced for this temporary visual test; other colors,
# jumping and croaking continue using their existing artwork and actions.
replacement=f'''if(selectedFrogColor==0 && (!frogActionAt || (uint32_t)(now-frogActionAt)>1400)){{
    drawTestIdleFrogFrame(now,{args[1]},{args[2]},{args[3]},selectedFrogHat);
  }}else{{
    {call.group(0)}
  }}'''
section=section[:call.start()]+replacement+section[call.end():]
s=s[:a]+section+s[b:]
# Support smoother idle frames instead of skipping two frames per repaint.
if "(now-prevFrameAt>=240)" in s:s=s.replace("(now-prevFrameAt>=240)","(now-prevFrameAt>=140)",1)
for token in ['drawTestIdleFrogFrame(now,','timeEditorPage=0','pondEditorIndicator();','openScreen(FACE); // A verified','openScreen(COUNTER_APP);']:
 if token not in s:raise RuntimeError("V19 feature missing after patch: "+token)
p.write_text(s)
print("V19: Home idle test, Clock removed, two-page Time/Date UI, verified Personalize Save -> pond home.")
