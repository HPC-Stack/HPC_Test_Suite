import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import subprocess

@rfm.simple_test
class HPCGRunTest(rfm.RunOnlyRegressionTest):
    descr = 'Run HPCG benchmark on different partitions'
        
    # Parameters for hpcg.dat
    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])
    num_nodes = parameter([1, 2])
    
    @run_before('run')
    def setup_run(self):
        # Discover paths on the login node
        def get_spack_output(cmd):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return res.stdout.strip()
            except:
                return None

        hpcg_prefix = get_spack_output(['spack', 'location', '-i', 'hpcg'])
        if not hpcg_prefix:
            self.modules = ['hpcg']
            self.executable = 'xhpcg'
        else:
            self.executable = os.path.join(hpcg_prefix, 'bin', 'xhpcg')
            
            ld_paths = set()
            try:
                res = subprocess.run(['ldd', self.executable], capture_output=True, text=True)
                for line in res.stdout.split('\n'):
                    if '=> /home/apps/spack' in line:
                        lib_path = line.split('=>')[1].split('(')[0].strip()
                        ld_paths.add(os.path.dirname(lib_path))
            except:
                pass
            
            mpi_bin = None
            for path in ld_paths:
                if 'intel-oneapi-mpi' in path:
                    mpi_bin = os.path.join(os.path.dirname(path), 'bin')
                    break
            
            self.env_vars = {
                'LD_LIBRARY_PATH': ':'.join(ld_paths) + ':$LD_LIBRARY_PATH',
                'I_MPI_PMI_LIBRARY': '/usr/lib64/libpmi2.so',
                'I_MPI_FABRICS': 'shm:ofi',
                'FI_PROVIDER': 'tcp'
            }
            if mpi_bin:
                self.env_vars['PATH'] = f'{mpi_bin}:$PATH'

        hpcg_dat_content = f"""HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
{self.nx} {self.ny} {self.nz}
{self.running_time}
"""
        self.prerun_cmds = [
            f'echo -e "{hpcg_dat_content}" > hpcg.dat'
        ]
        
        # Cat the result file to stdout for easier sanity checking
        self.postrun_cmds = ['cat HPCG-Benchmark_*.txt']
        
        if 'gpu' in self.current_partition.name:
            self.num_tasks_per_node = 2
            self.num_tasks = self.num_nodes * self.num_tasks_per_node
        else:
            self.num_tasks_per_node = 4
            self.num_tasks = self.num_nodes * self.num_tasks_per_node
            
        self.time_limit = '15m'
            
    @run_before('run')
    def replace_launcher(self):
        # Use srun with pmi2
        self.job.launcher = getlauncher('srun')()
        self.job.launcher.options = ['--mpi=pmi2']
        
    @sanity_function
    def validate_run(self):
        # Check stdout for the validation message (since we cat the file there)
        return sn.assert_found(r'HPCG result is VALID', self.stdout)
    
    @performance_function('GFlops')
    def extract_performance(self):
        return sn.extractsingle(
            r'Final Summary::HPCG result is VALID with a GFLOP/s rating of=(?P<gflops>[\d.]+)',
            self.stdout, 'gflops', float
        )
    
    reference = {
        'paramrudra.snbose:cpu': {
            'GFlops': (0.01, -0.1, None, 'GFlops')
        },
        'paramrudra.snbose:hm': {
            'GFlops': (0.01, -0.1, None, 'GFlops')
        },
        'paramrudra.snbose:gpu': {
            'GFlops': (0.01, -0.1, None, 'GFlops')
        }
    }
