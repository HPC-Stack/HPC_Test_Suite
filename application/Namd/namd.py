# rfmdocstart: echorand
import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import sys
sys.path.append('/home/samirs/reframe/application/module')
from module import parse_time_cmd


@rfm.simple_test
class NamdTest(rfm.RunOnlyRegressionTest):
    descr = 'A simple test that runs Namd'
    np = parameter([48,96,192,384])
    valid_systems = ['paramrudra.snbose:cpu']
    valid_prog_environs = ['gnu']
    num_tasks_per_node = 48
    modules = ['namd/ynfxnux'] 
    exclusive_access = True
    executable = 'namd2'
    executable_opts = ["apoa1.namd &> output"]
    
    env_vars = {
         'OMP_NUM_THREADS': '1'
     }
    prerun_cmds = [
        'tar -xvf apoa1.tar.gz',
        'cd apoa1',
        'time \\'
        ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()


    @run_before('run')
    def set_num_task(self):
         self.num_tasks = self.np

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    # @performance_function('timesteps/s', perf_key='Performance')
    # def extract_lammps_time(self):
    #     return sn.extractsingle(r'\s+(?P<perf>\S+) timesteps/s',self.stdout, 'perf', float)

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
# rfmdocend: echorand
