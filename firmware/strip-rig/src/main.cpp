/**
 * @file main.cpp
 * @brief Strip rig: ESP32 + LMP91000 potentiostat streaming OCK frames over BLE.
 *
 * GATT service 00001523-... mirrors the Biocoin layout so the host bridge can drive both:
 *   CONFIG  (write)        12 bytes <BBhHIH: version=1, tia_gain_code 1..7, bias_mv, period_ms, sensor_id, cal_id
 *   CONTROL (write)        1 byte: 0x01 START, 0xFF STOP
 *   STATUS  (read,notify)  1 byte: 0 stopped, 1 invalid parameters, 2 running, 3 error
 *   DATA    (notify)       20-byte OCK frames (docs/PROTOCOL.md)
 *   IDENT   (read)         latest 20-byte OCK identity frame
 * Acquisition stops on disconnect and the cell returns to zero bias (FET short).
 */

#include <Arduino.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <Wire.h>

#include "lmp91000.h"
#include "ock_frame.h"

namespace {

constexpr char kServiceUuid[] = "00001523-1212-efde-1523-785feabc93aa";
constexpr char kStatusUuid[] = "00001524-1212-efde-1523-785feabc93aa";
constexpr char kControlUuid[] = "00001528-1212-efde-1523-785feabc93aa";
constexpr char kDataUuid[] = "00001529-1212-efde-1523-785feabc93aa";
constexpr char kConfigUuid[] = "0000152a-1212-efde-1523-785feabc93aa";
constexpr char kIdentUuid[] = "0000152b-1212-efde-1523-785feabc93aa";

enum Status : uint8_t { kStopped = 0, kInvalid = 1, kRunning = 2, kError = 3 };

constexpr uint16_t kMinPeriodMs = 100;
constexpr uint16_t kMaxPeriodMs = 60000;
constexpr uint32_t kTempPeriodMs = 10000;   /* temperature is refreshed this often and held between reads */
constexpr uint32_t kTempSettleMs = 30;      /* placeholder: VOUT settling after switching to temperature mode */
constexpr uint32_t kSettleFlagMs = 30000;   /* placeholder: SETTLING flag after bias is applied; tune per strip */
constexpr uint16_t kIdentRepeatSamples = 256;
constexpr int kOversample = 64;
constexpr int32_t kRailMarginMv = 100;      /* VOUT this close to a rail is flagged OVERRANGE */

struct Config {
  uint8_t gainCode = 7;
  int16_t biasMv = 0;
  uint16_t periodMs = 1000;
  uint32_t sensorId = 0;
  uint16_t calId = 0;
};

/* Written by BLE callbacks, consumed by loop(). */
volatile bool requestStart = false;
volatile bool requestStop = false;
volatile bool linkLost = false;
volatile bool subscribed = false;
portMUX_TYPE configMux = portMUX_INITIALIZER_UNLOCKED;
Config pending;
volatile bool pendingValid = false;
volatile bool pendingChanged = false;

Config active;
lmp91000::Reference reference;
uint32_t rtiaOhms = 0;
Status status = kStopped;
uint16_t seq = 0;
uint8_t identEpoch = 0;
uint32_t startMs = 0;
uint32_t nextSampleMs = 0;
uint32_t nextTempMs = 0;
int16_t tempCc = OCK_TEMP_INVALID;

BLEServer* server = nullptr;
BLECharacteristic* statusChr = nullptr;
BLECharacteristic* dataChr = nullptr;
BLECharacteristic* identChr = nullptr;

bool writeReg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(lmp91000::kAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readReg(uint8_t reg, uint8_t* value) {
  Wire.beginTransmission(lmp91000::kAddress);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(static_cast<uint8_t>(lmp91000::kAddress), static_cast<uint8_t>(1)) != 1) return false;
  *value = Wire.read();
  return true;
}

void publishStatus(Status next) {
  status = next;
  const uint8_t value = static_cast<uint8_t>(next);
  statusChr->setValue(const_cast<uint8_t*>(&value), 1);
  if (subscribed || server->getConnectedCount() > 0) statusChr->notify();
}

void sendFrame(BLECharacteristic* chr, const uint8_t* frame, bool notify) {
  chr->setValue(const_cast<uint8_t*>(frame), OCK_FRAME_LEN);
  if (notify && server->getConnectedCount() > 0) chr->notify();
}

void sendIdent() {
  ock_ident_t id = {};
  id.status = static_cast<uint8_t>(identEpoch << OCK_ST_EPOCH_SHIFT);
  id.technique = 1;
  id.rtia_x10 = static_cast<uint16_t>(rtiaOhms / 10);
  id.bias_mv = reference.biasMv;
  id.period_ms = active.periodMs;
  id.sensor_id = active.sensorId;
  id.cal_id = active.calId;
  uint8_t frame[OCK_FRAME_LEN];
  ock_encode_ident(frame, &id);
  sendFrame(identChr, frame, false);
  sendFrame(dataChr, frame, true);
}

/** Mean VOUT in mV over kOversample reads of the ESP32 ADC (calibrated, 11 dB). */
int32_t readVoutMv() {
  int64_t sum = 0;
  for (int i = 0; i < kOversample; i++) sum += analogReadMilliVolts(PIN_VOUT);
  return static_cast<int32_t>(sum / kOversample);
}

void idleCell() {
  /* Deep sleep with the FET shorting WE to RE keeps zero bias on the electrode. */
  writeReg(lmp91000::kRegModecn, lmp91000::kFetShort | lmp91000::kModeDeepSleep);
}

bool readTemperature() {
  if (!writeReg(lmp91000::kRegModecn, lmp91000::kModeTempTiaOn)) return false;
  delay(kTempSettleMs);
  int16_t cc;
  const bool ok = lmp91000::tempCentiC(readVoutMv(), &cc);
  const bool back = writeReg(lmp91000::kRegModecn, lmp91000::kMode3Lead);
  tempCc = ok ? cc : OCK_TEMP_INVALID;
  return back;
}

bool startAcquisition() {
  if (!pendingValid) return false;
  portENTER_CRITICAL(&configMux);
  const Config next = pending;
  const bool changed = pendingChanged;
  pendingChanged = false;
  portEXIT_CRITICAL(&configMux);

  if (!lmp91000::gainOhms(next.gainCode, &rtiaOhms)) return false;
  if (!lmp91000::reference(next.biasMv, VREF_MV, &reference)) return false;
  if (changed) identEpoch = (identEpoch + 1) & 0x03;
  active = next;

  uint8_t ready = 0;
  const uint32_t deadline = millis() + 2000;
  while (millis() < deadline && !(readReg(lmp91000::kRegStatus, &ready) && (ready & 1))) delay(10);
  if (!(ready & 1)) return false;

  if (!writeReg(lmp91000::kRegLock, lmp91000::kLockWrite)) return false;
  const bool configured = writeReg(lmp91000::kRegTiacn, lmp91000::tiacn(active.gainCode)) &&
                          writeReg(lmp91000::kRegRefcn, reference.refcn);
  writeReg(lmp91000::kRegLock, lmp91000::kLockProtect);
  if (!configured) return false;
  if (!writeReg(lmp91000::kRegModecn, lmp91000::kMode3Lead)) return false;

  seq = 0;
  startMs = millis();
  readTemperature();
  nextTempMs = startMs + kTempPeriodMs;
  sendIdent();
  nextSampleMs = millis() + active.periodMs;
  return true;
}

void stopAcquisition() {
  idleCell();
}

void takeSample() {
  const uint32_t now = millis();
  const int32_t voutMv = readVoutMv();

  ock_sample_t sample = {};
  sample.seq = seq++;
  sample.t_ms = now;
  /* I = (VOUT - Vzero) / RTIA, in pA: mV * 1e9 / ohm. */
  const double pa = CURRENT_SIGN * static_cast<double>(voutMv - static_cast<int32_t>(reference.zeroMv)) * 1.0e9 /
                    static_cast<double>(rtiaOhms);
  sample.current_pa = static_cast<int32_t>(pa);
  sample.temp_cc = tempCc;
  sample.status = static_cast<uint8_t>(identEpoch << OCK_ST_EPOCH_SHIFT);
  if (tempCc == OCK_TEMP_INVALID) sample.status |= OCK_ST_TEMP_INVALID;
  sample.status |= OCK_ST_TEMP_DIE; /* LMP91000 die, not the strip */
  if (voutMv < kRailMarginMv || voutMv > VREF_MV - kRailMarginMv) sample.status |= OCK_ST_OVERRANGE;
  if (now - startMs < kSettleFlagMs) sample.status |= OCK_ST_SETTLING;

  uint8_t frame[OCK_FRAME_LEN];
  ock_encode_sample(frame, &sample);
  sendFrame(dataChr, frame, true);
  if (seq % kIdentRepeatSamples == 0) sendIdent();
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { linkLost = false; }
  void onDisconnect(BLEServer*) override {
    subscribed = false;
    linkLost = true; /* loop() stops acquisition and restarts advertising */
  }
};

class ConfigCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* chr) override {
    if (status == kRunning) return; /* configuration is frozen while running */
    std::string value = chr->getValue();
    Config next;
    uint32_t ohms;
    lmp91000::Reference ref;
    bool ok = value.size() == 12 && static_cast<uint8_t>(value[0]) == 1;
    if (ok) {
      const uint8_t* p = reinterpret_cast<const uint8_t*>(value.data());
      next.gainCode = p[1];
      next.biasMv = static_cast<int16_t>(p[2] | (p[3] << 8));
      next.periodMs = static_cast<uint16_t>(p[4] | (p[5] << 8));
      next.sensorId = static_cast<uint32_t>(p[6]) | (static_cast<uint32_t>(p[7]) << 8) |
                      (static_cast<uint32_t>(p[8]) << 16) | (static_cast<uint32_t>(p[9]) << 24);
      next.calId = static_cast<uint16_t>(p[10] | (p[11] << 8));
      ok = lmp91000::gainOhms(next.gainCode, &ohms) && lmp91000::reference(next.biasMv, VREF_MV, &ref) &&
           next.periodMs >= kMinPeriodMs && next.periodMs <= kMaxPeriodMs;
    }
    portENTER_CRITICAL(&configMux);
    if (ok) {
      pendingChanged = pendingChanged || !pendingValid || memcmp(&pending, &next, sizeof(Config)) != 0;
      pending = next;
    }
    pendingValid = ok;
    portEXIT_CRITICAL(&configMux);
    configRejected = !ok;
  }

 public:
  static volatile bool configRejected;
};
volatile bool ConfigCallbacks::configRejected = false;

class ControlCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* chr) override {
    std::string value = chr->getValue();
    if (value.size() != 1) return;
    if (static_cast<uint8_t>(value[0]) == 0x01) requestStart = true;
    if (static_cast<uint8_t>(value[0]) == 0xFF) requestStop = true;
  }
};

}  // namespace

void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  analogSetPinAttenuation(PIN_VOUT, ADC_11db);

  BLEDevice::init("OCK-StripRig");
  server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService* service = server->createService(kServiceUuid);

  BLECharacteristic* config = service->createCharacteristic(kConfigUuid, BLECharacteristic::PROPERTY_WRITE);
  config->setCallbacks(new ConfigCallbacks());
  BLECharacteristic* control = service->createCharacteristic(kControlUuid, BLECharacteristic::PROPERTY_WRITE);
  control->setCallbacks(new ControlCallbacks());
  statusChr = service->createCharacteristic(kStatusUuid, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  statusChr->addDescriptor(new BLE2902());
  dataChr = service->createCharacteristic(kDataUuid, BLECharacteristic::PROPERTY_NOTIFY);
  dataChr->addDescriptor(new BLE2902());
  identChr = service->createCharacteristic(kIdentUuid, BLECharacteristic::PROPERTY_READ);
  service->start();

  idleCell();
  publishStatus(kStopped);

  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(kServiceUuid);
  advertising->start();
}

void loop() {
  if (linkLost) {
    linkLost = false;
    requestStart = false;
    if (status == kRunning) stopAcquisition();
    publishStatus(kStopped);
    BLEDevice::startAdvertising();
  }
  if (requestStop) {
    requestStop = false;
    if (status == kRunning) stopAcquisition();
    publishStatus(kStopped);
  }
  if (ConfigCallbacks::configRejected) {
    ConfigCallbacks::configRejected = false;
    publishStatus(kInvalid);
  }
  if (requestStart) {
    requestStart = false;
    if (status != kRunning) {
      if (startAcquisition()) {
        publishStatus(kRunning);
      } else {
        stopAcquisition();
        publishStatus(pendingValid ? kError : kInvalid);
      }
    }
  }

  if (status == kRunning) {
    const uint32_t now = millis();
    if (static_cast<int32_t>(now - nextSampleMs) >= 0) {
      nextSampleMs += active.periodMs; /* fixed rate: no drift from sample cost */
      takeSample();
    } else if (static_cast<int32_t>(now - nextTempMs) >= 0 &&
               static_cast<int32_t>(nextSampleMs - now) > static_cast<int32_t>(kTempSettleMs + 40)) {
      nextTempMs += kTempPeriodMs;
      if (!readTemperature()) {
        stopAcquisition();
        publishStatus(kError);
      }
    }
  }
  delay(1);
}
