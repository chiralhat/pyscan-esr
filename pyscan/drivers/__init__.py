# Objects
from .instrument_driver import InstrumentDriver


# Instrument Drivers
try:
    from .oscilloscope import Oscilloscope
except OSError:
    print('Oscilloscope not found, generic driver not loaded')
try:
    from .tektronixmso2 import TektronixMSO2
except OSError:
    print('MSO2 Oscilloscope not found, TektronixMSO2 not loaded')
try:
    from .ecp5evn import ecp5evn
except OSError:
    print('ECP5 board not found, ecp5evn not loaded')
try:
    from .windfreaksynthhd import WindfreakSynthHD
except OSError:
    print('SynthHD not found, WindFreakSynthHD not loaded')
try:
    from .lakeshore335 import Lakeshore335
except OSError:
    print('Temperature Controller not found, Lakeshore335 not loaded')
try:
    from .mokugo import MokuGo
except OSError:
    print('Power Supply not found, Moku:Go not loaded')



# Methods
from .new_instrument import new_instrument

# Test Devices
from .testing.test_voltage import TestVoltage
from .testing.test_instrument_driver import TestInstrumentDriver
