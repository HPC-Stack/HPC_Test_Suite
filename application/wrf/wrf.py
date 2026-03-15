import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
from reframe.core.runtime import runtime
import sys
import os

def parse_time_cmd(s):	
    """ Convert timing info from `time` into float seconds.	
       E.g. parse_time('0m0.000s') -> 0.0	
    """	
    
    s = s.strip()
    mins, _, secs = s.partition('m')	
    mins = float(mins)	
    secs = float(secs.rstrip('s'))	

    return mins * 60.0 + secs

@rfm.simple_test
class wrfTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs wrf'
    valid_systems = ['paramrudra.snbose:hm']
    valid_prog_environs = ['gnu']
    modules = ['intel-oneapi-mpi/bzriwnc','intel-oneapi-compilers@2023.2.0']
    num_process = parameter([48,96,192,384])
    #num_process = parameter([24])   #1056
    sourcesdir = '/home/apps/hpc_inputs/applications/WRF/'                           #'src'
    exclusive_access = True
    env_vars = {
        'OMP_NUM_THREADS': '1',
    }
    prerun_cmds = [
            '#wget https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus2.5km.tar.gz',
            'ulimit -s unlimited',
            'tar -xvf wrf_run.tar ',
            'ml load apps/wrf-4.5.1',
            'cd run',
            'time \\'# want to run mpi task under time
        ]

    executable = 'wrf.exe'

    reference = {
        '*': {
            'runtime_real': (0, None, None, 's'),
        }
    }

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process
    
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)


    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)