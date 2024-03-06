# -*- coding: utf-8 -*-
"""
Created on June 9 2021

@author: Charles Collett
"""


from .instrumentdriver import InstrumentDriver


class WindfreakSynthUSBii(InstrumentDriver):
    '''
    Class to control Windfreaktech SynthUSBii RF source

    '''

    def __init__(self, instrument):

        super().__init__(instrument)
        
        self.f = 0
        self.o = 0
        self.l, self.u = 0, 0
        self.s = 0
        self.t = 0
        self.g = 0
    

    def freq(self, f=0):
        """Set or get the RF frequency.

        Parameters
        ----------
        f : Union[int, float], optional
            Frequency setting in MHz, by default 0 (read the current value)

        Returns
        -------
        float
            The current frequency value in MHz
        """
        if f:
            self.write('f{:.1f}'.format(f))
        self.f = float(self.query('f?'))/1000
        return self.f
    
    
    def output(self, o=0):
        """Turn on or off the RF output.

        Parameters
        ----------
        o : [0, 1], optional
            Output on (1) or off (0), by default 0

        Returns
        -------
        int
            The current output setting
        """
        if o not in [0, 1]:
            raise ValueError("`o` must be 0 or 1")
        self.write('o{}'.format(o))
        self.o = int(self.query('o?'))
        return self.o


    def sweep_lims(self, l=0, u=0):
        """Set or get the minimum and maximum RF sweep frequencies.

        Parameters
        ----------
        l : Union[int, float], optional
            Sweep frequency minimum setting in MHz,
            by default 0 (read the current value)
        u : Union[int, float], optional
            Sweep frequency maximum setting in MHz,
            by default 0 (read the current value)

        Returns
        -------
        (float, float)
            The current sweep frequency minimum and maximum values in MHz
        """
        if l:
            self.write('l{}'.format(l))
        self.l = float(self.query('l?'))/1000
        if u:
            self.write('u{}'.format(u))
        self.u = float(self.query('u?'))/1000
        return self.l, self.u
    
    
    def sweep_step(self, s=0):
        """Set or get the RF sweep frequency step.

        Parameters
        ----------
        s : Union[int, float], optional
            Sweep frequency step setting in MHz,
            by default 0 (read the current value)

        Returns
        -------
        float
            The current sweep frequency step value in MHz
        """
        if s:
            self.write('s{}'.format(s))
        self.s = float(self.query('s?'))/1000
        return self.s
    
    
    def sweep_timestep(self, t=0):
        """Set or get the RF sweep frequency timestep.

        Parameters
        ----------
        t : Union[int, float], optional
            Sweep frequency timestep setting in ms,
            by default 0 (read the current value)

        Returns
        -------
        float
            The current sweep frequency timestep value in ms
        """
        if t:
            self.write('t{}'.format(t))
        self.t = float(self.query('t?'))
        return self.t
    
    
    def sweep_run(self, g=0):
        """Turn on or off the RF sweep.

        Parameters
        ----------
        g : [0, 1], optional
            Sweep on (1) or off (0), by default 0

        Returns
        -------
        int
            The current sweep output setting
        """
        if g not in [0, 1]:
            raise ValueError("`g` must be 0 or 1")
        self.write('g{}'.format(g))
        self.g = int(self.query('g?'))
        return self.g


    def freq_sweep(self, params):
        """Set up and start a frequency sweep.

        Parameters
        ----------
        params : dict of float or int
            A dictionary including the starting, ending, and step
            frequencies (in MHz).
        """
        par_keys = ['start', 'stop', 'step', 'step_length']
        start, stop, step, step_length = [params.get(k)
                                            for k in params if k in par_keys]
        # num_steps = (stop-start)//step
        # step_length = length/num_steps

        self.sweep_lims(start, stop)
        self.sweep_step(step)
        self.sweep_timestep(step_length)

        self.output(1)
        self.sweep_run(1)
        
