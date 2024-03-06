# -*- coding: utf-8 -*-
"""
Created on Sat  Oct 10 2016

@author: amounce
"""

from pyscan.general.itemattribute import ItemAttribute


class Driver(ItemAttribute):  # pragma: no cover
    '''
    Meta class for write/query based visa drivers
    
    Args:
        instrument - pyvisa instrument object
    '''

    def __init__(self, instrument):
        self.instrument = instrument

    def write(self, string):
        '''
        Wrapper for instrument write function
        '''

        self.instrument.write(string)

    def query(self, string):
        '''
        Wrapper for instrument query function
        '''

        return self.instrument.query(string)
