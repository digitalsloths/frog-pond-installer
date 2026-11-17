#!/usr/bin/env python3
"""Native TAT bridge: QMI8658 gyro + ES8311 single-owner queued game audio."""
from pathlib import Path
import sys
f=list(Path(sys.argv[1]).rglob("*.ino"))
assert len(f)==1
p=f[0];s=p.read_text()
def swap(a,b,reason):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(reason+": "+str(n)+" anchors")
 s=s.replace(a,b,1)
def replace_in_function(sig,old,new,reason):
 global s
 i=s.find(sig)
 if i<0:raise RuntimeError("missing function "+sig)
 b=s.index("{",i);d=0
 for j in range(b,len(s)):
  if s[j]=="{":d+=1
  elif s[j]=="}":
   d-=1
   if d==0:break
 part=s[i:j+1]
 n=part.count(old)
 if n!=1:raise RuntimeError(reason+": "+str(n)+" anchors in "+sig)
 part=part.replace(old,new,1)
 s=s[:i]+part+s[j+1:]
# Keep the board's I2S audio owned by frogAudioTask. Game thread queues
# short sound envelopes rather than writing concurrently from game loop.
swap('void tatPresentBitmap(const uint16_t* pixels){',r'''
struct PondGameTone {
  float f0,f1,volume;
  uint16_t ms,delay;
  uint8_t wave;
};
QueueHandle_t frogGameToneQueue=nullptr;
void tatGameTone(float f0,float f1,uint16_t ms,uint8_t wave,float volume,uint16_t delay){
  if(!frogGameToneQueue)return;
  PondGameTone t={f0,f1,volume,ms,delay,wave};
  xQueueSend(frogGameToneQueue,&t,0);
}
void tatPresentBitmap(const uint16_t* pixels){''',"tone sink")
swap('pondtat::init(tatPresentBitmap,nullptr,tatExitToCatalog);',
     'pondtat::init(tatPresentBitmap,tatGameTone,tatExitToCatalog);',
     "connect tone callbacks")
# Existing board driver supports accelerometer and gyro.
swap('    imu.enableAccelerometer();',r'''    imu.enableAccelerometer();
    imu.configGyroscope(SensorQMI8658::GYR_RANGE_512DPS,
                        SensorQMI8658::GYR_ODR_224_2Hz,
                        SensorQMI8658::LPF_MODE_0);
    imu.enableGyroscope();''',"enable gyro at setup")
swap('''      if(imu.getAccelerometer(ax,ay,az))
        pondtat::motion({ax,ay,az,0.0f,0.0f,0.0f});''',
     '''      float gx=0,gy=0,gz=0;
      if(imuAvailable){
        imu.getAccelerometer(ax,ay,az);
        imu.getGyroscope(gx,gy,gz);
      }
      pondtat::motion({ax,ay,az,gx,gy,gz});''',
     "feed full accelerometer gyro sample")
audio=r'''
    // Original Tilt-a-Tron game's 16-kHz square, triangle and noise tones.
    // Samples are stereo 16-bit and share the ES8311 writer with croaks.
    PondGameTone gt;
    if(frogGameToneQueue&&xQueueReceive(frogGameToneQueue,&gt,0)==pdTRUE){
      if(gt.delay)vTaskDelay(pdMS_TO_TICKS(gt.delay));
      const int samples=constrain((int)gt.ms*16,16,16000*3);
      const float duration=(float)samples/16000.0f;
      float phase=0;
      int16_t chunk[512]; // 256 interleaved stereo frames
      const float volume=constrain(gt.volume,0.0f,1.0f)*0.17f;
      for(int start=0;start<samples;start+=256){
        int frames=min(256,samples-start);
        for(int i=0;i<frames;i++){
          int sample=start+i;
          float progress=(float)sample/(float)samples;
          float hz=(gt.f1<=0?gt.f0:(gt.f0+(gt.f1-gt.f0)*progress));
          hz=constrain(hz,20.0f,7500.0f);
          phase+=6.2831853f*hz/16000.0f;
          if(phase>=6.2831853f)phase-=6.2831853f;
          float val;
          if(gt.wave==TAT_NOISE){
            val=((int)(esp_random()&65535)-32768)/32768.0f;
          }else if(gt.wave==TAT_TRIANGLE){
            float q=phase/6.2831853f;
            val=1.0f-4.0f*fabsf(q-0.5f);
          }else val=(phase<3.14159265f)?1.0f:-1.0f;
          float time=(float)sample/16000.0f;
          float envelope=min(1.0f,min(time/0.008f,(duration-time)/0.008f));
          int16_t pcm=(int16_t)(val*volume*envelope*32767.0f);
          chunk[i*2]=pcm;chunk[i*2+1]=pcm;
        }
        frogI2S.write((uint8_t*)chunk,frames*4);
      }
    }
'''
replace_in_function('void frogAudioTask(void *param) {',
                    '    vTaskDelay(pdMS_TO_TICKS(10));',
                    audio+'    vTaskDelay(pdMS_TO_TICKS(10));',
                    "TAT tone synthesis in existing audio task")
swap('xTaskCreatePinnedToCore(frogAudioTask,"frog_audio",6144,NULL,1,NULL,1);',
     'frogGameToneQueue=xQueueCreate(24,sizeof(PondGameTone));\n  xTaskCreatePinnedToCore(frogAudioTask,"frog_audio",6144,NULL,1,NULL,1);',
     "allocate queue before existing I2S task")
for t in ('frogGameToneQueue=xQueueCreate','imu.enableGyroscope();',
          'frogI2S.write((uint8_t*)chunk,frames*4)','tatGameTone,tatExitToCatalog'):
 if t not in s:raise RuntimeError("Missing audio/gyro feature "+t)
p.write_text(s)
print("Native TAT ES8311 queued wave synthesis and QMI8658 accelerometer+gyro enabled.")
