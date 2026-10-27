"""OCK-P1 pod power budget from datasheet currents.

Sources (typical values): AD5940/5941 datasheet Rev. 0 supply table; TPS7A02
datasheet; bq25100 datasheet; nRF52840 product specification (ISP1807 is an
nRF52840 SiP). Radio energy per connection event is an estimate; measure it on
hardware with a power profiler before trusting the lifetime.
"""
import json
import sys

UA = 1e-6
MA = 1e-3

# (name, average current A, source/assumption)
LOADS = [
    ("AD5940 LP potentiostat + LPTIA + LPDAC + LP ref + 32 kHz, continuous", 8.5 * UA,
     "AD5940 DS: 8.5 uA hibernate with LP loop on (6.5 uA half-power)"),
    ("AD5940 ADC + analog idle, 50 ms burst every 30 s", (1.5 * MA + 0.56 * MA) * 0.050 / 30,
     "AD5940 DS: ADC 1.5 mA @200 kSPS, analog idle 0.56 mA; burst length is our choice"),
    ("nRF52840 System ON idle, RTC running, RAM retained", 3.0 * UA,
     "nRF52840 PS: ~1.5 uA (RTC) to ~3 uA (full RAM retention)"),
    ("BLE connection events, 4 s interval, ~5 uC each", 5e-6 / 4.0,
     "Biocoin kConnectionIntervalEff = 4000 ms; 5 uC/event is an estimate"),
    ("BLE data notification, 1 per minute, ~20 uC", 20e-6 / 60,
     "estimate"),
    ("Battery divider 10M + 4.99M at 4.2 V", 4.2 / 14.99e6, "Biocoin R2/R3 values"),
    ("MAX44264 divider buffer", 0.75 * UA, "MAX44264 DS typical supply current"),
    ("TPS7A0230 LDO quiescent", 25e-9, "TPS7A02 DS: 25 nA"),
    ("bq25100 battery-side leakage, no input", 75e-9, "bq25100 DS example leakage 75 nA"),
    ("Status LED, 50 ms every 5 min at 0.5 mA", 0.5 * MA * 0.05 / 300, "Biocoin kBlinkOn/kBlinkOff"),
]

WEAR_DAYS = 15
USABLE_FRACTION = 0.8  # LDO dropout, ageing, cold


def main(cell_mah: float = 15.0):
    total = sum(i for _, i, _ in LOADS)
    need_mah = total * WEAR_DAYS * 24 / MA
    life_days = cell_mah * USABLE_FRACTION * MA / total / 24
    report = {
        "loads_uA": {n: round(i / UA, 3) for n, i, _ in LOADS},
        "total_uA": round(total / UA, 2),
        "mAh_per_15_day_wear": round(need_mah, 2),
        "cell_mAh": cell_mah,
        "days_per_charge": round(life_days, 1),
        "sources": {n: s for n, _, s in LOADS},
    }
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 15.0)
