import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
from reframe.core.runtime import runtime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


def parse_time_cmd(s):
    mins, _, secs = s.strip().partition('m')
    return float(mins) * 60.0 + float(secs.rstrip('s'))


@rfm.simple_test
class wrfTest(rfm.RunOnlyRegressionTest):
    descr = 'WRF CPU benchmark — CONUS 2.5km'
    valid_systems = ['*:cpu']
    valid_prog_environs = ['foss']
    tags = {'sciapp', 'weather', 'wrf', 'cpu'}
    num_process = parameter([48, 96, 192, 384])
    sourcesdir = '/home/apps/hpc_inputs/applications/WRF/'
    exclusive_access = True
    modules = ['openmpi/kmaehjs','wrf/c3ap2ci']
    env_vars = {'OMP_NUM_THREADS': '1'}

    prerun_cmds = [
        'ulimit -s unlimited',
        'tar -xvf wrf_run.tar',
        'cd run',
        'time \\',
    ]

    executable = 'wrf.exe'

    reference = {
        '*': {'runtime_real': (0, None, None, 's')},
    }

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
        prefix = spack_ensure('wrf@4.5.1 build_type=dm+sm')
        if prefix:
            self.executable = os.path.join(prefix, 'run', 'wrf.exe')

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
