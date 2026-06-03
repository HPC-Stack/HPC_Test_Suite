import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture



def parse_time_cmd(s):
    mins, _, secs = s.strip().partition('m')
    return float(mins) * 60.0 + float(secs.rstrip('s'))

@rfm.simple_test
class cp2kBuildTest(rfm.CompileOnlyRegressionTest):
    
    descr = 'Build CP2K with Spack'

    build_system = 'Spack'

    local = True

    num_process = variable(int, value=1)

    benchmark_type = variable(str)

    @run_before('compile')
    def setup_build(self):
        if self.benchmark_type == 'cpu':
            self.build_system.specs = ['cp2k ^openmpi~cuda schedulers=slurm']
        if self.benchmark_type == 'gpu':
            self.build_system.specs = ['cp2k+cuda cuda_arch=80 ^openmpi+cuda schedulers=slurm']

    @sanity_function
    def validate_build(self):
        return sn.assert_true(True)

@rfm.simple_test
class cp2ktest(rfm.RunOnlyRegressionTest):
    descr = 'CP2K CPU benchmark — H2O energy'
    
    benchmark_type = variable(str)

    num_process = variable(int, value=1)
    
    tags = {'sciapp', 'chemistry', 'cp2k', 'cpu'}

    sourcesdir = '/home/apps/hpc_inputs/applications/CP2K/'

    exclusive_access = True

    executable = 'cp2k.popt'
    executable_opts = ['-i H2O.inp']

    reference = {
        '*': {'cp2k_time': (0, None, None, 's'), 'runtime_real': (0, None, None, 's')},
    }

    build = fixture(
        cp2kBuildTest,
        scope='environment',
    )

    @run_before('run')
    def setup_run(self):
        if self.benchmark_type == 'cpu':
            self.valid_systems = ['*:cpu']
            self.num_tasks_per_node = 48
        else:
            self.valid_systems = ['*:gpu']
            self.num_tasks_per_node = 2

    prerun_cmds = ['time \\']

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)


    @sanity_function
    def assert_cp2k(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='cp2k_time')
    def extract_cp2k_time(self):
        return sn.extractsingle(r'^ CP2K\s+\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)', self.stdout, 1, float)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
