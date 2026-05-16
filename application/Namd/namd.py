import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module'))
from module import parse_time_cmd
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


@rfm.simple_test
class NamdTest(rfm.RunOnlyRegressionTest):
    descr = 'NAMD CPU benchmark — apoa1'
    np = parameter([48, 96, 192, 384])
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'namd', 'cpu'}
    num_tasks_per_node = 48
    exclusive_access = True
    executable = 'namd2'
    executable_opts = ["apoa1.namd > output"]

    env_vars = {'OMP_NUM_THREADS': '1'}

    prerun_cmds = [
        'tar -xvf apoa1.tar.gz',
        'cd apoa1',
        'time \\',
    ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.np

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('namd')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'namd2')

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
