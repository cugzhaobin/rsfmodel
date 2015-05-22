#!/usr/bin/env python

"""
rsf

This module provides rate and state frictional modeling capability.

Documentation is provided throughout the module in the form of docstrings.
It is easy to view these in the iPython interactive shell environment. Simply
type the command and ? to view the docstring. Examples are provided at the
GitHub page (https://github.com/jrleeman/rate-and-state) in the README.md file.
"""

__authors__ = ["John Leeman", "Ryan May"]
__credits__ = ["Chris Marone", "Demian Saffer"]
__license__ = ""
__version__ = "1.0."
__maintainer__ = "John Leeman"
__email__ = "kd5wxb@gmail.com"
__status__ = "Development"

import numpy as np
import matplotlib.pyplot as plt
from scipy import integrate
from math import exp, log
from collections import namedtuple


class StateRelation(object):
    def __init__(self, relation):
        self.b = None
        self.Dc = None
        self.state = None

    def velocity_component(self, system):
        return self.b * log(system.vref * self.state / self.Dc)


class DieterichState(StateRelation):
    def _set_steady_state(self, system):
        self.state = self.Dc/system.vref

    def evolve_state(self, system):
        if self.state is None:
            self.state = _steady_state(self, system)
        # return dtheta/dt
        return 1. - system.v * self.state / self.Dc


class RuinaState(StateRelation):
    def _set_steady_state(self, system):
        self.state = self.Dc/system.vref

    def evolve_state(self, system):
        if self.state is None:
            self.state = _steady_state(self, system)
        # return dtheta/dt
        return -1 * (system.v * self.state / self.Dc) * log(system.v * self.state / self.Dc)


class PrzState(StateRelation):
    def _set_steady_state(self, system):
        self.state = 2 * self.Dc / system.vref

    def evolve_state(self, system):
        if self.state is None:
            self.state = _steady_state(self, system)
        # return dtheta/dt
        return 1. - (system.v * self.state / (2 * self.Dc))**2


class ExternalSystem(object):
    def __init__(self):
        # Rate and state model parameters
        self.mu0 = None
        self.a = None
        self.k = None
        self.v = None
        self.vref = None
        self.state_relations = []

    def velocity_evolution(self):
        v_contribution = 0
        for state in self.state_relations:
            v_contribution += state.velocity_component(self)
        self.v = self.vref * exp((self.mu - self.mu0 - v_contribution) / self.a)

    def friction_evolution(self, loadpoint_vel):
        return self.k * (loadpoint_vel - self.v)


class RateState(object):
    def __init__(self):

        self.model_time = None  # List of times we want answers at
        self.loadpoint_velocity = []  # Matching list of velocities

        # Results of running the model
        self.results = namedtuple("results", ["time", "displacement", "slider_velocity", "friction", "states"])

    def _integrationStep(self, w, t, system):
        """
        Do the calculation for a time-step
        """

        system.mu = w[0]
        for i, state_variable in enumerate(system.state_relations):
            state_variable.state = w[i+1]

        system.velocity_evolution()

        # Find the loadpoint_velocity corresponding to the most recent time
        # <= the current time.
        loadpoint_vel = system.loadpoint_velocity[system.model_time <= t][-1]

        dmu_dt = system.friction_evolution(loadpoint_vel)

        step_results = [dmu_dt]

        for state_variable in system.state_relations:
            dtheta_dt = state_variable.evolve_state(system)
            step_results.append(dtheta_dt)

        return step_results

    def readyCheck(self):
        return True

    def solve(self, system, **kwargs):
        """
        Runs the integrator to actually solve the model and returns a
        named tuple of results.
        """
        odeint_kwargs = dict(rtol=1e-12, atol=1e-12)
        odeint_kwargs.update(kwargs)

        # Make sure we have everything set before we try to run
        if self.readyCheck() != True:
            raise RuntimeError('Not all model parameters set')

        # Initial conditions at t = 0
        w0 = [system.mu0]
        for state_variable in system.state_relations:
            state_variable._set_steady_state(system)
            w0.append(state_variable.state)

        # Solve it
        wsol = integrate.odeint(self._integrationStep, w0, system.model_time, args=(system,), **odeint_kwargs)
        self.results.friction = wsol[:, 0]
        self.results.states = wsol[:, 1:]
        self.results.time = system.model_time

        # Calculate slider velocity after we have solved everything
        velocity_contribution = 0
        for i, state_variable in enumerate(system.state_relations):
            velocity_contribution += state_variable.b * np.log(system.vref * self.results.states[:, i] / state_variable.Dc)

        self.results.slider_velocity = system.vref * np.exp((self.results.friction - system.mu0 - velocity_contribution) / system.a)

        # Calculate displacement from velocity and dt
        dt = np.ediff1d(system.model_time)
        self.results.displacement = np.cumsum(system.loadpoint_velocity[:-1] * dt)
        self.results.displacement = np.insert(self.results.displacement, 0, 0)

        return self.results

    def phasePlot(self, system):
        """
        Make a phase plot of the current model.
        """
        # Need to make sure the model has run! Duh!

        fig = plt.figure()
        ax1 = plt.subplot(111)
        ax1.plot(np.log(self.results.slider_velocity/system.vref), self.results.friction, color='k')
        ax1.set_xlabel('Log(V/Vref)')
        ax1.set_ylabel('Friction')
        plt.show()

    def dispPlot(self, system):
        """
        Make a standard plot with displacement as the x variable
        """
        fig = plt.figure(figsize=(12, 9))
        ax1 = plt.subplot(411)
        ax2 = plt.subplot(412, sharex=ax1)
        ax3 = plt.subplot(413, sharex=ax1)
        ax4 = plt.subplot(414, sharex=ax1)
        ax1.plot(self.results.displacement, self.results.friction, color='k')
        ax2.plot(self.results.displacement, self.results.states, color='k')
        ax3.plot(self.results.displacement, self.results.slider_velocity, color='k')
        ax4.plot(self.results.displacement, system.loadpoint_velocity, color='k')
        ax1.set_ylabel('Friction')
        ax2.set_ylabel('State')
        ax3.set_ylabel('Slider Velocity')
        ax4.set_ylabel('Loadpoint Velocity')
        ax4.set_xlabel('Displacement')
        plt.show()

    def timePlot(self, system):
        """
        Make a standard plot with time as the x variable
        """
        fig = plt.figure(figsize=(12, 9))
        ax1 = plt.subplot(411)
        ax2 = plt.subplot(412, sharex=ax1)
        ax3 = plt.subplot(413, sharex=ax1)
        ax4 = plt.subplot(414, sharex=ax1)
        ax1.plot(self.results.time, self.results.friction, color='k')
        ax2.plot(self.results.time, self.results.states, color='k')
        ax3.plot(self.results.time, self.results.slider_velocity, color='k')
        ax4.plot(self.results.time, system.loadpoint_velocity, color='k')
        ax1.set_ylabel('Friction')
        ax2.set_ylabel('State')
        ax3.set_ylabel('Slider Velocity')
        ax4.set_ylabel('Loadpoint Velocity')
        ax4.set_xlabel('Time')
        plt.show()
