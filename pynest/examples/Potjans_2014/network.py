# -*- coding: utf-8 -*-
#
# network.py
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#/
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.

"""PyNEST Microcircuit: Network Class
----------------------------------------

Main file of the microcircuit defining the ``Network`` class with functions to
build and simulate the network.

"""

import os
import numpy as np
import nest
import helpers

class Network:
    """ Provides functions to setup NEST, to create and connect all nodes of
    the network, to simulate, and to evaluate the resulting spike data.
    
    Instantiating a Network object already initializes the NEST kernel.

    Parameters
    ---------
    sim_dict
        Dictionary containing all parameters specific to the simulation
        (see: ``sim_params.py``).
    net_dict
         Dictionary containing all parameters specific to the neuron and
         network models (see: ``network_params.py``).
    stim_dict
        Optional dictionary containing all parameter specific to the stimulus
        (see: ``stimulus_params.py``)

    """
    def __init__(self, sim_dict, net_dict, stim_dict=None):
        self.sim_dict = sim_dict
        self.net_dict = net_dict
        if stim_dict is not None:
            self.stim_dict = stim_dict
        else:
            self.stim_dict = None

        # derive parameters based on input dictionaries
        self.__derive_parameters()

        # data directory
        self.data_path = sim_dict['data_path']
        if nest.Rank() == 0:
            if os.path.isdir(self.data_path):
                message = '  Directory already existed.'
                if self.sim_dict['overwrite_files']:
                    message += ' Existing data will be overwritten.'
            else:
                os.mkdir(self.data_path)
                message = '  Directory has been created.'
            print('Data will be written to: {}\n{}'.format(self.data_path,
                                                           message))

        # initialize the NEST kernel
        self.__setup_nest()


    def create(self):
        """ Creates all network nodes.

        Neuronal populations and recording and stimulating devices are created.

        """
        self.__create_neuronal_populations()
        if len(self.net_dict['rec_dev']) > 0:
            self.__create_recording_devices()
        if self.net_dict['poisson_input']:
            self.__create_poisson_bg_input()
        if self.stim_dict['thalamic_input']:
            self.__create_thalamic_stim_input()
        if self.stim_dict['dc_input']:
            self.__create_dc_stim_input()


    def connect(self):
        """ Connects the network.
        
        Recurrent connections among neurons of the neuronal populations are 
        established, and recording and stimulating devices are connected.

        """
        self.__connect_neuronal_populations()

        if len(self.net_dict['rec_dev']) > 0:
            self.__connect_recording_devices()
        if self.net_dict['poisson_input']:
            self.__connect_poisson_bg_input()
        if self.stim_dict['thalamic_input']:
            self.__connect_thalamic_stim_input()
        if self.stim_dict['dc_input']:
            self.__connect_dc_stim_input()

        
    def simulate(self):
        """ Simulates the microcircuit. """
        nest.Simulate(self.sim_dict['t_sim'])


    def evaluate(self, raster_plot_interval, firing_rates_interval):
        """ Displays simulation results.

        Creates a spike raster plot.
        Calculates the firing rate of each population and displays them as a
        box plot.

        Parameters
        ----------
        raster_plot_interval
            Times to start and stop loading spike times for raster plot
            (included).
        firing_rates_interval
            Times to start and stop lading spike times for computing firing
            rates (included).

        Returns
        -------
            None

        """
        if nest.Rank() == 0:
            print(
                'Interval to plot spikes: %s ms'
                % np.array2string(raster_plot_interval)
                )
            helpers.plot_raster(
                self.data_path, 'spike_detector',
                raster_plot_interval[0], raster_plot_interval[1]
                )

            print(
                'Interval to compute firing rates: %s ms'
                % np.array2string(firing_rates_interval)
                )
            helpers.firing_rates(
                self.data_path, 'spike_detector',
                firing_rates_interval[0], firing_rates_interval[1]
                )
            helpers.boxplot(self.net_dict, self.data_path)


    def __derive_parameters(self):
        """
        Derives and adjusts parameters and stores them as class attributes.
        """
        self.num_pops = len(self.net_dict['populations'])

        # total number of synapses between neuronal populations before scaling
        full_num_synapses = helpers.num_synapses_from_conn_probs(
            self.net_dict['conn_probs'],
            self.net_dict['N_full'],
            self.net_dict['N_full'])

        # scaled numbers of neurons and synapses
        self.num_neurons = (self.net_dict['N_full'] \
                * self.net_dict['N_scaling']).astype(int)
        self.num_synapses = (full_num_synapses \
            * self.net_dict['N_scaling'] \
            * self.net_dict['K_scaling']).astype(int)
        self.ext_indegrees = (self.net_dict['K_ext'] \
            * self.net_dict['K_scaling']).astype(int)

        # conversion from PSP to PSC
        mean_PSC_matrix = helpers.weight_as_current_from_potential(
            self.net_dict['PSP_mean_matrix'],
            self.net_dict['neuron_params']['C_m'],
            self.net_dict['neuron_params']['tau_m'],
            self.net_dict['neuron_params']['tau_syn'])
        PSC_ext = helpers.weight_as_current_from_potential(
            self.net_dict['PSP_e'],
            self.net_dict['neuron_params']['C_m'],
            self.net_dict['neuron_params']['tau_m'],
            self.net_dict['neuron_params']['tau_syn'])

        # DC input compensates for potentially missing Poisson input
        if self.net_dict['poisson_input']:
            DC_amp = np.zeros(self.num_pops)
        else:
            if nest.Rank() == 0:
                print('DC input compensates for missing Poisson input')
            DC_amp = helpers.dc_input_compensating_poisson(
                self.net_dict['bg_rate'], self.net_dict['K_ext'],
                self.net_dict['neuron_params']['tau_syn'],
                PSC_ext)
            print(DC_amp)

        # adjust weights and DC amplitude if the number of synapses is scaled
        if self.net_dict['K_scaling'] != 1:
            mean_PSC_matrix, PSC_ext, DC_amp = \
                helpers.adjust_weights_and_input_to_synapse_scaling(
                    self.net_dict['N_full'],
                    full_num_synapses, self.net_dict['K_scaling'],
                    mean_PSC_matrix, PSC_ext,
                    self.net_dict['neuron_params']['tau_syn'],
                    self.net_dict['full_mean_rates'],
                    DC_amp,
                    self.net_dict['poisson_input'],
                    self.net_dict['bg_rate'], self.net_dict['K_ext'])

        # store final parameters as class attributes
        self.mean_weight_matrix = mean_PSC_matrix
        self.std_weight_matrix = self.net_dict['PSP_std_matrix']
        self.weight_ext = PSC_ext
        self.DC_amp = DC_amp
 
        # thalamic input
        if self.stim_dict['thalamic_input']:
            nr_synapses_th = helpers.num_synapses_from_conn_probs(
                self.stim_dict['conn_probs_th'],
                self.stim_dict['n_thal'],
                self.net_dict['N_full'])[0]
            self.thalamic_weight = helpers.weight_as_current_from_potential(
                self.stim_dict['PSP_th'],
                self.net_dict['neuron_params']['C_m'],
                self.net_dict['neuron_params']['tau_m'],
                self.net_dict['neuron_params']['tau_syn'])
            if self.net_dict['K_scaling'] != 1:
                nr_synapses_th *= self.net_dict['K_scaling']
                self.thalamic_weight /= np.sqrt(self.net_dict['K_scaling'])
            self.nr_synapses_th = nr_synapses_th.astype(int)
            
        if nest.Rank() == 0:
            message = 'Neuron numbers are scaled by {:.3f}.\n'.format(
                self.net_dict['N_scaling'])
            message += 'Indegrees are scaled by {:.3f}'.format(
                self.net_dict['K_scaling'])
            if self.net_dict['K_scaling'] != 1:
                message += '\n Weights and DC input are adjusted to compensate.'
            print(message)


    def __setup_nest(self):
        """ Hands parameters to the NEST kernel.

        Resets the NEST kernel and passes parameters to it.
        The number of seeds for random number generation are computed based on
        the total number of virtual processes
        (number of MPI processes x number of threads per MPI process).
        """
        nest.ResetKernel()

        # set seeds for random number generation
        nest.SetKernelStatus(
            {'local_num_threads': self.sim_dict['local_num_threads']})
        N_vp = nest.GetKernelStatus('total_num_virtual_procs')
       
        master_seed = self.sim_dict['master_seed']
        grng_seed = master_seed + N_vp
        rng_seeds = (master_seed + N_vp + 1 + np.arange(N_vp)).tolist()

        if nest.Rank() == 0:
            print('Master seed: %i ' % master_seed)
            print('  Total number of virtual processes: %i' % N_vp)
            print('  Global random number generator seed: %i' % grng_seed)
            print(
                '  Seeds for random number generators of virtual processes: %r'
                % rng_seeds
                )

        # pass parameters to NEST kernel
        self.sim_resolution = self.sim_dict['sim_resolution']
        kernel_dict = {
            'resolution': self.sim_resolution,
            'grng_seed': grng_seed,
            'rng_seeds': rng_seeds,
            'overwrite_files': self.sim_dict['overwrite_files'],
            'print_time': self.sim_dict['print_time'],
            }
        nest.SetKernelStatus(kernel_dict)


    def __create_neuronal_populations(self):
        """ Creates the neuronal populations.

        The neuronal populations are created and the parameters are assigned
        to them. The initial membrane potential of the neurons is drawn from
        normal distributions dependent on the parameter ``V0_type``.
        """
        if nest.Rank() == 0:
            print('Creating neuronal populations.')

        self.pops = []
        pop_file = open(
            os.path.join(self.data_path, 'population_nodeids.dat'), 'w+'
            )
        for i, pop in enumerate(self.net_dict['populations']):
            population = nest.Create(self.net_dict['neuron_model'],
                                     self.num_neurons[i])

            population.set(
                    tau_syn_ex=self.net_dict['neuron_params']['tau_syn'],
                    tau_syn_in=self.net_dict['neuron_params']['tau_syn'],
                    E_L=self.net_dict['neuron_params']['E_L'],
                    V_th=self.net_dict['neuron_params']['V_th'],
                    V_reset=self.net_dict['neuron_params']['V_reset'],
                    t_ref=self.net_dict['neuron_params']['t_ref'],
                    I_e=self.DC_amp[i]
                    )

            if self.net_dict['V0_type'] == 'optimized':
                population.set(V_m=nest.random.normal(
                    self.net_dict['neuron_params']['V0_mean']['optimized'][i],
                    self.net_dict['neuron_params']['V0_sd']['optimized'][i],
                    ))
            elif self.net_dict['V0_type'] == 'original':
                population.set(V_m=nest.random.normal(
                    self.net_dict['neuron_params']['V0_mean']['original'],
                    self.net_dict['neuron_params']['V0_sd']['original'],
                    ))
            self.pops.append(population)
            pop_file.write('%d  %d \n' % (
                population.global_id[0],
                population.global_id[-1]))
        pop_file.close()


    def __create_recording_devices(self):
        """ Creates one recording device of each kind per population.

        Only devices which are given in ``net_dict['rec_dev']`` are created.

        """
        if nest.Rank() == 0:
            print('Creating recording devices.')

        if 'spike_detector' in self.net_dict['rec_dev']:
            if nest.Rank() == 0:
                print('  Creating spike detectors.')
            sd_dict = {'record_to': 'ascii',
                      'label': os.path.join(self.data_path, 'spike_detector')}
            self.spike_detectors = nest.Create('spike_detector',
                                               n=self.num_pops,
                                               params=sd_dict) 

        if 'voltmeter' in self.net_dict['rec_dev']:
            if nest.Rank() == 0:
                print('  Creating voltmeters.')
            vm_dict = {'interval': self.sim_dict['rec_V_int'],
                      'record_to': 'ascii',
                      'record_from': ['V_m'],
                      'label': os.path.join(self.data_path, 'voltmeter')}
            self.voltmeters = nest.Create('voltmeter',
                                          n=self.num_pops,
                                          params=vm_dict)


    def __create_poisson_bg_input(self):
        """ Creates the Poisson generators for ongoing background input if
        specified in ``network_params.py``.
        If ``poisson_input`` is ``False``, DC input is applied for compensation
        in ``create_neuronal_populations()``.

        """
        if nest.Rank() == 0:
            print('Creating Poisson generators for background input.')

        self.poisson_bg_input = nest.Create('poisson_generator',
                                            n=self.num_pops)
        self.poisson_bg_input.rate = \
            self.net_dict['bg_rate'] * self.ext_indegrees


    def __create_thalamic_stim_input(self):
        """ Creates the thalamic neuronal population if specified in
        ``stimulus_params.py``.

        Thalamic neurons are of type ``parrot_neuron`` and receive input from a
        Poisson generator.
        Note that the number of thalamic neurons is not scaled with
        ``Ǹ_scaling``.

        """
        if nest.Rank() == 0:
            print('Creating thalamic input for external stimulation.')

        self.thalamic_population = nest.Create('parrot_neuron',
                                               n=self.stim_dict['n_thal'])

        self.poisson_th = nest.Create('poisson_generator')
        self.poisson_th.set(
            rate=self.stim_dict['th_rate'],
            start=self.stim_dict['th_start'],
            stop=(self.stim_dict['th_start'] + self.stim_dict['th_duration']))


    def __create_dc_stim_input(self):
        """ Creates DC generators for external stimulation if specified
        in ``stimulus_params.py``.

        """
        dc_amp_stim = self.net_dict['K_ext'] * self.stim_dict['dc_amp']
        if nest.Rank() == 0:
            print(""" Creating DC generators for external stimulation.
                  dc_amp_stim = {} pA""".format(dc_amp_stim))

        dc_dict = {'amplitude': dc_amp_stim,
                  'start': self.stim_dict['dc_start'],
                  'stop': (self.stim_dict['dc_start'] \
                          + self.stim_dict['dc_dur'])} 
        self.dc_stim_input = nest.Create('dc_generator', n=self.num_pops,
                                             params=dc_dict)


    def __connect_neuronal_populations(self):
        """ Creates the recurrent connections between neuronal populations. """
        if nest.Rank() == 0:
            print('Connecting neuronal populations recurrently.')

        mean_delays = self.net_dict['mean_delay_matrix']
        std_delays = self.net_dict['std_delay_matrix']
        for i, target_pop in enumerate(self.pops):
            for j, source_pop in enumerate(self.pops):
                synapse_nr = self.num_synapses[i][j]
                if synapse_nr >= 0.:
                    weight = self.mean_weight_matrix[i][j]
                    w_sd = abs(weight * self.std_weight_matrix[i][j])
                    conn_dict_rec = {
                        'rule': 'fixed_total_number', 'N': synapse_nr
                        }
                    syn_dict = {
                        'synapse_model': 'static_synapse',
                        'weight': {
                            'distribution': 'normal_clipped', 'mu': weight,
                            'sigma': w_sd
                            },
                        'delay': {
                            'distribution': 'normal_clipped',
                            'mu': mean_delays[i][j], 'sigma': std_delays[i][j],
                            'low': self.sim_resolution
                            }
                        }
                    if weight < 0:
                        syn_dict['weight']['high'] = 0.0
                    else:
                        syn_dict['weight']['low'] = 0.0
                    nest.Connect(
                        source_pop, target_pop,
                        conn_spec=conn_dict_rec,
                        syn_spec=syn_dict
                        )


    def __connect_recording_devices(self):
        """ Connects the recording devices to the microcircuit."""

        if nest.Rank == 0:
            print('Connecting recording devices.')

        for i, target_pop in enumerate(self.pops):
            if 'spike_detector' in self.net_dict['rec_dev']:
                nest.Connect(target_pop, self.spike_detectors[i])
            if 'voltmeter' in self.net_dict['rec_dev']:
                nest.Connect(self.voltmeters[i], target_pop)


    def __connect_poisson_bg_input(self):
        """ Connects the Poisson generators to the microcircuit."""
        if nest.Rank() == 0:
            print('Connecting Poisson generators for background input.')

        for i, target_pop in enumerate(self.pops):
            conn_dict_poisson = {'rule': 'all_to_all'}
            syn_dict_poisson = {
                'synapse_model': 'static_synapse',
                'weight': self.weight_ext,
                'delay': self.net_dict['poisson_delay']
                }
            nest.Connect(
                self.poisson_bg_input[i], target_pop,
                conn_spec=conn_dict_poisson,
                syn_spec=syn_dict_poisson
                )


    def __connect_thalamic_stim_input(self):
        """ Connects the Thalamic input to the neuronal populations. """

        if nest.Rank() == 0:
            print('Connecting Thalamic input.')

        # connect Poisson input to thalamic population
        nest.Connect(self.poisson_th, self.thalamic_population)

        # connect thalamic population to neuronal populations
        for i, target_pop in enumerate(self.pops):
            conn_dict_th = {
                'rule': 'fixed_total_number',
                'N': self.nr_synapses_th[i]
                }
            syn_dict_th = {
                'weight': {
                    'distribution': 'normal_clipped',
                    'mu': self.thalamic_weight,
                    'sigma': (
                        self.thalamic_weight * self.net_dict['PSP_sd']
                        ),
                    'low': 0.0
                    },
                'delay': {
                    'distribution': 'normal_clipped',
                    'mu': self.stim_dict['delay_th'][i],
                    'sigma': self.stim_dict['delay_th_sd'][i],
                    'low': self.sim_resolution
                    }
                }
            nest.Connect(
                self.thalamic_population, target_pop,
                conn_spec=conn_dict_th, syn_spec=syn_dict_th
                )


    def __connect_dc_stim_input(self):
        """ Connects the DC generators to the neuronal populations. """

        if self.stim_dict['dc_input']:
            if nest.Rank() == 0:
                print('Connecting DC generators.')

            for i, target_pop in enumerate(self.pops):
                nest.Connect(self.dc_stim_input[i], target_pop)
