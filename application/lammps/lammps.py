# rfmdocstart: echorand
import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import sys
sys.path.append('/home/samirs/reframe/application/module')
from module import parse_time_cmd


@rfm.simple_test
class lammpsTest(rfm.RunOnlyRegressionTest):
    descr = 'A simple test that runs lammps'
    np = parameter([48,96,192,384])
    valid_systems = ['paramrudra.iuac:hm']
    valid_prog_environs = ['gnu']
    num_tasks_per_node = 48
    modules = ['lammps/feqr35c','intel-oneapi-mpi/3alw73q'] #intel-oneapi-mpi@2021.6.0 fftw +openmp/2tm3alt
    exclusive_access = True
    executable = 'lmp '
    executable_opts = ["-in in.lj.txt"]
    
    env_vars = {
         'OMP_NUM_THREADS': '1'
     }
    prerun_cmds = [
        #'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/apps/spack/opt/spack/linux-centos7-cascadelake/gcc-11.2.0/fftw-3.3.10-2tm3altwm7aflowjr5n6rgyrvg343byw/lib',
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
