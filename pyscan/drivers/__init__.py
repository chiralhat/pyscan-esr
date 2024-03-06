# Objects
from .instrumentdriver import InstrumentDriver
from .driver import Driver
# Instrument Drivers
try:
    from .oscilloscope import Oscilloscope
except OSError:
    print('Oscilloscope not found, generic driver not loaded')
try:
    from .bkprecision2190e import BKPrecision2190E
except OSError:
    print('BK2190E Oscilloscope not found, BKPrecision2190E not loaded')
try:
    from .tektronix2022b import Tektronix2022B
except OSError:
    print('2022B Oscilloscope not found, Tektronix2022B not loaded')
try:
    from .tektronix1052b import Tektronix1052B
except OSError:
    print('1052B Oscilloscope not found, Tektronix1052B not loaded')
try:
    from .tektronixmso2 import TektronixMSO2
except OSError:
    print('MSO2 Oscilloscope not found, TektronixMSO2 not loaded')
try:
    from .ice40hx8k import ice40HX8K
except OSError:
    print('iceBoard not found, ice40HX8K not loaded')
try:
    from .ecp5evn import ecp5evn
except OSError:
    print('ECP5 board not found, ecp5evn not loaded')
try:
    from .windfreaksynthhd import WindfreakSynthHD
except OSError:
    print('SynthHD not found, WindFreakSynthHD not loaded')
try:
    from .windfreaksynthusbii import WindfreakSynthUSBii
except OSError:
    print('SynthUSBii not found, WindFreakSynthUSBii not loaded')
try:
    from .lakeshore335 import Lakeshore335
except OSError:
    print('Temperature Controller not found, Lakeshore335 not loaded')
try:
    from .gpd3303s import GPD3303S
except OSError:
    print('Power Supply not found, GPD3303S not loaded')

# Methods
from .newinstrument import new_instrument

# Test Devices

