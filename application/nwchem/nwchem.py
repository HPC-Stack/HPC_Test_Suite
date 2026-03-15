import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
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
class nwchemTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs nwchem'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['gnu']
    #np = parameter((for i in [48,96,202,384]))
    num_process = parameter([48,96,192,384])
    num_tasks_per_node = 48
    sourcesdir = 'src'
    modules = ['nwchem','intel-oneapi-mpi/akaysq6']
    exclusive_access = True
    
    prerun_cmds = [
            #'ml load openmpi/4.1.4',
            'time \\'# want to run mpi task under time
        ]

    executable = 'nwchem'
    executable_opts = ["input.nw"]

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