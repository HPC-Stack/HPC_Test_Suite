import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


def parse_time_cmd(s):
    mins, _, secs = s.strip().partition('m')
    return float(mins) * 60.0 + float(secs.rstrip('s'))


@rfm.simple_test
class cp2ktest(rfm.RunOnlyRegressionTest):
    descr = 'CP2K CPU benchmark — H2O energy'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'cp2k', 'cpu'}
    num_process = parameter([48, 96, 192, 384])
    num_tasks_per_node = 48
    exclusive_access = True

    executable = 'cp2k.popt'
    executable_opts = ['-i H2O.inp']

    reference = {
        '*': {'cp2k_time': (0, None, None, 's'), 'runtime_real': (0, None, None, 's')},
    }

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

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('cp2k@2024.1')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'cp2k.popt')

    @sanity_function
    def assert_cp2k(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='cp2k_time')
    def extract_cp2k_time(self):
        return sn.extractsingle(r'^ CP2K\s+\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)', self.stdout, 1, float)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
