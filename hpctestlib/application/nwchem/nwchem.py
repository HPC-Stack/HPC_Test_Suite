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
class nwchemTest(rfm.RunOnlyRegressionTest):
    descr = 'NWChem CPU benchmark — input.nw'
    valid_systems = ['*:cpu']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'nwchem', 'cpu'}
    num_process = parameter([48, 96, 192, 384])
    num_tasks_per_node = 48
    exclusive_access = True
    sourcesdir = '/home/apps/hpc_inputs/applications/NWCHEM/'
    prerun_cmds = ['time \\']
    modules = ['openmpi/s3crpr4', 'nwchem/qn3o5ac']
    executable = 'nwchem'
    executable_opts = ["input2.nw"]

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

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
