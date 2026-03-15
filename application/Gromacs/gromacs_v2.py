import reframe as rfm
import reframe.utility.sanity as sn
from hpc_base import SpackAppTest
from reframe.core.backends import getlauncher

@rfm.simple_test
class GromacsTest(SpackAppTest):
    descr = 'Gromacs performance test'
    valid_systems = ['paramrudra.snbose:cpu', 'paramrudra.snbose:gpu']
    valid_prog_environs = ['gnu']
    spack_spec = 'gromacs@2024.2'
    
    num_process = parameter([48, 96])
    num_tasks_per_node = 48
    exclusive_access = True
    
    sourcesdir = 'src' # Assuming src exists with necessary files
    
    executable = 'gmx_mpi'
    executable_opts = ['mdrun', '-nsteps', '5000', '-s', 'water_pme.tpr']
    
    @run_before('run')
    def prepare_run(self):
        self.num_tasks = self.num_process
        if 'gpu' in self.current_partition.name:
            self.executable_opts += ['-nb', 'gpu']
        
        self.prerun_cmds = [
            'tar -xvf water_GMX50_bare.tar.gz',
            'cd water-cut1.0_GMX50_bare/3072',
            'gmx_mpi grompp -f pme.mdp -c conf.gro -p topol.top -o water_pme.tpr',
            'time \\'
        ]

    @run_before('run')
    def set_launcher(self):
        self.job.launcher = getlauncher('srun')()

    @performance_function('ns/day', perf_key='ns_per_day')
    def extract_ns_per_day(self):
        return sn.extractsingle(r'Performance:\s+(\S+)\s+(\S+)', self.stdout, 1, float)
