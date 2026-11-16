// Frog Pond host-side implementation of the original Tilt-a-Tron TAT API 1.3.
// The upstream games remain byte-for-byte unchanged; this is a compatibility host.
#include "pondtat_runtime.h"
#include <Arduino.h>
#include <Preferences.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <math.h>
#include <algorithm>
#include <climits>
#include <vector>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "lodepng.h"
#include "frogpond_pause.h"

namespace wc { extern const uint8_t kFont5x7[][5]; }
struct tat_canvas {
 int w=0,s=2,used=1;
 uint8_t* pixels=nullptr;
 uint16_t pal[256]={};
};
struct tat_sheet {
 int w=0,h=0,fw=0,fh=0;
 uint8_t* pixels=nullptr;
};

extern "C" {
extern const tat_game_t tat_game_echo,tat_game_starfall,tat_game_radar,tat_game_maze;
extern const tat_game_t tat_game_racer,tat_game_tiltatris,tat_game_star,tat_game_pindrop;
extern const tat_game_t tat_game_breakout,tat_game_skatergirlz,tat_game_jump;
}
namespace {
const tat_game_t* const GAMES[11]={
 &tat_game_echo,&tat_game_starfall,&tat_game_radar,&tat_game_maze,
 &tat_game_racer,&tat_game_tiltatris,&tat_game_star,&tat_game_pindrop,
 &tat_game_breakout,&tat_game_skatergirlz,&tat_game_jump
};
const tat_game_t* game=nullptr;
uint8_t slot=0,returnPage=0;
pondtat::Present presenter=nullptr;
pondtat::ToneSink sound=nullptr;
pondtat::Exit exitToMenuFn=nullptr;
std::vector<void*> allocations;
std::vector<tat_canvas_t*> canvases;
std::vector<tat_sheet_t*> sheets;
Preferences saved;
tat_api_t api{};
tat_input_t inputState{};
tat_gestures_t gestures{};
frogpond::GamePauseController pauseControl;
uint16_t* framebuffer=nullptr;
uint16_t *polarAngle=nullptr,*polarRadius=nullptr;
bool pauseOverlay=false,menuOpened=false,wasDown=false,edgeWasDown=false;
int touchStartX=0,touchStartY=0,touchLastX=0,touchLastY=0;
uint32_t lastFrame=0;
uint32_t lastTouch=0;
float t0=0;
static inline tat_canvas* cv(tat_canvas_t* p){return reinterpret_cast<tat_canvas*>(p);}
static inline tat_sheet* sh(tat_sheet_t* p){return reinterpret_cast<tat_sheet*>(p);}
static inline uint16_t nativeRGB(uint8_t r,uint8_t g,uint8_t b){
 return uint16_t((r&0xf8)<<8)|uint16_t((g&0xfc)<<3)|uint16_t(b>>3);
}
static inline void put(tat_canvas* c,int x,int y,uint8_t col){
 if(c&&x>=0&&y>=0&&x<c->w&&y<c->w)c->pixels[y*c->w+x]=col;
}
static tat_color_t rgb(uint8_t r,uint8_t g,uint8_t b){return nativeRGB(r,g,b);}
static void home(){if(exitToMenuFn)exitToMenuFn();}
static void logGame(const char* fmt,...){
 char buf[256];va_list args;va_start(args,fmt);
 vsnprintf(buf,sizeof(buf),fmt,args);va_end(args);Serial.println(buf);
}
static int64_t nowUS(){return esp_timer_get_time();}
static uint32_t rng(){return esp_random();}
static const tat_input_t* in(){return &inputState;}
static const tat_gestures_t* ges(){return &gestures;}
static void* alloc(size_t bytes){
 if(!bytes)return nullptr;
 void* ptr=heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
 if(!ptr)ptr=malloc(bytes);
 if(ptr)allocations.push_back(ptr);
 return ptr;
}
static void freeTracked(void* p){
 if(!p)return;
 auto it=std::find(allocations.begin(),allocations.end(),p);
 if(it!=allocations.end())allocations.erase(it);
 free(p);
}
static tat_canvas_t* canvasCreate(int scale,int size){
 if(scale!=2&&scale!=3)scale=2;
 tat_canvas* c=new tat_canvas;
 c->s=scale;
 c->w=size>0?size:(466+scale-1)/scale;
 c->pixels=(uint8_t*)alloc((size_t)c->w*c->w);
 if(!c->pixels){delete c;return nullptr;}
 memset(c->pixels,0,(size_t)c->w*c->w);
 canvases.push_back(c);
 return reinterpret_cast<tat_canvas_t*>(c);
}
static void canvasDestroy(tat_canvas_t* p){
 if(!p)return;tat_canvas* c=cv(p);
 auto it=std::find(canvases.begin(),canvases.end(),p);
 if(it!=canvases.end())canvases.erase(it);
 freeTracked(c->pixels);delete c;
}
static int canvasWidth(tat_canvas_t* p){return cv(p)->w;}
static uint8_t* canvasPixels(tat_canvas_t* p){return cv(p)->pixels;}
static int colorDistance(uint16_t a,uint16_t b){
 int dr=(a>>11)-(b>>11),dg=((a>>5)&63)-((b>>5)&63),db=(a&31)-(b&31);
 return 2*dr*dr+dg*dg+2*db*db;
}
static uint8_t nearestColor(tat_canvas* c,uint16_t color){
 int best=1,dist=INT_MAX;
 for(int i=1;i<c->used;i++){
  if(c->pal[i]==color)return i;
  int d=colorDistance(c->pal[i],color);
  if(d<dist){best=i;dist=d;}
 }
 if(c->used<256){c->pal[c->used]=color;return (uint8_t)c->used++;}
 return best;
}
static uint8_t canvasColor(tat_canvas_t* p,tat_color_t c){return nearestColor(cv(p),c);}
static uint8_t canvasReserve(tat_canvas_t* p,int n){
 tat_canvas* c=cv(p);int start=c->used;
 if(n<0||start+n>256)return 0;
 c->used+=n;return start;
}
static void canvasSetColor(tat_canvas_t* p,uint8_t index,tat_color_t color){
 tat_canvas* c=cv(p);c->pal[index]=color;
 if(c->used<=index)c->used=(int)index+1;
}
static void canvasSetPalette(tat_canvas_t* p,const tat_color_t* colors,int n){
 if(!p||!colors)return;tat_canvas* c=cv(p);
 if(n>256)n=256;if(n<1)return;
 memcpy(c->pal,colors,n*sizeof(tat_color_t));
 c->pal[0]=0;c->used=n;
}
static void canvasClear(tat_canvas_t* p,uint8_t color){
 tat_canvas* c=cv(p);memset(c->pixels,color,(size_t)c->w*c->w);
}
static void canvasPixel(tat_canvas_t* p,int x,int y,uint8_t col){put(cv(p),x,y,col);}
static void canvasFillRect(tat_canvas_t* p,int x,int y,int w,int h,uint8_t col){
 if(!p||w<=0||h<=0)return;tat_canvas* c=cv(p);
 int x0=std::max(0,x),y0=std::max(0,y),x1=std::min(c->w,x+w),y1=std::min(c->w,y+h);
 if(x1<=x0||y1<=y0)return;
 for(int row=y0;row<y1;row++)memset(c->pixels+row*c->w+x0,col,x1-x0);
}
static void canvasRect(tat_canvas_t* p,int x,int y,int w,int h,uint8_t col){
 canvasFillRect(p,x,y,w,1,col);canvasFillRect(p,x,y+h-1,w,1,col);
 canvasFillRect(p,x,y,1,h,col);canvasFillRect(p,x+w-1,y,1,h,col);
}
static void canvasLine(tat_canvas_t* p,int x0,int y0,int x1,int y1,uint8_t col){
 int dx=abs(x1-x0),sx=x0<x1?1:-1,dy=-abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;
 while(true){canvasPixel(p,x0,y0,col);if(x0==x1&&y0==y1)break;
 int e2=2*err;if(e2>=dy){err+=dy;x0+=sx;}if(e2<=dx){err+=dx;y0+=sy;}}
}
static void canvasFillCircle(tat_canvas_t* p,int cx,int cy,int r,uint8_t col){
 for(int dy=-r;dy<=r;dy++){
  int dx=(int)sqrtf((float)(r*r-dy*dy));
  canvasFillRect(p,cx-dx,cy+dy,dx*2+1,1,col);
 }
}
static int textWidth(const char* s,int scale,bool bold){
 (void)bold;return s?(int)strlen(s)*6*std::max(scale,1):0;
}
static int canvasText(tat_canvas_t* p,int x,int y,const char* s,uint8_t col,int scale,bool bold){
 if(!p||!s)return x;if(scale<1)scale=1;
 for(const unsigned char* q=(const unsigned char*)s;*q;q++){
  unsigned ch=*q;if(ch<32||ch>126)ch='?';
  for(int cx=0;cx<5;cx++){
   uint8_t bits=wc::kFont5x7[ch-32][cx];
   for(int cy=0;cy<7;cy++)if(bits&(1u<<cy)){
    canvasFillRect(p,x+cx*scale,y+cy*scale,scale+(bold?1:0),scale,col);
   }
  }x+=6*scale;
 }
 return x;
}
static void canvasTextCentered(tat_canvas_t* p,int cx,int cy,const char* s,uint8_t col,int scale,bool bold){
 canvasText(p,cx-textWidth(s,scale,bold)/2,cy,s,col,scale,bold);
}
static tat_sheet_t* sheetLoad(tat_canvas_t* p,const void* png,size_t len,int fw,int fh){
 if(!p||!png||len==0||fw<1||fh<1)return nullptr;
 unsigned char* pixels=nullptr;unsigned w=0,h=0;
 unsigned err=lodepng_decode32(&pixels,&w,&h,(const unsigned char*)png,len);
 if(err||!pixels||!w||!h)return nullptr;
 tat_sheet* sheet=new tat_sheet;
 sheet->w=w;sheet->h=h;sheet->fw=fw;sheet->fh=fh;
 sheet->pixels=(uint8_t*)alloc((size_t)w*h);
 if(!sheet->pixels){free(pixels);delete sheet;return nullptr;}
 tat_canvas* c=cv(p);
 for(size_t i=0;i<(size_t)w*h;i++){
  uint8_t* rgba=pixels+i*4;
  sheet->pixels[i]=rgba[3]<128?0:nearestColor(c,nativeRGB(rgba[0],rgba[1],rgba[2]));
 }
 free(pixels);sheets.push_back(sheet);
 return reinterpret_cast<tat_sheet_t*>(sheet);
}
static void sheetSprite(tat_canvas_t* p,tat_sheet_t* sheet,int frame,int x,int y,bool flip){
 if(!p||!sheet)return;tat_sheet* shh=sh(sheet);
 int cols=shh->w/shh->fw,rows=shh->h/shh->fh;if(!cols||!rows)return;
 frame=(frame%(cols*rows)+(cols*rows))%(cols*rows);
 int fx=(frame%cols)*shh->fw,fy=(frame/cols)*shh->fh;
 for(int yy=0;yy<shh->fh;yy++)for(int xx=0;xx<shh->fw;xx++){
  int sx=flip?shh->fw-1-xx:xx;
  uint8_t color=shh->pixels[(fy+yy)*shh->w+fx+sx];
  if(color)canvasPixel(p,x+xx,y+yy,color);
 }
}
static void sheetScaled(tat_canvas_t* p,tat_sheet_t* sheet,int frame,float x,float y,float sx,float sy,bool flip){
 if(!p||!sheet||sx<=0||sy<=0)return;tat_sheet* shh=sh(sheet);
 int dw=std::max(1,(int)(shh->fw*sx+.5f)),dh=std::max(1,(int)(shh->fh*sy+.5f));
 int cols=shh->w/shh->fw,rows=shh->h/shh->fh;if(!cols||!rows)return;
 frame=(frame%(cols*rows)+(cols*rows))%(cols*rows);
 int fx=(frame%cols)*shh->fw,fy=(frame/cols)*shh->fh;
 int left=(int)floorf(x-dw/2.0f+.5f),top=(int)floorf(y-dh+.5f);
 for(int j=0;j<dh;j++)for(int i=0;i<dw;i++){
  int px=std::min(shh->fw-1,i*shh->fw/dw),py=std::min(shh->fh-1,j*shh->fh/dh);
  if(flip)px=shh->fw-1-px;
  uint8_t col=shh->pixels[(fy+py)*shh->w+fx+px];
  if(col)canvasPixel(p,left+i,top+j,col);
 }
}
static void presentCanvas(tat_canvas_t* p,float angle){
 if(!p||!presenter||!framebuffer)return;
 tat_canvas* c=cv(p);const int n=466;
 float co=cosf(angle),si=sinf(angle),cc=(c->w-1)/2.0f,sc=232.5f;
 for(int y=0;y<n;y++){
  int row=y*n;
  for(int x=0;x<n;x++){
   float dx=x-sc,dy=y-sc;
   float u=(cc+(co*dx-si*dy)/c->s),v=(cc+(si*dx+co*dy)/c->s);
   int sx=(int)floorf(u+.5f),sy=(int)floorf(v+.5f);
   framebuffer[row+x]=(sx>=0&&sy>=0&&sx<c->w&&sy<c->w)?
     c->pal[c->pixels[sy*c->w+sx]]:c->pal[0];
  }
 }
 presenter(framebuffer);
}
static void canvasPresent(tat_canvas_t* c){presentCanvas(c,0);}
static void canvasPresentRotated(tat_canvas_t* c,float a){presentCanvas(c,a);}
static void menuOpen(){menuOpened=true;pauseControl.forcePause();}
static void menuClose(){menuOpened=false;}
static bool menuIsOpen(){return menuOpened;}
static void menuInvalidate(){}
static int menuUpdate(){return TAT_MENU_NONE;}
static tat_menu_row_t menuSoundRow(){
 tat_menu_row_t row={"SOUND","ON",0};return row;
}
static void menuToggleSound(){}
static tat_color_t uiColor(int which){
 const uint16_t col[]={0xffff,0xa534,0x6b4d,0xf7be,0xff00,0x27ec,0xf800};
 return col[constrain(which,0,6)];
}
static void menuDraw(const tat_menu_row_t*,int,const char*){}
static void soundTone(const tat_tone_t* tone){
 if(sound&&tone)sound(tone->f0,tone->f1,tone->ms,tone->wave,tone->volume,tone->delay_ms);
}
static int volume(){return 3;}
static void saveGet(const char* key,int* value,int limit){
 if(!key||!value)return;int got=saved.getInt(key,*value);
 if(limit>0&&(got<0||got>=limit))return;*value=got;
}
static void saveSet(const char* key,int v){if(key)saved.putInt(key,v);}
static const void* asset(const char* name,size_t* len){
 if(len)*len=0;
 if(!game||!name||!game->assets)return nullptr;
 for(int i=0;i<game->asset_count;i++){
  const tat_asset_t& a=game->assets[i];
  if(a.name&&strcmp(a.name,name)==0){
   if(len)*len=(size_t)(a.end-a.data);
   return a.data;
  }
 }
 return nullptr;
}
static void canvasBanner(tat_canvas_t* p,int cx,int y,int w,const tat_banner_t* b){
 if(!p||!b)return;int lines=1+(b->mid?1:0)+(b->bottom?1:0);
 int height=lines*17+12,top=y-4;
 canvasFillRect(p,cx-w/2,top,w,height,b->panel);
 if(b->bars){
  canvasFillRect(p,cx-w/2,top,w,2,b->border);
  canvasFillRect(p,cx-w/2,top+height-2,w,2,b->border);
 }else canvasRect(p,cx-w/2,top,w,height,b->border);
 canvasTextCentered(p,cx,top+6,b->top,b->top_color,1,true);
 if(b->mid)canvasTextCentered(p,cx,top+22,b->mid,b->mid_color,1,false);
 if(b->bottom)canvasTextCentered(p,cx,top+(lines==3?38:22),b->bottom,b->bottom_color,1,b->bottom_bold);
}
static const uint16_t* polar(bool angle){
 uint16_t*& out=angle?polarAngle:polarRadius;
 if(out)return out;
 out=(uint16_t*)heap_caps_malloc(466*466*2,MALLOC_CAP_SPIRAM);
 if(!out)return nullptr;
 for(int y=0;y<466;y++)for(int x=0;x<466;x++){
  float dx=x-232.5f,dy=y-232.5f;
  float n=angle?atan2f(dy,dx)*65536.0f/6.2831853f:sqrtf(dx*dx+dy*dy)*16.0f;
  out[y*466+x]=angle?(uint16_t)(int)n:(uint16_t)std::min(65535,(int)n);
 }
 return out;
}
static const uint16_t* polarAngles(){return polar(true);}
static const uint16_t* polarRadii(){return polar(false);}
static const uint8_t* sheetPixels(tat_sheet_t* p){return p?sh(p)->pixels:nullptr;}
static void sheetInfo(tat_sheet_t* p,int* w,int* h,int* fw,int* fh){
 if(!p)return;tat_sheet* q=sh(p);
 if(w)*w=q->w;if(h)*h=q->h;if(fw)*fw=q->fw;if(fh)*fh=q->fh;
}
static void clearAll(){
 if(game&&game->leave)game->leave();
 if(game&&game->unload)game->unload();
 for(auto s:sheets){freeTracked(sh(s)->pixels);delete sh(s);}
 sheets.clear();
 for(auto c:canvases){freeTracked(cv(c)->pixels);delete cv(c);}
 canvases.clear();
 for(void* ptr:allocations)free(ptr);
 allocations.clear();
 saved.end();game=nullptr;
 menuOpened=false;pauseOverlay=false;wasDown=false;
}
static void bindAPI(){
 api.major=TAT_API_MAJOR;api.minor=TAT_API_MINOR;
 api.rgb=rgb;api.go_home=home;api.log=logGame;api.now_us=nowUS;api.random=rng;
 api.input=in;api.gestures=ges;
 api.alloc=alloc;api.free=freeTracked;
 api.canvas_create=canvasCreate;api.canvas_destroy=canvasDestroy;
 api.canvas_width=canvasWidth;api.canvas_pixels=canvasPixels;
 api.canvas_color=canvasColor;api.canvas_reserve=canvasReserve;api.canvas_set_color=canvasSetColor;
 api.canvas_clear=canvasClear;api.canvas_pixel=canvasPixel;api.canvas_fill_rect=canvasFillRect;
 api.canvas_rect=canvasRect;api.canvas_line=canvasLine;api.canvas_fill_circle=canvasFillCircle;
 api.canvas_text=canvasText;api.canvas_text_centered=canvasTextCentered;
 api.sheet_load=sheetLoad;api.canvas_sprite=sheetSprite;api.canvas_sprite_scaled=sheetScaled;
 api.canvas_present=canvasPresent;api.canvas_present_rotated=canvasPresentRotated;
 api.menu_open=menuOpen;api.menu_close=menuClose;api.menu_is_open=menuIsOpen;
 api.menu_invalidate=menuInvalidate;api.menu_update=menuUpdate;api.menu_draw=menuDraw;
 api.menu_sound_row=menuSoundRow;api.menu_toggle_sound=menuToggleSound;api.ui_color=uiColor;
 api.tone=soundTone;api.volume=volume;api.save_get=saveGet;api.save_set=saveSet;api.asset=asset;
 api.canvas_banner=canvasBanner;api.polar_angles=polarAngles;api.polar_radii=polarRadii;
 api.text_width=textWidth;api.sheet_pixels=sheetPixels;api.sheet_info=sheetInfo;
 api.canvas_set_palette=canvasSetPalette;
}
}
namespace pondtat {
void init(Present p,ToneSink s,Exit e){
 presenter=p;sound=s;exitToMenuFn=e;
 if(!framebuffer)framebuffer=(uint16_t*)heap_caps_malloc(466*466*2,MALLOC_CAP_SPIRAM);
 bindAPI();
}
bool start(uint8_t index){
 if(index>=11||!framebuffer||!presenter)return false;
 clearAll();slot=index;returnPage=index/4;
 game=GAMES[slot];
 if(!game||game->magic!=TAT_GAME_MAGIC||game->api_major!=TAT_API_MAJOR) {
  game=nullptr;return false;
 }
 String ns=String("tat_")+game->id;
 if(!saved.begin(ns.c_str(),false)){game=nullptr;return false;}
 memset(&inputState,0,sizeof(inputState));memset(&gestures,0,sizeof(gestures));
 inputState.tilt.az=1.0f;
 pauseControl.startGame(slot,returnPage);
 lastFrame=millis();
 if(game->begin)game->begin(&api);
 if(game->enter)game->enter();
 if(game->redraw)game->redraw();
 return true;
}
void stop(){clearAll();}
bool paused(){return pauseControl.isPaused();}
bool running(){return game!=nullptr;}
uint8_t page(){return returnPage;}
const char* gameName(uint8_t i){return i<11?GAMES[i]->name:"";}
void motion(Motion m){
 inputState.tilt={m.ax,m.ay,m.az,m.gx,m.gy,m.gz};
}
void frame(uint32_t now){
 if(!game||pauseControl.isPaused())return;
 float dt=(now-lastFrame)*.001f;
 if(dt>0.05f)dt=.05f;
 if(dt<0)dt=0;
 lastFrame=now;
 if(game->update)game->update(dt);
 if(game->draw)game->draw();
 inputState.pressed=inputState.released=inputState.clicked=inputState.long_press=inputState.double_clicked=0;
 inputState.touch.pressed=inputState.touch.released=0;
 gestures={};
}
void touch(uint32_t now,bool down,int x,int y){
 if(!game)return;
 if(down&&!wasDown){
  wasDown=true;touchStartX=touchLastX=x;touchStartY=touchLastY=y;lastTouch=now;
  edgeWasDown=(y<=frogpond::GamePauseController::TOP_EDGE);
  pauseControl.touchDown(x,y);
  if(!pauseControl.isPaused()&&!edgeWasDown){
   inputState.touch.down=1;inputState.touch.pressed=1;inputState.touch.x=x;inputState.touch.y=y;
  }
 }else if(down&&wasDown){
  touchLastX=x;touchLastY=y;
  if(pauseControl.touchMove(x,y)==frogpond::GamePauseController::PAUSE){
   pauseOverlay=true;inputState.touch.down=0;inputState.touch.released=1;return;
  }
  if(!pauseControl.isPaused()&&!edgeWasDown){
   inputState.touch.x=x;inputState.touch.y=y;
  }
 }else if(!down&&wasDown){
  wasDown=false;
  if(pauseOverlay){pauseOverlay=false;return;}
  if(pauseControl.isPaused()){
   auto action=pauseControl.touchUp(touchLastX,touchLastY);
   if(action==frogpond::GamePauseController::RESTART)restart();
   else if(action==frogpond::GamePauseController::EXIT_TO_GAMES)exitToMenu();
   return;
  }
  if(edgeWasDown){edgeWasDown=false;return;}
  inputState.touch.down=0;inputState.touch.released=1;
  gestures.x=touchStartX;gestures.y=touchStartY;
  int dx=touchLastX-touchStartX,dy=touchLastY-touchStartY;
  if(abs(dx)<35&&abs(dy)<35)gestures.tap=1;
  else if(abs(dx)>70&&abs(dx)>abs(dy)*1.3f){
    if(dx<0)pauseControl.forcePause();
    else gestures.swipe_right=1;
  }
 }
}
void pause(){pauseControl.forcePause();}
void resume(){lastFrame=millis();/* Resume handled by touchUp */ }
void restart(){uint8_t at=slot;start(at);}
void exitToMenu(){uint8_t keep=returnPage;stop();returnPage=keep;if(exitToMenuFn)exitToMenuFn();}
}
