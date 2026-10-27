/**
 * @file ock_frame.h
 * @brief Open CGM Kit framed sensor protocol, version 1 (see docs/PROTOCOL.md).
 *
 * Header-only and freestanding: shared by the ESP32 strip rig, the patched
 * Biocoin firmware and the host-side C test. All multi-byte fields are
 * little-endian. Every frame is exactly OCK_FRAME_LEN bytes.
 */

#ifndef OCK_FRAME_H
#define OCK_FRAME_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OCK_SYNC 0xA5u
#define OCK_VERSION 1u
#define OCK_FRAME_LEN 20u

#define OCK_KIND_SAMPLE 0x01u
#define OCK_KIND_IDENT 0x02u

/* Status byte: bits 0..5 flags, bits 6..7 identity epoch. */
#define OCK_ST_OVERRANGE 0x01u    /* ADC or TIA saturated; current is a bound */
#define OCK_ST_TEMP_INVALID 0x02u /* temp_cc is not a measurement */
#define OCK_ST_TEMP_DIE 0x04u     /* temperature is a chip die, not the strip */
#define OCK_ST_SETTLING 0x08u     /* bias applied < settle time ago */
#define OCK_ST_DROPPED 0x10u      /* device dropped samples before this one */
#define OCK_ST_EPOCH_SHIFT 6u
#define OCK_ST_EPOCH_MASK 0xC0u

#define OCK_TEMP_INVALID ((int16_t)-32768)

typedef struct {
  uint8_t status;      /* flags | (ident_epoch << 6) */
  uint16_t seq;        /* per-sample counter, wraps at 65536 */
  uint32_t t_ms;       /* device acquisition time, ms since boot, wraps at 2^32 */
  int32_t current_pa;  /* electrode current, picoamps, positive = oxidation */
  int16_t temp_cc;     /* hundredths of a degree C, OCK_TEMP_INVALID if absent */
} ock_sample_t;

typedef struct {
  uint8_t status;      /* only the epoch bits are meaningful */
  uint8_t technique;   /* 1 = chronoamperometry */
  uint16_t rtia_x10;   /* feedback resistance in units of 10 ohm */
  int16_t bias_mv;     /* working-electrode bias vs reference, mV */
  uint16_t period_ms;  /* nominal sample period */
  uint32_t sensor_id;  /* strip lot / serial, 0 = unknown */
  uint16_t cal_id;     /* calibration identity, 0 = none */
} ock_ident_t;

/* CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout. */
static inline uint16_t ock_crc16(const uint8_t *data, size_t len) {
  uint16_t crc = 0xFFFFu;
  while (len--) {
    crc ^= (uint16_t)((uint16_t)*data++ << 8);
    for (int i = 0; i < 8; i++) crc = (crc & 0x8000u) ? (uint16_t)((crc << 1) ^ 0x1021u) : (uint16_t)(crc << 1);
  }
  return crc;
}

static inline void ock_put16(uint8_t *p, uint16_t v) {
  p[0] = (uint8_t)v;
  p[1] = (uint8_t)(v >> 8);
}

static inline void ock_put32(uint8_t *p, uint32_t v) {
  ock_put16(p, (uint16_t)v);
  ock_put16(p + 2, (uint16_t)(v >> 16));
}

static inline void ock_header(uint8_t *out, uint8_t kind, uint8_t status) {
  out[0] = OCK_SYNC;
  out[1] = OCK_VERSION;
  out[2] = OCK_FRAME_LEN;
  out[3] = kind;
  out[4] = status;
}

static inline void ock_seal(uint8_t *out) {
  ock_put16(out + OCK_FRAME_LEN - 2, ock_crc16(out, OCK_FRAME_LEN - 2));
}

/** Encode one sample into out[OCK_FRAME_LEN]. */
static inline void ock_encode_sample(uint8_t *out, const ock_sample_t *s) {
  ock_header(out, OCK_KIND_SAMPLE, s->status);
  out[5] = 0;
  ock_put16(out + 6, s->seq);
  ock_put32(out + 8, s->t_ms);
  ock_put32(out + 12, (uint32_t)s->current_pa);
  ock_put16(out + 16, (uint16_t)s->temp_cc);
  ock_seal(out);
}

/** Encode an identity/configuration frame into out[OCK_FRAME_LEN]. */
static inline void ock_encode_ident(uint8_t *out, const ock_ident_t *id) {
  ock_header(out, OCK_KIND_IDENT, id->status);
  out[5] = id->technique;
  ock_put16(out + 6, id->rtia_x10);
  ock_put16(out + 8, (uint16_t)id->bias_mv);
  ock_put16(out + 10, id->period_ms);
  ock_put32(out + 12, id->sensor_id);
  ock_put16(out + 16, id->cal_id);
  ock_seal(out);
}

#ifdef __cplusplus
}
#endif

#endif /* OCK_FRAME_H */
