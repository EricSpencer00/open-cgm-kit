/**
 * @file lmp91000.h
 * @brief LMP91000 register map and encoders (TI SNAS506I, Dec 2014). Hardware-free.
 */

#pragma once

#include <stdint.h>

namespace lmp91000 {

constexpr uint8_t kAddress = 0x48; /* 7-bit, fixed (1001 000) */

constexpr uint8_t kRegStatus = 0x00; /* bit0 = 1 when ready */
constexpr uint8_t kRegLock = 0x01;   /* bit0 = 0 unlocks TIACN and REFCN; power-on 1 */
constexpr uint8_t kRegTiacn = 0x10;  /* [4:2] TIA_GAIN, [1:0] RLOAD */
constexpr uint8_t kRegRefcn = 0x11;  /* [7] source, [6:5] INT_Z, [4] sign, [3:0] BIAS */
constexpr uint8_t kRegModecn = 0x12; /* [7] FET_SHORT, [2:0] OP_MODE */

constexpr uint8_t kLockWrite = 0x00;
constexpr uint8_t kLockProtect = 0x01;

constexpr uint8_t kModeDeepSleep = 0x00;
constexpr uint8_t kModeStandby = 0x02;
constexpr uint8_t kMode3Lead = 0x03;
constexpr uint8_t kModeTempTiaOn = 0x07; /* VOUT = temperature, TIA output on C2 */
constexpr uint8_t kFetShort = 0x80;      /* shorts WE to RE while the cell is idle */

constexpr uint8_t kRload100 = 0x03;

/* TIA_GAIN codes 1..7. Code 0 selects an external resistor and is not supported. */
constexpr uint32_t kGainOhms[8] = {0, 2750, 3500, 7000, 14000, 35000, 120000, 350000};

inline bool gainOhms(uint8_t code, uint32_t* ohms) {
  if (code < 1 || code > 7) return false;
  *ohms = kGainOhms[code];
  return true;
}

inline uint8_t tiacn(uint8_t gainCode, uint8_t rload = kRload100) {
  return static_cast<uint8_t>((gainCode << 2) | (rload & 0x03));
}

/* BIAS field 0..13 as percent of VREF (datasheet 7.6.4; codes 1110/1111 are not defined). */
constexpr uint8_t kBiasPercent[14] = {0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24};

/* INT_Z field -> percent of VREF. Code 3 bypasses the zero and is not supported. */
constexpr uint8_t kIntZPercent[3] = {20, 50, 67};

struct Reference {
  uint8_t refcn;    /* REFCN register value, internal source */
  int16_t biasMv;   /* quantized WE-RE bias actually selected */
  uint16_t zeroMv;  /* internal zero (TIA non-inverting input) */
};

/**
 * Choose REFCN for a requested WE-RE bias. Positive bias uses 50 % internal zero;
 * negative bias must use 67 % (datasheet note 7 on VOS_RW). Zero bias uses 50 %.
 * Returns false if |bias| exceeds 24 % of VREF by more than half a step.
 */
inline bool reference(int16_t requestedMv, uint16_t vrefMv, Reference* out) {
  const bool negative = requestedMv < 0;
  const int32_t magnitude = negative ? -static_cast<int32_t>(requestedMv) : requestedMv;
  uint8_t best = 0;
  int32_t bestError = 0x7fffffff;
  for (uint8_t i = 0; i < 14; i++) {
    const int32_t mv = static_cast<int32_t>(vrefMv) * kBiasPercent[i] / 100;
    const int32_t error = magnitude > mv ? magnitude - mv : mv - magnitude;
    if (error < bestError) {
      bestError = error;
      best = i;
    }
  }
  if (magnitude > static_cast<int32_t>(vrefMv) * 25 / 100) return false;
  const uint8_t intZ = negative ? 2 : 1;
  const int16_t quantized = static_cast<int16_t>(static_cast<int32_t>(vrefMv) * kBiasPercent[best] / 100);
  out->refcn = static_cast<uint8_t>((intZ << 5) | ((negative ? 0u : 1u) << 4) | best);
  out->biasMv = (negative && best != 0) ? static_cast<int16_t>(-quantized) : quantized;
  out->zeroMv = static_cast<uint16_t>(static_cast<uint32_t>(vrefMv) * kIntZPercent[intZ] / 100);
  return true;
}

/* Temperature output, linear fit over 20..50 C from datasheet Table 1: V = -8.16 mV/C * T + 1562.2 mV. */
inline bool tempCentiC(int32_t voutMv, int16_t* centiC) {
  if (voutMv < 800 || voutMv > 1900) return false;
  *centiC = static_cast<int16_t>(((15622 - voutMv * 10) * 1000) / 816);
  return true;
}

} // namespace lmp91000
