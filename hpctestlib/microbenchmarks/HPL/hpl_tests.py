import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os

@rfm.simple_test
class HPLRunTest(rfm.RunOnlyRegressionTest):
    descr = 'Run HPL benchmark on different partitions'
    valid_systems = ['paramrudra.snbose:cpu', 'paramrudra.snbose:hm', 'paramrudra.snbose:gpu']
    valid_prog_environs = ['gnu']
    
    # Parameters for HPL.dat
    n_size = parameter([5000, 10000])
    p_grid = parameter([2])
    q_grid = parameter([2])
    
    @run_before('run')
    def setup_run(self):
        # Use the specific hash for the installed HPL
        self.modules = ['hpl/pp7qab2']
        
        p = self.p_grid
        q = self.q_grid
        
        if 'gpu' in self.current_partition.name:
            # Force single node for GPU to debug MPI issues
            self.num_tasks = 2
            self.num_tasks_per_node = 2
            p = 1
            q = 2
        else:
            self.num_tasks = self.p_grid * self.q_grid
            self.num_tasks_per_node = 4
            
        # Create HPL.dat
        hpl_dat_content = f"""HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out      output file name
6            device out (6=stdout,7=stderr,file)
1            # of problems sizes (N)
{self.n_size}         Ns
1            # of NBs
128          NBs
0            PMAP process mapping (0=Row-,1=Column-major)
1            # of process grids (P x Q)
{p}            Ps
{q}            Qs
16.0         threshold
1            # of panel fact
2            PFACTs (0=Left, 1=Crout, 2=Right)
1            # of recursive stopping criterium
4            NBMINs (>= 1)
1            # of panels in recursion
2            NDIVs
1            # of recursive panel fact.
1            RFACTs (0=Left, 1=Crout, 2=Right)
1            # of broadcast
1            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)
1            # of lookahead depth
1            DEPTHs (>=0)
2            SWAP (0=bin-syst,1=long,2=mix)
64           swapping threshold
0            L1 in (0=transposed,1=no-transposed) form
0            U  in (0=transposed,1=no-transposed) form
1            Equilibration (0=no,1=yes)
8            memory alignment in double (> 0)
"""
        self.prerun_cmds = [
            f'echo "{hpl_dat_content}" > HPL.dat'
        ]
        
    @run_before('run')
    def replace_launcher(self):
        # Use mpirun to avoid PMI issues with srun
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--mca pml ob1',
            '--mca btl ^openib',
        ]
        
    executable = 'xhpl'
    
    @sanity_function
    def validate_run(self):
        return sn.assert_found(r'End of Tests.', self.stdout)
    
    @performance_function('GFlops')
    def extract_performance(self):
        return sn.extractsingle(
            r'WR\w+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+(?P<gflops>[\d.E+]+)',
            self.stdout, 'gflops', float
        )
    
    reference = {
        'paramrudra.snbose:cpu': {
            'GFlops': (2, -0.1, None, 'GFlops')
        },
        'paramrudra.snbose:hm': {
            'GFlops': (2, -0.1, None, 'GFlops')
        },
        'paramrudra.snbose:gpu': {
            'GFlops': (2, -0.1, None, 'GFlops')
        }
    }
