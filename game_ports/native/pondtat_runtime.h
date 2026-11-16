#pragma once
#include <stdint.h>
#include "tat/tat_api.h"

// Original Tilt-a-Tron TAT API 1.3 ABI adapter for Frog Pond's Arduino shell.
// Existing hardware/display code supplies these hooks; games keep their upstream sources.
namespace pondtat {
using Present = void (*)(const uint16_t* pixels);
using ToneSink = void (*)(float f0,float f1,uint16_t ms,uint8_t wave,float volume,uint16_t delay);
using Exit = void (*)();
struct Motion {float ax,ay,az,gx,gy,gz;};
void init(Present present,ToneSink tone,Exit exitFn);
bool start(uint8_t slot);
void stop();
void frame(uint32_t now);
void touch(uint32_t now,bool down,int x,int y);
void motion(Motion v);
bool paused();
bool running();
uint8_t page();
void pause();
void resume();
void restart();
void exitToMenu();
const char* gameName(uint8_t slot);
}
