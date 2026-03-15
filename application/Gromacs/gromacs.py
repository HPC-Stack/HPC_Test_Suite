import reframe as rfm
import reframe.utility.sanity as sn
import sys
sys.path.append('/home/cdacapp01/HPC_Test_Suite/application/module')
from module import parse_time_cmd
from reframe.core.backends import getlauncher



@rfm.simple_test
class gromacTest_cpu(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs gromacs'
    valid_systems = ['paramrudra.snbose:cpu']
    valid_prog_environs = ['gnu']
    modules = ['gromacs/m6krxp7', 'openmpi/qmzsyj6']
    num_tasks_per_node = 48
    num_process = parameter([48,96,192,384]) #
    sourcesdir = 'src'
    exclusive_access = True

    prerun_cmds = [
        'tar -xvf water_GMX50_bare.tar.gz',
        'cd water-cut1.0_GMX50_bare/3072',
        'gmx_mpi grompp -f pme.mdp -c conf.gro -p topol.top -o water_pme.tpr',
        'time \\'
        ] # want to run mpi task under time

    executable = 'gmx_mpi '
    executable_opts = ["mdrun -nsteps 5000 -s water_pme.tpr"]
    
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

@rfm.simple_test
class gromacTest_gpu(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs gromacs'
    valid_systems = ['paramrudra.snbose:cpu']
    valid_prog_environs = ['gnu']
    num_tasks_per_node = 40
    num_process = parameter([48,96,192])
    sourcesdir = 'src'
    exclusive_access = True
    
    prerun_cmds = [
        'tar -xvf water_GMX50_bare.tar.gz',
        'cd water-cut1.0_GMX50_bare/3072',
        'gmx_mpi grompp -f pme.mdp -c conf.gro -p topol.top -o water_pme.tpr',
        'time \\'
        ] # want to run mpi task under time

    executable = 'gmx_mpi'
    executable_opts = ["mdrun -nsteps 50000 -ntomp 2 -nb gpu -s water_pme.tpr"]
    
    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process


    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()


    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('ns/day', perf_key='ns_per_day')
    def extract_runtime_real(self):
        return sn.extractsingle(r'Performance:\s+(\S+)\s+(\S+)', self.stderr, 1, float)
