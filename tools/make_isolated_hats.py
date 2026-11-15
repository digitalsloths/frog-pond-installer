#!/usr/bin/env python3
"""Create compact, transparent RGB565 hat assets from user's isolated 2026-11-15 PNGs.
Transparency encoded as sentinel 0x0001. Position tables are pixel-verified
against the 20-frame reference sheets (32x32 coordinates).
"""
import base64,struct,zlib,sys,pathlib
ASSETS=[["cowboy",21,10,"eNqdkMEJACEMBLW1PPynBFvIy2982oaVyTVyLEs4EDy4Yx9KMskuySn/UGmluea0qiv+Z252MbFV+YqdWNfZQ9cAvZN0hCf6D3sN1pmKu8Rc4bkLSZB5ds6ApNsubkYntoNlNRRZOR8c2Td9vfYN55VtPQ==","5,5,5,6,5,5,5,5,5,7,5,6,6,5,5,5,6,5,5,5","13,13,13,12,13,12,12,12,14,3,14,11,10,5,12,12,10,3,12,10"],["pirate",22,16,"eNpjZGAkE2oCwZlKGMSv8rwjMsSnGqI2dm/sXohaTU18KkGqfk3+NRnCwq4a5E6IWSB1MJUQd6C6fJmEjyHClQg3YLocpBKiFkT/mowgkU2AqIaoBUGWHawvQPDNRwhkfYFQD3E5TC3LDhCEqEZAmDnLJGCuAEGIWnQIkYOpxA9ZdhAf66SoZX1BG7XIEAAU9oqE","4,4,4,5,4,4,4,4,4,6,4,5,5,4,4,4,5,4,4,4","11,11,11,10,11,10,10,10,12,1,12,9,8,3,10,10,8,1,10,8"],["tophat",17,11,"eNpjZGAkCi6TWCahiQaWSWBT4WN43hEEfQwHqwqWHSw7WF+wvnjz8c3H97/e/3rzkfUFyw7iVYBsgEDMEEG1CRcEACoRTms=","6,6,6,7,6,6,6,6,6,8,6,7,7,6,6,6,7,6,6,6","11,11,11,10,11,10,10,10,12,2,12,10,9,4,10,10,9,2,10,8"],["viking",17,9,"eNpjZGAkCEPv4ZaT/A4iJ56F0NjkIbonng29B4KLm5yKlK8oX1m026locRNEdOJZiNqJZyeeRZUH8UCiCPOcikAQWQVIDaprF+1etHviWRC5aDeMh6wCpBsTMjIQBwFlmEo3","6,6,5,7,6,6,6,6,6,8,6,7,7,6,6,6,7,6,6,6","13,13,13,12,13,12,12,12,14,4,14,12,11,6,12,12,11,4,12,10"],["clown",19,15,"eNqdkTEKhDAQRU2VPq2l3mKrsHgGr2HnGfYaKT2Adc4iKRQCihY2Wdx8hpAIgWWXD5GQ55vJhBXshxzXfBpXL5Rhrxelpb0zEz8u45Smc0Rp46RNubICJW0wIcYZB/98RipnalYwzRpNaU+gUQ2mrZ8445FK68FEHjBlFahmlRYOpRF0jXpbD+bxAtUKxkN1MKFbmN7PVhDlV56boP/Tm1oxdtiNnbflZ81hIgocfYcdk7hT4SyG7vftLemGrPg3Hyjcosw=","6,6,6,7,6,6,6,6,6,8,6,7,7,6,6,6,7,6,6,6","12,12,12,11,12,11,11,11,13,3,13,11,10,5,11,11,10,3,11,9"],["funnyglasses",16,12,"eNpjZGAkCB0tDwUeCoSxkXnEQQhAZjOgyCJoBgxRBEvrybNNDFjMZIDKXv3me/XZJuz6n226+s3w3aojypNgKlBdoDzJ8B0I+l5VnoTuPoj/lSdBIMT/qP47FAgShUEQj/iwAQDAZyh7","7,7,7,8,7,7,7,7,7,9,7,8,8,7,7,7,8,7,7,7","17,17,17,16,17,16,16,16,18,7,18,15,14,9,16,16,14,7,16,14"]]
target=pathlib.Path(sys.argv[1])
target.mkdir(parents=True,exist_ok=True)
out=['#pragma once','#include <Arduino.h>','#define ISOLATED_HAT_COUNT 6']
for i,(name,w,h,data,xs,ys) in enumerate(ASSETS):
    px=list(struct.unpack('<%dH'%(w*h),zlib.decompress(base64.b64decode(data))))
    assert len(px)==w*h
    out.append('static const uint16_t ISOLATED_HAT_'+str(i)+'[] PROGMEM = {')
    for st in range(0,len(px),20):
        out.append('  '+','.join('0x%04X'%v for v in px[st:st+20])+',')
    out.append('};')
out.extend([
 'static const uint16_t * const ISOLATED_HAT_PIXELS[6] = {'+','.join('ISOLATED_HAT_'+str(i) for i in range(6))+'};',
 'static const uint8_t ISOLATED_HAT_W[6] = {'+','.join(str(v[1]) for v in ASSETS)+'};',
 'static const uint8_t ISOLATED_HAT_H[6] = {'+','.join(str(v[2]) for v in ASSETS)+'};',
 'static const int8_t ISOLATED_HAT_X[6][20] = {',
 ])
for item in ASSETS: out.append('  {'+item[4]+'},')
out.append('};')
out.append('static const int8_t ISOLATED_HAT_Y[6][20] = {')
for item in ASSETS: out.append('  {'+item[5]+'},')
out.append('};')
(target/'frog_isolated_hats.h').write_text('\n'.join(out)+'\n')
print('Created isolated hats, exact RGB565 pixels and 20-frame offsets')
