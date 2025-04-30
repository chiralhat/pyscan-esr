# -*- coding: utf-8 -*-
"""
Created on Fri Apr 29 09:25:29 2016

@author: ccollett
"""

import numpy as np
import scipy.optimize as sop
import matplotlib.pyplot as plt

# Fitting functions


def lorentzian(x, b, a, w, f):
    return b + a * (w / 2)**2 / ((x - f)**2 + (w / 2)**2)


def lorentziannoback(x, a, w, f):
    return a * (w / 2)**2 / ((x - f)**2 + (w / 2)**2)


def lorentzianslope(x, b, a, w, f, slope, gf):
    return b + a * (w / 2)**2 / ((x - f)**2 + (w / 2)**2) + slope * (x - gf)


def exponential(x, c, a, t):
    return a * np.exp(-(x) / t) + c


def double_exponential(x, c, a, t, b, t2):
    return a * np.exp(-(x) / t) + b * np.exp(-(x) / t2) + c


def stretched_exponential(x, a, t, beta):
    return a * np.exp((-x**beta / t**beta))


def exponentialnoback(x, a, t):
    return a * np.exp(-(x) / t)


def gaussian(x, b, a, w, f):
    return b + a * np.exp(-(2 / w)**2 * (x - f)**2)


def gaussiannoback(x, a, w, f):
    return a * np.exp(-(2 / w)**2 * (x - f)**2)


def gaussianslope(x, b, a, w, f, slope, gf):
    return b + a * np.exp(-(2 / w)**2 * (x - f)**2) + slope * (x - gf)


def sinefit(x, b, a, w, t):
    return b + a * np.sin(w * x + t)


def quadlorfit(x, b, a, w, f, c, d):
    return lorentzian(x, b, a, w, f) + c * x + d * x**2


def rabifit(x, a, t, T, phi, b):
    return a*np.exp(-x/t)*np.cos(2*np.pi/T*x+phi)+b

def rabifitnophi(x, a, t, T, b):
    return a*np.exp(-x/t)*np.cos(2*np.pi/T*x)+b
    

# Helper functions

def find_nearest_idx(array, value):
    """Finds the element in 'array' that is nearest to 'value'.

    Returns the index of the nearest element."""
    if type(value) != list and type(value) != np.ndarray:
        return (np.abs(array - value)).argmin()
    else:
        def mfun(val):
            return find_nearest_idx(array, val)
        return np.array(list(map(mfun, value)))


def find_min(data):
    return data[1].min()


def r2bar(data, fit, numfitpars):
    """Calculates the adjusted R-squared value for a fit based on the data.

    R2=1-np.sum(data-fit)**2/np.sum(data-np.mean(data))**2
    r2bar=1-(1-R2)*(len(data)-1)/(len(data)-numfitpars-1)

    'data' is an array of y-axis data;
    'fit' is an array of fit data corresponding to 'data';
    'numfitpars' is the number of fit parameters used in the fit.

    Returns the adjusted R-squared value."""
    R2 = 1 - np.sum([(data[i] - fit[i])**2 for i in np.arange(len(data))]) / \
        np.sum([(data[i] - np.mean(data))**2 for i in np.arange(len(data))])
    r2_adj = 1 - (1 - R2) * (len(data) - 1) / (len(data) - numfitpars - 1)
    return r2_adj


def func_fit(func, data, guess, **kwargs):
    """Fits any function to a dataset.

    'func' is the fitting function to use;
    'data' is a data array;
    'guess' is an array of initial guess parameters.

    Returns a list with three elements: an array with the fit parameters;
    an array with the uncertainties in those parameters;
    the adjusted R-squared for the fit.
    If the fitting fails, it will return all zeroes."""
    try:
        fit = sop.curve_fit(func, data[0], data[1], guess, **kwargs)
        err = np.sqrt(np.diag(fit[1]))
        fitdat = func(data[0], *fit[0])
        R2b = r2bar(data[1], fitdat, len(fit[0]))
    except RuntimeError:
        n = len(guess)
        fit = [np.zeros(n)]
        err = np.zeros(n)
        R2b = 0
    return [fit[0], err, R2b]


def plot_func_fit(func, data, guess, plt=plt, fit=0, cols=0, datlab='Data',
                  fitlab='Fit', dsty='o', fsty='--', transpose=False, **kwargs):
    """Fits any function to a dataset and plots the result.

    'func' is the fitting function to use;
    'data' is a data array;
    'guess' is an array of initial guess parameters;
    'plt' is the plotting environment to use,
    defaulting to pyplot (imported as plt).

    Returns an array with the fit parameters."""
    if fit == 0:
        fit, err, R2b = func_fit(func, data, guess)
    if cols == 0:
        cols = ['b', 'g']
    if transpose:
        plt.plot(data[1], data[0], dsty, label=datlab, c=cols[0], **kwargs)
        plt.plot(func(data[0], *fit), data[0], fsty, label=fitlab, c=cols[1])
    else:
        plt.plot(data[0], data[1], dsty, label=datlab, c=cols[0], **kwargs)
        plt.plot(data[0], func(data[0], *fit), fsty, label=fitlab, c=cols[1])

    return np.array([fit, err])



def guess_lor_pars(data, skew, full):
    """Algorithmically produces the initial guess parameters for a Lorentzian fit.

    'data' is a data array with elements [x-axis data,y-axis data];
    'skew' is 1 to subtract a linear background, and 0 to use no slope;
    'full' is 1 to fit the whole dataset, and 0 to only fit between the maxima
    on either side of the peak.
    Works for VNA and pulsed data, where the peak goes down and is centered.

    Returns an array of guess parameters: Background, Amplitude, Width,
    Frequency, slope, fitting points."""
    datLength = len(data[1])
    minPos = data[1].argmin()
    GuessB = data[1, 1:].max()
    GuessA = data[1].min() - GuessB
    left_midpoint = find_nearest_idx(data[1, minPos:], GuessB + GuessA / 2)
    right_midpoint = find_nearest_idx(data[1, :minPos], GuessB + GuessA / 2)
    GuessW = data[0][left_midpoint] - data[0][right_midpoint]
    GuessF = data[0, minPos]
    if full == 0:
        fitp = [data[1, :minPos].argmax(), data[1, minPos:].argmax() + minPos]
    else:
        fitp = [0, datLength - 1]
    if skew == 1:
        slope = -(data[1][fitp[0]] - data[1][fitp[1]]) * minPos / \
            datLength / (data[0][fitp[1]] - data[0][fitp[0]])
    else:
        slope = 0
    return [GuessB, GuessA, GuessW, GuessF, slope, fitp]


def lor_fit(data, skew=1, full=1):
    """Fits a Lorentzian function to a dataset.

    'data' is a data array with elements [x-axis data,y-axis data];
    'skew' is 1 (default) to subtract a linear background,
    and 0 to use no slope;
    'full' is 1 (default) to fit the whole dataset,
    and 0 to only fit between the maxima on either side of the peak.
    Works for VNA and pulsed data, where the peak goes down and is centered.

    Returns an array with: an array with the fit parameters (background,
    amplitude, width, frequency); the uncertainty in those parameters;
    the slope (if any) of the linear background;
    the adjusted R-squared of the fit."""
    [GuessB, GuessA, GuessW, GuessF, slope,
     fitp] = guess_lor_pars(data, skew, full)

    def lorentzian(x, b, a, w, f):
        return lorentzianslope(x, b, a, w, f, slope, GuessF)
    fitdata = np.array([data[0][fitp[0]:fitp[1]], data[1][fitp[0]:fitp[1]]])
    guess = [GuessB, GuessA, GuessW, GuessF]
    fit, err, R2b = func_fit(lorentzian, fitdata, guess)
    return [fit, err, slope, R2b]


def plot_lor_fit(data, skew=1, full=1, plt=plt):
    """Fits a Lorentzian function to a dataset and plot the result.

    'data' is a data array with elements [x-axis data,y-axis data];
    'skew' is 1 (default) to subtract a linear background,
    and 0 to use no slope;
    'full' is 1 (default) to fit the whole dataset,
    and 0 to only fit between the maxima on either side of the peak;
    'plt' is the plotting environment to use, defaulting to pyplot
    (imported as plt).
    Works for VNA and pulsed data, where the peak goes down and is centered.

    Returns an array with: an array with the fit parameters (background,
    amplitude, width, frequency), the Q of the peak."""
    [fit, err, slope, _] = lor_fit(data, skew, full)
    plt.plot(data[0], data[1], data[0], lorentzianslope(
        data[0], fit[0], fit[1], fit[2], fit[3], slope, fit[3]))
    return [fit, np.abs(fit[3] / fit[2])]


def exp_fit(data, freq, start, end, up, coefs=0):
    """Fits an exponential decay function to a dataset.

    'data' is a data array with elements [time,in-phase,quadrature];
    'freq' is the experimental microwave frequency;
    'start' is the lowest time point in the fitting window;
    'end' is the highest time point in the fitting window;
    'up' is 1 if the exponential is decaying down (towards -infinity),
    and 0 if it is decaying up (towards +infinity);
    'coefs' is 0 (default) if the initial guess parameters should be
    calculated from the dataset, and an array of guess parameters otherwise.

    Returns a list with three elements: an array with the fit parameters
    (background, amplitude, decay time, Q);
    an array with the uncertainties in those parameters;
    the adjusted R-squared for the fit."""
    points = find_nearest_idx(data[0], [start, end])
    if coefs == 0:
        guess = []
        guess.append(data[1, points[0]:points[1]].min())
        guess.append((data[1, points[0]:points[1]].max() -
                      data[1, points[0]:points[1]].min()) * up)
        guess.append(np.diff(data[0, points])[0] / 10)
    else:
        guess = coefs
    fit, err, R2b = func_fit(exponential, [data[0, points[0]:points[1]], data[
                             1, points[0]:points[1]]], guess)
    Q = np.pi * freq * fit[2]
    Qerr = np.pi * freq * err[2]
    fitout = np.append(fit, Q)
    errout = np.append(err, Qerr)
    return [fitout, errout, R2b]


def exp_fit_norange(data, freq, up, coefs=0):
    """Fits an exponential decay function to a dataset.

    'data' is a data array with elements [time,in-phase,quadrature];
    'freq' is the experimental microwave frequency;
    'up' is 1 if the exponential is decaying down (towards -infinity),
    and 0 if it is decaying up (towards +infinity);
    'coefs' is 0 (default) if the initial guess parameters should be
    calculated from the dataset, and an array of guess parameters otherwise.

    Returns a list with three elements: an array with the fit parameters
    (background, amplitude, decay time, Q);
    an array with the uncertainties in those parameters;
    the adjusted R-squared for the fit."""
    if coefs == 0:
        guess = []
        guess.append(data[1].min())
        guess.append((data[1].max() -
                      data[1].min()) * up)
        guess.append(np.diff(data[0, [0,-1]])[0] / 10)
    else:
        guess = coefs
    fit, err, R2b = func_fit(exponential, data, guess)
    Q = np.pi * freq * fit[2]
    Qerr = np.pi * freq * err[2]
    fitout = np.append(fit, Q)
    errout = np.append(err, Qerr)
    return [fitout, errout, R2b]


def plot_exp_fit(data, freq, start, end, up=1, coefs=0, plt=plt, col=0,
                 datlab='Data', fitlab='Fit'):
    """Fits an exponential decay function to a dataset and plot the result.

    'data' is a data array with elements [time,in-phase,quadrature];
    'freq' is the experimental microwave frequency;
    'start' is the lowest time point in the fitting window;
    'end' is the highest time point in the fitting window;
    'up' is 1 (default) if the exponential is decaying down
    (towards -infinity), and 0 if it is decaying up (towards +infinity);
    'coefs' is 0 (default) if the initial guess parameters should be
    calculated from the dataset, and an array of guess parameters otherwise;
    'plt' is the plotting environment to use, defaulting to pyplot
    (imported as plt).

    Returns an array with the fit parameters (background, amplitude,
    decay time, Q)."""
    points = find_nearest_idx(data[0], [start, end])
    [fit, err, _] = exp_fit(data, freq, start, end, up, coefs)
    if col == 0:
        plt.plot(data[0, points[0]:points[1]], data[
                 1, points[0]:points[1]], '-', label=datlab)
        plt.plot(data[0, points[0]:points[1]], exponential(
            data[0, points[0]:points[1]], fit[0], fit[1], fit[2]), '--',
            label=fitlab)
    else:
        plt.plot(data[0, points[0]:points[1]], data[
                 1, points[0]:points[1]], '-', c=col[0], label=datlab)
        plt.plot(data[0, points[0]:points[1]], exponential(
                data[0, points[0]:points[1]], fit[0], fit[1], fit[2]), '--',
                c=col[1], label=fitlab)
    return fit


def plot_exp_fit_norange(data, freq, up=1, coefs=0, plt=plt, col=0,
                 datlab='Data', fitlab='Fit', plotdat=1):
    """Fits an exponential decay function to a dataset and plot the result.

    'data' is a data array with elements [time,in-phase,quadrature];
    'freq' is the experimental microwave frequency;
    'up' is 1 (default) if the exponential is decaying down
    (towards -infinity), and 0 if it is decaying up (towards +infinity);
    'coefs' is 0 (default) if the initial guess parameters should be
    calculated from the dataset, and an array of guess parameters otherwise;
    'plt' is the plotting environment to use, defaulting to pyplot
    (imported as plt).

    Returns two arrays, the first with the fit parameters (background,
    amplitude, decay time, Q) and the second with the error in those."""
    [fit, err, _] = exp_fit_norange(data, freq, up, coefs)
    if col == 0:
        if plotdat:
            plt.plot(data[0], data[1], '.-', label=datlab)
        plt.plot(data[0], exponential(data[0], fit[0], fit[1], fit[2]), '--',
            label=fitlab)
    else:
        plt.plot(data[0], data[1], '.-', c=col[0], label=datlab)
        plt.plot(data[0], exponential(data[0], fit[0], fit[1], fit[2]), '--',
                c=col[1], label=fitlab)
    return np.array([fit, err])