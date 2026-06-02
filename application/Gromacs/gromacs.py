import os
import sys

import reframe as rfm
import reframe.utility.sanity as sn

from reframe.core.backends import getlauncher

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module'))
from module import parse_time_cmd

sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'continuousbench', 'hooks'
    )
)

from env_capture import add_env_capture


@rfm.simple_test
class GromacsBuildTest(rfm.CompileOnlyRegressionTest):
    descr = 'Build GROMACS with Spack'

    build_system = 'Spack'

    local = True

    num_process = variable(int, value=1)

    benchmark_type = variable(str)

    spec = variable(str, value='gromacs ^openmpi~cuda schedulers=slurm')

    @run_before('compile')
    def setup_build(self):
        self.build_system.specs = [self.spec]

    @sanity_function
    def validate_build(self):
        return sn.assert_true(True)


@rfm.simple_test
class GromacsBenchmark(rfm.RunOnlyRegressionTest):
    descr = 'GROMACS benchmark'

    valid_prog_environs = ['gnu']

    benchmark_type = variable(str)

    num_process = variable(int, value=1)

    sourcesdir = '/home/apps/hpc_inputs/applications/GROMACS/'

    exclusive_access = True

    build = fixture(
        GromacsBuildTest,
        scope='environment'
    )

    @run_after('init')
    def setup_test(self):

        if self.benchmark_type == 'cpu':
            self.valid_systems = ['*:cpu']
            self.gromacs_spec = (
                'gromacs ^openmpi~cuda schedulers=slurm'
            )

            self.num_tasks_per_node = 48

            self.executable_opts = [
                'mdrun',
                '-nsteps', '50000',
                '-s', 'water_pme.tpr'
            ]

        else:
            self.valid_systems = ['*:gpu']
            self.gromacs_spec = (
                'gromacs+cuda cuda_arch=80 '
                '^openmpi+cuda schedulers=slurm'
            )

            self.num_tasks_per_node = 2

            self.executable_opts = [
                'mdrun',
                '-nsteps', '500000',
                '-ntomp', '2',
                '-nb', 'gpu',
                '-s', 'water_pme.tpr'
            ]

    @run_before('run')
    def prepare_run(self):

        spack_env = os.path.join(
            self.build.stagedir,
            'rfm_spack_env'
        )

        self.prerun_cmds = [
            f'eval `spack -e {spack_env} load --sh {self.gromacs_spec}`',
            'which gmx_mpi',
            'which mpirun',
            'tar -xvf water_GMX50_bare.tar.gz',
            'cd water-cut1.0_GMX50_bare/3072',
            'gmx_mpi grompp -f pme.mdp '
            '-c conf.gro -p topol.top -o water_pme.tpr'
        ]

        self.num_tasks = self.num_process

    executable = 'gmx_mpi'

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_run(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('ns/day')
    def perf(self):
        return sn.extractsingle(
            r'Performance:\s+(\S+)',
            self.stderr,
            1,
            float
        )
