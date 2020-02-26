# -*- coding: utf-8 -*-
#
# network_params.py
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.

"""PyNEST Microcircuit: Network Parameters
---------------------------------------------

A dictionary with base network and neuron parameters is enhanced with derived
parameters.

"""

import numpy as np


def get_mean_delays(mean_delay_exc, mean_delay_inh, number_of_pop):
    """ Creates matrix containing the delays of all connections.

    Parameters
    ----------
    mean_delay_exc
        Delay of the excitatory connections.
    mean_delay_inh
        Delay of the inhibitory connections.
    number_of_pop
        Number of populations.

    Returns
    -------
    mean_delays
        Matrix specifying the mean delay of all connections.

    """

    dim = number_of_pop
    mean_delays = np.zeros((dim, dim))
    mean_delays[:, 0:dim:2] = mean_delay_exc
    mean_delays[:, 1:dim:2] = mean_delay_inh
    return mean_delays


def get_std_delays(std_delay_exc, std_delay_inh, number_of_pop):
    """ Creates matrix containing the standard deviations of all delays.

    Parameters
    ----------
    std_delay_exc
        Standard deviation of excitatory delays.
    std_delay_inh
        Standard deviation of inhibitory delays.
    number_of_pop
        Number of populations in the microcircuit.

    Returns
    -------
    std_delays
        Matrix specifying the standard deviations of all delays.

    """

    dim = number_of_pop
    std_delays = np.zeros((dim, dim))
    std_delays[:, 0:dim:2] = std_delay_exc
    std_delays[:, 1:dim:2] = std_delay_inh
    return std_delays


def get_mean_PSP_matrix(PSP_e, g, number_of_pop):
    """ Creates a matrix of the mean evoked postsynaptic potential.

    The function creates a matrix of the mean evoked postsynaptic
    potentials between the recurrent connections of the microcircuit.
    The weight of the connection from L4E to L23E is doubled.

    Parameters
    ----------
    PSP_e
        Mean evoked potential.
    g
        Relative strength of the inhibitory to excitatory connection.
    number_of_pop
        Number of populations in the microcircuit.

    Returns
    -------
    weights
        Matrix of the weights for the recurrent connections.

    """
    dim = number_of_pop
    weights = np.zeros((dim, dim))
    exc = PSP_e
    inh = PSP_e * g
    weights[:, 0:dim:2] = exc
    weights[:, 1:dim:2] = inh
    weights[0, 2] = exc * 2
    return weights


def get_std_PSP_matrix(PSP_rel, number_of_pop):
    """ Relative standard deviation matrix of postsynaptic potentials created.

    The relative standard deviation matrix of the evoked postsynaptic potentials
    for the recurrent connections of the microcircuit is created.

    Parameters
    ----------
    PSP_rel
        Relative standard deviation of the evoked postsynaptic potential.
    number_of_pop
        Number of populations in the microcircuit.

    Returns
    -------
    std_mat
        Matrix of the standard deviation of postsynaptic potentials.

    """
    dim = number_of_pop
    std_mat = np.zeros((dim, dim))
    std_mat[:, :] = PSP_rel
    return std_mat


net_dict = {
    # neuron model
    'neuron_model': 'iaf_psc_exp',
    # The default recording device is the spike_detector. If you also
    # want to record the membrane potentials of the neurons, add
    # 'voltmeter' to the list. Nothing will be recorded if an empty list is
    # given.
    'rec_dev': ['spike_detector'],
    # names of the simulated neuronal populations
    'populations': ['L23E', 'L23I', 'L4E', 'L4I', 'L5E', 'L5I', 'L6E', 'L6I'],
    # number of neurons in the different populations (the order of the
    # elements corresponds to the names of the variable 'populations')
    'N_full': np.array([20683, 5834, 21915, 5479, 4850, 1065, 14395, 2948]),
    # Mean rates of the different populations in the non-scaled version
    # of the microcircuit. Necessary for the scaling of the network.
    # The order corresponds to the order in 'populations'.
    'full_mean_rates':
        np.array([0.971, 2.868, 4.746, 5.396, 8.142, 9.078, 0.991, 7.523]),
    # connection probabilities (the first index corresponds to the targets
    # and the second to the sources)
    'conn_probs':
        np.array(
            [[0.1009, 0.1689, 0.0437, 0.0818, 0.0323, 0., 0.0076, 0.],
             [0.1346, 0.1371, 0.0316, 0.0515, 0.0755, 0., 0.0042, 0.],
             [0.0077, 0.0059, 0.0497, 0.135, 0.0067, 0.0003, 0.0453, 0.],
             [0.0691, 0.0029, 0.0794, 0.1597, 0.0033, 0., 0.1057, 0.],
             [0.1004, 0.0622, 0.0505, 0.0057, 0.0831, 0.3726, 0.0204, 0.],
             [0.0548, 0.0269, 0.0257, 0.0022, 0.06, 0.3158, 0.0086, 0.],
             [0.0156, 0.0066, 0.0211, 0.0166, 0.0572, 0.0197, 0.0396, 0.2252],
             [0.0364, 0.001, 0.0034, 0.0005, 0.0277, 0.008, 0.0658, 0.1443]]
    ),
    # number of external connections to the different populations (the order
    # corresponds to the order in 'populations')
    'K_ext': np.array([1600, 1500, 2100, 1900, 2000, 1900, 2900, 2100]),
    # factor to scale the indegrees
    'K_scaling': 0.1,
    # factor to scale the number of neurons
    'N_scaling': 0.1,
    # mean amplitude of excitatory postsynaptic potential (in mV)
    'PSP_e': 0.15,
    # relative standard deviation of the postsynaptic potential
    'PSP_sd': 0.1,
    # relative inhibitory synaptic strength
    'g': -4,
    # rate of the Poissonian spike generator (in Hz)
    'bg_rate': 8.,
    # turn Poisson input on or off (True or False)
    # if False: DC input is applied for compensation
    'poisson_input': True,
    # delay of the Poisson generator (in ms)
    'poisson_delay': 1.5,
    # mean delay of excitatory connections (in ms)
    'mean_delay_exc': 1.5,
    # mean delay of inhibitory connections (in ms)
    'mean_delay_inh': 0.75,
    # relative standard deviation of the delay of excitatory and
    # inhibitory connections
    'rel_std_delay': 0.5,
    # initial conditions for the membrane potential, options are:
    # 'original': uniform mean and standard deviation for all populations as
    #             used in earlier implementations of the model
    # 'optimized': population-specific mean and standard deviation, allowing a
    #              reduction of the initial activity burst in the network
    #              (default)
    # choose either 'original' or 'optimized'
    'V0_type': 'optimized',
    # prameters of the neuron model
    'neuron_params': {
        # membrane qpotential average for the neurons (in mV)
        'V0_mean': {'original': -58.0,
                    'optimized': [-68.28, -63.16, -63.33, -63.45,
                                  -63.11, -61.66, -66.72, -61.43]},
        # standard deviation of the average membrane potential (in mV)
        'V0_sd': {'original': 10.0,
                  'optimized': [5.36, 4.57, 4.74, 4.94,
                                4.94, 4.55, 5.46, 4.48]},
        # reset membrane potential of the neurons (in mV)
        'E_L': -65.0,
        # threshold potential of the neurons (in mV)
        'V_th': -50.0,
        # membrane potential after a spike (in mV)
        'V_reset': -65.0,
        # membrane capacitance (in pF)
        'C_m': 250.0,
        # membrane time constant (in ms)
        'tau_m': 10.0,
        # time constant of postsynaptic currents (in ms)
        'tau_syn': 0.5,
        # refractory period of the neurons after a spike (in ms)
        't_ref': 2.0}
}

updated_dict = {
    # matrix of mean PSPs
    'PSP_mean_matrix': get_mean_PSP_matrix(
        net_dict['PSP_e'], net_dict['g'], len(net_dict['populations'])
    ),
    # matrix of standard deviations of PSPs
    'PSP_std_matrix': get_std_PSP_matrix(
        net_dict['PSP_sd'], len(net_dict['populations'])
    ),
    # matrix of mean delays
    'mean_delay_matrix': get_mean_delays(
        net_dict['mean_delay_exc'], net_dict['mean_delay_inh'],
        len(net_dict['populations'])
    ),
    # matrix of standard deviations of delays
    'std_delay_matrix': get_std_delays(
        net_dict['mean_delay_exc'] * net_dict['rel_std_delay'],
        net_dict['mean_delay_inh'] * net_dict['rel_std_delay'],
        len(net_dict['populations'])
    ),
}

net_dict.update(updated_dict)
