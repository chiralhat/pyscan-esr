# -*- coding: utf-8 -*-
"""
Created on Jan 7, 2019

@author: amounce
"""


import pyvisa
import serial
import pyscan as ps


def new_instrument(visa_string=None, gpib_address=None, serial_string=None):
    '''
    Function creates a new visa instrument based on input type
    If neither a visa_string or gpib_address is entered, returns a list
    of possible instruments

    Args:
        visa_string(None) - full visa string address
        gpib_address(None) - int to format visa string 'GPIB0::{}::INSTR'
        serial_string(None) - full serial string address



    '''
    if serial_string is not None:
        return serial.Serial(serial_string, timeout=1)
    else:
        if not hasattr(ps, 'rm'):
            ps.rm = pyvisa.ResourceManager('@py')

        if gpib_address is not None:
            return ps.rm.open_resource('GPIB0::{}::INSTR'.format(gpib_address))
        elif visa_string is not None:
            return ps.rm.open_resource(visa_string)
        else:
            print('No visa_string or gpib_address or serial_string')
            print('Please choose from one of the following:')
            for resource in ps.rm.list_resources():
                print(resource)
