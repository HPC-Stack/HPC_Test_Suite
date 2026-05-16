import reframe as rfm
import reframe.utility.sanity as sn
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module'))
from module import parse_time_cmd
from reframe.core.backends import getlauncher
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


@rfm.simple_test
class GromacsBuildTest(rfm.RegressionTest):
    descr = 'Build Gromacs using Spack'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'build', 'sciapp', 'chemistry', 'gromacs'}

    build_system = 'Spack'

    @run_before('compile')
    def setup_build(self):
        self.build_system.specs = ['gromacs@2024.2']

    executable = 'gmx_mpi'
    executable_opts = ['--version']

    @sanity_function
    def validate_build(self):
        return sn.assert_found(r'GROMACS', self.stdout)


@rfm.simple_test
class gromacTest_cpu(rfm.RunOnlyRegressionTest):
    descr = 'GROMACS CPU benchmark — water box'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'gromacs', 'cpu'}
    num_tasks_per_node = 48
    num_process = parameter([48, 96, 192, 384])
    sourcesdir = 'src'
    exclusive_access = True

    prerun_cmds = [
        'tar -xvf water_GMX50_bare.tar.gz',
        'cd water-cut1.0_GMX50_bare/3072',
        'gmx_mpi grompp -f pme.mdp -c conf.gro -p topol.top -o water_pme.tpr',
        'time \\',
    ]

    executable = 'gmx_mpi'
    executable_opts = ["mdrun -nsteps 5000 -s water_pme.tpr"]

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('gromacs@2024.2')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'gmx_mpi')

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)


@rfm.simple_test
class gromacTest_gpu(rfm.RunOnlyRegressionTest):
    descr = 'GROMACS GPU benchmark — water box'
    valid_systems = ['*:gpu']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'gromacs', 'gpu'}
    num_tasks_per_node = 40
    num_process = parameter([48, 96, 192])
    sourcesdir = 'src'
    exclusive_access = True

    prerun_cmds = [
        'tar -xvf water_GMX50_bare.tar.gz',
        'cd water-cut1.0_GMX50_bare/3072',
        'gmx_mpi grompp -f pme.mdp -c conf.gro -p topol.top -o water_pme.tpr',
        'time \\',
    ]

    executable = 'gmx_mpi'
    executable_opts = ["mdrun -nsteps 50000 -ntomp 2 -nb gpu -s water_pme.tpr"]

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('gromacs@2024.2')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'gmx_mpi')

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('ns/day', perf_key='ns_per_day')
    def extract_runtime_real(self):
        return sn.extractsingle(r'Performance:\s+(\S+)\s+(\S+)', self.stderr, 1, float)
