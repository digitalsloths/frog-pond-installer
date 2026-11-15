#!/usr/bin/env python3
"""V17 settings + PCF85063 date/time + time-of-day SD scene switching."""
from pathlib import Path
import re,sys
files=list(Path(sys.argv[1]).rglob("*.ino"))
assert len(files)==1,files
p=files[0];s=p.read_text()
def swap(a,b,n):
 global s
 if s.count(a)!=1:raise RuntimeError(f"{n}: expected one source anchor, found {s.count(a)}")
 s=s.replace(a,b,1)
def fn(sig,new):
 global s
 a=s.find(sig)
 if a<0:raise RuntimeError("Missing "+sig)
 b=s.index("{",a);d=0
 for i in range(b,len(s)):
  if s[i]=="{":d+=1
  elif s[i]=="}":
   d-=1
   if d==0:
    s=s[:a]+new+s[i+1:];return
 raise RuntimeError("Unbalanced "+sig)
swap('#include "frog_isolated_hats.h"','#include "frog_isolated_hats.h"\n#include <SD_MMC.h>',"SDMMC")
swap("volatile uint8_t frogVolumePct = 72;","volatile uint8_t frogVolumePct = 72;\nuint8_t ambientVolumePct=40;", "ambient control")
m=re.search(r'enum Screen\s*:\s*uint8_t\s*\{[^}]+\};',s)
if not m:raise RuntimeError("screen enumeration missing")
s=s[:m.end()]+"\nconstexpr Screen TIME_SETTINGS=static_cast<Screen>(42);\n"+s[m.end():]
helpers=r"""
struct PondDate {int year,month,day,hour,minute;};
PondDate editDate={2026,1,1,12,0}, realDate={2026,1,1,12,0};
bool clock24h=true, pondRtcReady=false, pondSD=false, dateSaveError=false;
uint32_t rtcPollAt=0;
uint16_t *sceneRGB=nullptr;
int sceneLoaded=-1;
const char *sceneNames[6]={"night","dawn","sunrise","morning","day","dusk"};
uint8_t pondBcd(int v){return (uint8_t)((v/10)*16+(v%10));}
int pondDec(uint8_t v){return (v>>4)*10+(v&15);}
int pondMonthDays(int y,int m){
 if(m==2)return (y%4==0&&(y%100!=0||y%400==0))?29:28;
 return (m==4||m==6||m==9||m==11)?30:31;
}
bool pondReadClock(){
 Wire.beginTransmission(0x51);Wire.write((uint8_t)4);
 if(Wire.endTransmission(false)!=0)return false;
 if(Wire.requestFrom((uint8_t)0x51,(uint8_t)7)!=7)return false;
 uint8_t v[7];for(int i=0;i<7;i++)v[i]=Wire.read();
 PondDate t={2000+pondDec(v[6]),pondDec(v[5]&31),pondDec(v[3]&63),pondDec(v[2]&63),pondDec(v[1]&127)};
 if(t.year<2020||t.year>2099||t.month<1||t.month>12||t.day<1||t.day>pondMonthDays(t.year,t.month)||t.hour>23||t.minute>59)return false;
 realDate=t;return true;
}
bool pondWriteClock(){
 if(editDate.year<2020||editDate.year>2099||editDate.month<1||editDate.month>12||editDate.day<1||editDate.day>pondMonthDays(editDate.year,editDate.month)||editDate.hour>23||editDate.minute>59)return false;
 Wire.beginTransmission(0x51);Wire.write((uint8_t)4);
 Wire.write(pondBcd(0));Wire.write(pondBcd(editDate.minute));Wire.write(pondBcd(editDate.hour));
 Wire.write(pondBcd(editDate.day));Wire.write((uint8_t)0);
 Wire.write(pondBcd(editDate.month));Wire.write(pondBcd(editDate.year-2000));
 return Wire.endTransmission()==0;
}
int pondScene(int h,int m){
 int t=h*60+m;
 if(t<300)return 0; // night
 if(t<390)return 1; // dawn
 if(t<450)return 2; // sunrise
 if(t<660)return 3; // morning
 if(t<990)return 4; // day
 if(t<1050)return 2; // sunset uses sunrise art
 if(t<1110)return 1; // evening uses dawn art
 if(t<1170)return 5; // dusk
 return 0;
}
void pondMountSD(){
 SD_MMC.setPins(2,1,3);pondSD=SD_MMC.begin("/sdcard",true,false);
 Serial.println(pondSD?"POND scenes: SD ready":"POND scenes: embedded day fallback");
}
void pondSelectScene(int index){
 if(index==sceneLoaded)return;
 sceneLoaded=index;
 if(!pondSD)return;
 if(!sceneRGB)sceneRGB=(uint16_t*)ps_malloc(466*466*2);
 if(!sceneRGB)return;
 String path=String("/FrogPond/backgrounds/")+sceneNames[index]+".rgb565";
 File file=SD_MMC.open(path,FILE_READ);
 if(!file || file.size()!=466*466*2){if(file)file.close();Serial.printf("POND scene missing %s\n",path.c_str());return;}
 size_t got=file.readBytes((char*)sceneRGB,466*466*2);
 file.close();
 if(got!=466*466*2)Serial.println("POND scene read incomplete");
}
void pondSceneDraw(uint32_t now){
 if(!rtcPollAt || now-rtcPollAt>=30000){
  rtcPollAt=now?now:1;
  pondRtcReady=pondReadClock();
  pondSelectScene(pondRtcReady?pondScene(realDate.hour,realDate.minute):4);
 }
 if(pondSD&&sceneRGB&&sceneLoaded>=0)gfx->draw16bitRGBBitmap(0,0,sceneRGB,466,466);
 else if(frogPondRGB)gfx->draw16bitRGBBitmap(0,0,frogPondRGB,466,466);
 else gfx->fillScreen(0x056A);
}
void pondEditOpen(){
 editDate=pondReadClock()?realDate:PondDate{2026,1,1,12,0};
 dateSaveError=false;openScreen(TIME_SETTINGS);
}
void pondDateChange(int which,int step){
 if(which==0)editDate.month=1+(editDate.month-1+12+step)%12;
 if(which==1)editDate.day=1+(editDate.day-1+31+step)%pondMonthDays(editDate.year,editDate.month);
 if(which==2)editDate.year=2020+(editDate.year-2020+80+step)%80;
 if(which==3)editDate.hour=(editDate.hour+24+step)%24;
 if(which==4)editDate.minute=(editDate.minute+60+step)%60;
 if(editDate.day>pondMonthDays(editDate.year,editDate.month))editDate.day=pondMonthDays(editDate.year,editDate.month);
}
void pondTimeTap(int x,int y){
 if(y>=108&&y<195)pondDateChange(x<157?0:x<309?1:2,y<148?1:-1);
 else if(y>=205&&y<290)pondDateChange(x<233?3:4,y<244?1:-1);
 else if(y>=299&&y<352)clock24h=!clock24h;
 else if(y>=373&&y<=449){
  if(pondWriteClock()){
   prefs.putBool("24hour",clock24h);
   pondRtcReady=pondReadClock();rtcPollAt=0;dateSaveError=false;
   openScreen(SETTINGS);
  }else dateSaveError=true;
 }
}
void pondDrawTime(){
 gfx->fillScreen(0x0863);
 centered("TIME & DATE",233,54,2,WHITE);
 const int px[]={91,233,375};const char *lab[]={"MONTH","DAY","YEAR"};
 int val[]={editDate.month,editDate.day,editDate.year};
 for(int i=0;i<3;i++){
  centered(lab[i],px[i],91,1,GRAY);centered("+",px[i],115,2,WHITE);
  centered(String(val[i]),px[i],145,2,WHITE);centered("-",px[i],177,2,WHITE);
 }
 centered("HOUR",151,196,1,GRAY);centered("MINUTE",316,196,1,GRAY);
 int hour=editDate.hour;
 if(!clock24h)hour=hour%12?hour%12:12;
 centered("+",151,211,1,WHITE);centered("+",316,211,1,WHITE);
 centered(String(hour),151,244,2,WHITE);centered(String(editDate.minute),316,244,2,WHITE);
 centered("-",151,271,1,WHITE);centered("-",316,271,1,WHITE);
 centered(clock24h?"24 HOUR":(editDate.hour>=12?"12 HOUR PM":"12 HOUR AM"),233,313,2,WHITE);
 centeredButton(150,375,166,57,dateSaveError?"RTC ERROR":"SAVE",0x07E0);
 centered("SWIPE EITHER WAY TO RETURN",233,450,1,GRAY);
}
void pondDrawSettings(){
 gfx->fillScreen(0x0863);
 centered("SETTINGS",233,53,3,WHITE);
 centered("CROAK VOLUME",233,117,2,WHITE);
 gfx->fillRoundRect(65,158,336,40,12,0x39C7);
 int w=(int)frogVolumePct*316/100;
 if(w>0)gfx->fillRoundRect(75,165,w,26,8,0x07E0);
 centered(String((int)frogVolumePct)+"%",233,204,1,WHITE);
 centered("BACKGROUND VOLUME",233,229,2,WHITE);
 gfx->fillRoundRect(65,270,336,40,12,0x39C7);
 w=(int)ambientVolumePct*316/100;
 if(w>0)gfx->fillRoundRect(75,277,w,26,8,0x07E0);
 centered(String((int)ambientVolumePct)+"%",233,316,1,WHITE);
 centeredButton(124,352,218,56,"TIME",0x2C6A);
 centered("SWIPE RIGHT TO RETURN",233,437,1,GRAY);
}
uint8_t pondPercent(int x){return (uint8_t)constrain((x-75)*100/316,0,100);}
"""
swap('void drawSettingsMenu() {',helpers+'\nvoid drawSettingsMenu() {',"helper insertion")
def replacefunc(sig,new):
 global s
 a=s.find(sig)
 if a<0:raise RuntimeError("function missing: "+sig)
 b=s.index("{",a);d=0
 for j in range(b,len(s)):
  if s[j]=="{":d+=1
  elif s[j]=="}":
   d-=1
   if not d:s=s[:a]+new+s[j+1:];return
 raise RuntimeError("unbalanced "+sig)
replacefunc("void drawSettingsMenu() {","void drawSettingsMenu(){pondDrawSettings();}")
# Update the pond renderer without affecting the sprite or particle layers.
a=s.index('void drawFace(uint32_t now) {')
b=s.index('}',a)
section=s[a:b]
pat=r'if \(frogPondRGB\) gfx->draw16bitRGBBitmap\(0,0,frogPondRGB,FROG_POND_W,FROG_POND_H\);\s*else gfx->fillScreen\(0x056A\);'
if not re.search(pat,section):raise RuntimeError("scene blit anchor changed")
section=re.sub(pat,"pondSceneDraw(now);",section,count=1)
s=s[:a]+section+s[b:]
# Replace the settings input block, leave other menu controls untouched.
a=s.index("void tapped(int x, int y) {")
b=s.index("  } else if (screen == SETTINGS) {",a)
e=s.index("  } else if (screen ==",b+20)
s=s[:b]+'''  } else if (screen == SETTINGS) {
    if(inside(x,y,115,343,236,75))pondEditOpen();
'''+s[e:]
swap('void changeScreen(int direction) {','void changeScreen(int direction) {\n  if(screen==TIME_SETTINGS){openScreen(SETTINGS);return;}',"time swipe")
# Touch DOWN, MOVE, RELEASE. Existing V16 slider interception is replaced
# alongside the original touch function to avoid stale hit boxes.
replacefunc("void pollTouch(uint32_t now) {",r'''void pollTouch(uint32_t now){
 int x=0,y=0;bool down=readTouch(x,y);
 if(down)touchReleasedAt=0;
 else if(fingerDown){
  if(!touchReleasedAt)touchReleasedAt=now;
  if((uint32_t)(now-touchReleasedAt)<55)return;
 }
 if(down&&!fingerDown){
  fingerDown=true;downX=lastX=x;downY=lastY=y;downAt=now;
  personalizePressConsumed=false;frogSwipeJumpConsumed=false;
  if(screen==PERSONALIZE){tapped(x,y);personalizePressConsumed=true;}
  if(screen==SETTINGS){
   if(y>=154&&y<=212)frogVolumePct=pondPercent(x);
   if(y>=264&&y<=322)ambientVolumePct=pondPercent(x);
  }
  return;
 }
 if(down&&fingerDown){
  lastX=x;lastY=y;
  if(screen==SETTINGS){
   if(downY>=154&&downY<=212)frogVolumePct=pondPercent(x);
   if(downY>=264&&downY<=322)ambientVolumePct=pondPercent(x);
  }
  if(screen==FACE&&!frogSwipeJumpConsumed&&downX>=169&&downX<=299&&downY>=166&&downY<=312&&(downY-y)>=34&&abs(x-downX)<95){
   frogSwipeJumpConsumed=true;frogTapPending=false;
   frogCurrentAction=FROG_JUMP_ACTION;frogActionAt=now;
   frogActionNumber++;frogLastRenderedFrame=-1;
  }
  return;
 }
 if(!down&&fingerDown){
  fingerDown=false;
  int dx=lastX-downX,dy=lastY-downY;
  if(screen==SETTINGS&&((downY>=154&&downY<=212)||(downY>=264&&downY<=322))){
   prefs.putUChar("frogVolume",frogVolumePct);
   prefs.putUChar("ambientVolume",ambientVolumePct);
   return;
  }
  if(screen==TIME_SETTINGS){
   if(abs(dx)>SWIPE_THRESHOLD&&abs(dx)>abs(dy)*1.1f)openScreen(SETTINGS);
   else if(abs(dx)<40&&abs(dy)<40)pondTimeTap(downX,downY);
   return;
  }
  if(frogSwipeJumpConsumed){frogSwipeJumpConsumed=false;return;}
  if(screen==PERSONALIZE){
   personalizePressConsumed=false;
   if(abs(dx)>SWIPE_THRESHOLD&&abs(dx)>abs(dy)*1.2f)changeScreen(dx<0?1:-1);
   return;
  }
  if(screen==FACE&&downX>=169&&downX<=299&&downY>=166&&downY<=312&&dy>=34&&abs(dx)<95){
   frogTapPending=false;frogCurrentAction=FROG_JUMP_ACTION;frogActionAt=now;frogActionNumber++;frogLastRenderedFrame=-1;return;
  }
  if(abs(dx)>=SWIPE_THRESHOLD&&abs(dx)>abs(dy)*1.3f)changeScreen(dx<0?1:-1);
  else if(abs(dx)<45&&abs(dy)<45&&(uint32_t)(now-downAt)<900)tapped(downX,downY);
 }
}''')
swap('  frogVolumePct = min((uint8_t)100,prefs.getUChar("frogVolume",72));',
     '  frogVolumePct = min((uint8_t)100,prefs.getUChar("frogVolume",72));\n  ambientVolumePct=min((uint8_t)100,prefs.getUChar("ambientVolume",40));\n  clock24h=prefs.getBool("24hour",true);',"settings restore")
swap('  Serial.println("Ready: Frog Pond V7");',
     '  pondMountSD();pondRtcReady=pondReadClock();\n  Serial.println("Ready: Frog Pond V17");',"scene init")
swap('    else if (screen == SETTINGS) drawSettingsMenu();',
     '    else if (screen == SETTINGS) drawSettingsMenu();\n    else if (screen == TIME_SETTINGS) pondDrawTime();',"screen renderer")
swap('redraw = changedScreen || (screen == SETTINGS && now-prevFrameAt >= 125) || (screen == APPS && frogStepsRendered != frogSteps);',
     'redraw = changedScreen || ((screen == SETTINGS || screen == TIME_SETTINGS) && now-prevFrameAt >= 125) || (screen == APPS && frogStepsRendered != frogSteps);',"settings refresh")
for token in ('pondWriteClock()','pondMountSD();','pondDrawTime();','drawIsolatedHatFrame','prefs.getUChar("frogHat",255)'):
 if token not in s:raise RuntimeError("Required feature missing "+token)
p.write_text(s)
print("V17 RTC/dual volume/SD backgrounds patched:",p,len(s))
