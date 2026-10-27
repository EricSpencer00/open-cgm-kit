# Strip rig firmware

ESP32 dev board + LMP91000 breakout (I2C 0x48) streaming OCK frames (`docs/PROTOCOL.md`) over BLE.

Wiring: SDA GPIO21, SCL GPIO22, VOUT to GPIO34 (ADC1), LMP91000 VDD 3.3 V, MENB to GND, 4.7 kohm I2C pull-ups
if the breakout has none. Override pins and `VREF_MV` (measured LMP91000 VDD) in `platformio.ini`.

```sh
pio run -e esp32dev          # build from firmware/strip-rig
pio run -e esp32dev -t upload
pio test -e native           # host test of the LMP91000 register encoders
clang -std=c99 -Wall -Wextra -Werror -I../common ../common/test/test_ock_frame.c && ./a.out
python3 ../../software/bridge/biocoin_bridge.py --device strip-rig --address ID --tia-gain-code 7 \
  --bias-mv 594 --period-ms 1000 --duration-s 600 --csv run.csv --calibration cal.json
```

Register values follow TI SNAS506I: LOCK 0x01 must be cleared to write TIACN 0x10 and REFCN 0x11;
MODECN 0x12 = 0x03 runs the 3-lead potentiostat, 0x07 shows the die temperature on VOUT, and
0x80 (FET short, deep sleep) holds zero bias when idle. Bias is the nearest of 0-24 % of VREF, so
requested and applied values differ; the applied value is in the identity frame.

Behaviour: acquisition stops and the cell is shorted on disconnect, STOP, or an I2C error. Configuration
is frozen while running. Temperature is read every 10 s and held between reads.
