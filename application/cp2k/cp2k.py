import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
#from reframe.core.launchers import LauncherWrapper
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
class cp2ktest(rfm.RunOnlyRegressionTest):
    #np = parameter([x for x in range(10,101,10)])
    valid_systems = ['paramrudra.snbose:cpu']
    valid_prog_environs = ['gnu']
    num_process = parameter([48,96,192,384])
    num_tasks_per_node = 48
    #modules = ['cp2k'] #
    executable = 'cp2k.popt'
    executable_opts = ['-i H2O.inp']  #'-o H2O.out'
    prerun_cmds = [
            'source  /home/apps/SPACK/spack/share/spack/setup-env.sh',
            'time \\',
            'spack load cp2k'
        ]
    reference = {
        '*': {
           'cp2k_time': (0, None, None, 's'),
        }
    }

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process
         
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()
    
    # @run_before('run')
    # def set_cpu_oversubscribe(self):
    #     self.job.launcher.options = ['--host /home/cdacapp/parikshit/reframe/hostfile']
    # #    self.job.launcher = LauncherWrapper(self.job.launcher, 'time')
    # #    self.num_tasks = self.np
  
   
    @sanity_function
    def assert_cp2k(self):
        return sn.assert_eq(self.job.exitcode, 0)
    
    @performance_function('s', perf_key='cp2k_time')
    def extract_cp2k_time(self):
        return sn.extractsingle(r'^ CP2K\s+\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)', self.stdout, 1, float)
#  Regex patten                     CP2K 1  1.0    0.407    0.418  111.874  111.875

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)                            
    
