# Copyright 2016-2024 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture


@rfm.simple_test
class OsuBuildTest(rfm.CompileOnlyRegressionTest):
    descr = 'Build OSU micro-benchmarks with Spack'

    valid_systems = ['*']
    valid_prog_environs = ['*']
    build_system = 'Spack'
    local = True
    build_type = parameter(['cpu', 'cuda'])

    spack_spec = variable(str)

    @run_before('compile')
    def setup_build(self):
        mapping = {
            'cpu': 'osu-micro-benchmarks ~cuda ~rocm ^openmpi',
            'cuda': 'osu-micro-benchmarks +cuda cuda_arch=80 ^openmpi+cuda cuda_arch=80',
        }
        self.spack_spec = mapping[self.build_type]
        self.build_system.specs = [self.spack_spec]

    @sanity_function
    def validate_build(self):
        return sn.assert_true(True)


class osu_benchmark(rfm.RunOnlyRegressionTest):
    '''OSU benchmark test base class.'''

    valid_systems = ['*']
    valid_prog_environs = ['*']

    num_warmup_iters = variable(int, value=10)
    num_iters = variable(int, value=1000)
    message_size = variable(int)
    device_buffers = variable(str, value='cpu')

    num_tasks = required
    num_tasks_per_node = 1

    benchmark_info = parameter([
        ('mpi.collective.osu_alltoall', 'latency'),
        ('mpi.collective.osu_allreduce', 'latency'),
        ('mpi.pt2pt.osu_bw', 'bandwidth'),
        ('mpi.pt2pt.osu_latency', 'latency')
    ], fmt=lambda x: x[0], loggable=True)

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('setup')
    def setup_per_benchmark(self):
        bench, bench_metric = self.benchmark_info
        if bench_metric == 'latency':
            self.message_size = 8
            unit = 'us'
        elif bench_metric == 'bandwidth':
            self.message_size = 4194304
            unit = 'MB/s'
        else:
            raise ValueError(f'unknown benchmark metric: {bench_metric}')

        self.executable = bench.split('.')[-1]
        self.executable_opts = ['-m', f'1:{self.message_size}',
                                '-x', f'{self.num_warmup_iters}',
                                '-i', f'{self.num_iters}', '-c']

        if self.device_buffers != 'cpu':
            self.executable_opts += ['-d', self.device_buffers]

        if bench.startswith('mpi.pt2pt'):
            self.executable_opts += ['D', 'D']
            self.num_tasks = 2

        self.perf_variables = {
            bench_metric: sn.make_performance_function(
                self._extract_metric, unit
            )
        }

    @sanity_function
    def validate_test(self):
        return sn.assert_found(rf'^{self.message_size}.*Pass', self.stdout)

    @deferrable
    def _extract_metric(self):
        return sn.extractsingle(rf'^{self.message_size}\s+(\S+)',
                                self.stdout, 1, float)


@rfm.simple_test
class osu_run(osu_benchmark):
    '''Run-only OSU benchmark test (binary must be in PATH)'''

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)


@rfm.simple_test
class osu_build_run(osu_benchmark):
    '''OSU benchmark test (build and run via Spack)'''

    build = fixture(OsuBuildTest, scope='environment')

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def load_spack_env(self):
        spack_env = os.path.join(self.build.stagedir, 'rfm_spack_env')
        spec = self.build.spack_spec
        self.prerun_cmds = [
            f'eval `spack -e {spack_env} load --sh {spec}`',
            f'which {self.executable}',
        ]
