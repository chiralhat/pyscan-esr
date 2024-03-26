# -*- coding: utf-8 -*-
import pyvisa as visa
import pyscan as ps
import serial


def new_instrument(visa_string=None, gpib_address=None, serial_string=None):
    '''
    Function creates a new visa instrument based on input type.
    If neither a visa_string or gpib_address or serial_string is entered, prints a list
    of possible instruments and returns `None`. If both visa_string and gpib_address are
    entered, only gpib_address is used. If serial_string and any other string are entered,
    only serial_string is used.

    Parameters
    ----------
    visa_string : str
        full visa string address, defaults to `None`.
    gpib_address: int or str
        int to format visa string 'GPIB0::{}::INSTR', defaults to `None`.
    serial_string : str
        full serial string address, defaults to `None`.

    Returns
    -------
    pyvisa :class:`Resource`
        Subclass of Resource from pyvisa library matching the instrument

    '''
    if serial_string is not None:
        return serial.Serial(serial_string, timeout=1)
    else:
        if not hasattr(ps, 'rm'):
            ps.rm = visa.ResourceManager()

        if gpib_address is not None:
            return ps.rm.open_resource('GPIB0::{}::INSTR'.format(gpib_address))
        elif visa_string is not None:
            return ps.rm.open_resource(visa_string)
        else:
            print('No visa_string or gpib_address')
            print('Please choose from one of the following:')
            for resource in ps.rm.list_resources():
                print(resource)
