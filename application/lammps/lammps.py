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
class lammpsTest(rfm.RunOnlyRegressionTest):
    descr = 'LAMMPS CPU benchmark — LJ melt'
    np = parameter([48, 96, 192, 384])
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'chemistry', 'lammps', 'cpu'}
    num_tasks_per_node = 48
    exclusive_access = True
    executable = 'lmp'
    executable_opts = ["-in in.lj.txt"]

    env_vars = {'OMP_NUM_THREADS': '1'}

    prerun_cmds = ['time \\']

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
        prefix = spack_ensure('lammps@20240205')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'lmp')

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
