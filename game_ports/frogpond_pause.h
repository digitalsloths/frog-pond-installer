#pragma once
// Reusable, platform-independent pause-and-exit controller for Frog Pond's future
// Tilt-a-Tron games. Touch coordinates must already be corrected for orientation.
#include <stdint.h>
namespace frogpond {
class GamePauseController {
public:
 enum Action : uint8_t { NONE, PAUSE, RESUME, RESTART, EXIT_TO_GAMES };
 enum Mode : uint8_t { RUNNING, PAUSED };
 static constexpr int TOP_EDGE=36, PULL_DISTANCE=72;
 Mode mode() const { return mode_; }
 bool isPaused() const { return mode_==PAUSED; }
 void startGame(uint8_t index,uint8_t page) {
   index_=index; page_=page; mode_=RUNNING; edge_=false;
 }
 uint8_t gameIndex() const { return index_; }
 uint8_t returnPage() const { return page_; }
 bool touchDown(int x,int y) {
   (void)x;
   edge_=mode_==RUNNING && y>=0 && y<=TOP_EDGE;
   firstY_=y;
   return edge_ || mode_==PAUSED;
 }
 Action touchMove(int x,int y) {
   (void)x;
   if(mode_==PAUSED) return NONE;
   if(edge_ && y-firstY_>=PULL_DISTANCE) {
     edge_=false; mode_=PAUSED; return PAUSE;
   }
   if(edge_ && y<firstY_-18) edge_=false;
   return NONE;
 }
 Action touchUp(int x,int y) {
   edge_=false;
   if(mode_!=PAUSED) return NONE;
   // Resume, Restart, Exit to Games: large button hit targets.
   if(x>=95 && x<=371) {
     if(y>=132 && y<210) { mode_=RUNNING; return RESUME; }
     if(y>=223 && y<301) { mode_=RUNNING; return RESTART; }
     if(y>=314 && y<=396) { mode_=RUNNING; return EXIT_TO_GAMES; }
   }
   return NONE;
 }
 void forcePause() { mode_=PAUSED; edge_=false; }
private:
 Mode mode_=RUNNING;
 bool edge_=false;
 int firstY_=0;
 uint8_t index_=0,page_=0;
};
}
