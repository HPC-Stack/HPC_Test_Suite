import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher

@rfm.simple_test
class castroTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs amrex 2D Heat solver'
    valid_systems = ['paramrudra.iuac:cpu']
    valid_prog_environs = ['gnu']
    #num_process = parameter([48,96,192,384,768])
    num_threads = parameter([1, 2, 4, 8, 16, 30, 32, 40, 46]) #
    num_tasks_per_node = 1
    num_cpus_per_task = 48
    modules = ['gcc/3wdooxp','openmpi/3nm34j7']
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'AMREX_HOME': '/home/samirs/AMReX/Castro/external/amrex',
        'CASTRO_HOME': '/home/samirs/AMReX/Castro',
        'MICROPHYSICS_HOME': '/home/samirs/AMReX/Castro/external/Microphysics'
    }
    prerun_cmds = [
           #'export PATH=/home/samirs/AMReX/amrex-tutorials/ExampleCodes/Amr/Wave_AmrLevel:$PATH',
           'export PATH=/home/samirs/AMReX/Castro/Exec/hydro_tests/Sedov:$PATH',
           'time \\'
        ]

    executable = 'Castro2d.gnu.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    # @run_before('run')
    # def set_num_task(self):
    #     self.num_tasks = self.num_process

    @run_before('run')
    def set_cpus_per_task(self):
        self.num_cpus_per_task = self.num_threads
        self.env_vars = {
            'OMP_NUM_THREADS': str(self.num_threads),
            'OMP_PLACES': 'cores'
        }

    
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)

@rfm.simple_test
class castro_mpi_Test(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs amrex 2D Heat solver'
    valid_systems = ['paramrudra.iuac:cpu']
    valid_prog_environs = ['gnu']
    num_process = parameter([46]) #,96,192,384,768
    num_tasks_per_node = 48
    modules = ['gcc/6brco2m','openmpi/3nm34j7']
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'AMREX_HOME': '/home/samirs/AMReX/Castro/external/amrex',
        'CASTRO_HOME': '/home/samirs/AMReX/Castro',
        'MICROPHYSICS_HOME': '/home/samirs/AMReX/Castro/external/Microphysics',
        'OMP_NUM_THREADS': '1'
    }
    prerun_cmds = [
           #'export PATH=/home/samirs/AMReX/amrex-tutorials/ExampleCodes/Amr/Wave_AmrLevel:$PATH',
           'export PATH=/home/samirs/AMReX/Castro/Exec/hydro_tests/Sedov:$PATH',
           'time \\'
        ]

    executable = 'Castro2d.gnu.MPI.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [f'-npernode {self.num_process}']


    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)

@rfm.simple_test
class castro_intelTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs amrex 2D Heat solver'
    valid_systems = ['paramrudra.iuac:cpu']
    valid_prog_environs = ['gnu']
    #num_process = parameter([48,96,192,384,768])
    num_threads = parameter([1, 2, 4, 8, 16, 30, 32, 40, 46]) #
    num_tasks_per_node = 1
    num_cpus_per_task = 48
    modules = ['intel-oneapi-mkl@2024.2.0','intel-oneapi-mpi@2021.12.1/cebrslr', 'intel-oneapi-compilers@2023.2.0']
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'AMREX_HOME': '/home/samirs/AMReX/Castro-intel/external/amrex',
        'CASTRO_HOME': '/home/samirs/AMReX/Castro-intel',
        'MICROPHYSICS_HOME': '/home/samirs/AMReX/Castro-intel/external/Microphysics'
    }
    prerun_cmds = [
           #'export PATH=/home/samirs/AMReX/amrex-tutorials/ExampleCodes/Amr/Wave_AmrLevel:$PATH',
           'export PATH=/home/samirs/AMReX/Castro-intel/Exec/hydro_tests/Sedov:$PATH',
           'time \\'
        ]

    executable = 'Castro2d.intel-llvm.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    # @run_before('run')
    # def set_num_task(self):
    #     self.num_tasks = self.num_process

    @run_before('run')
    def set_cpus_per_task(self):
        self.num_cpus_per_task = self.num_threads
        self.env_vars = {
            'OMP_NUM_THREADS': str(self.num_threads),
            'OMP_PLACES': 'cores'
        }

    
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)

@rfm.simple_test
class castro_intel_mpiTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs amrex 2D Heat solver'
    valid_systems = ['paramrudra.iuac:hm']
    valid_prog_environs = ['gnu']
    num_process = parameter([46]) #,96,192,384,768
    #num_threads = parameter([1, 2, 4, 8, 16, 30, 32, 40, 46]) #
    num_tasks_per_node = 48
    modules = ['intel-oneapi-mkl@2024.2.0/te7ayi7','intel-oneapi-mpi@2021.12.1/cebrslr', 'intel-oneapi-compilers@2023.2.0']
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'AMREX_HOME': '/home/samirs/AMReX/Castro-intel/external/amrex',
        'CASTRO_HOME': '/home/samirs/AMReX/Castro-intel',
        'MICROPHYSICS_HOME': '/home/samirs/AMReX/Castro-intel/external/Microphysics',
        'OMP_NUM_THREADS': '1'
    }
    prerun_cmds = [
           #'export PATH=/home/samirs/AMReX/amrex-tutorials/ExampleCodes/Amr/Wave_AmrLevel:$PATH',
           'export PATH=/home/samirs/AMReX/Castro-intel/Exec/hydro_tests/Sedov:$PATH',
           'time \\'
        ]

    executable = 'Castro2d.intel-llvm.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.num_process
        #self.job.launcher.options = [f'-ppn {self.num_process}']

    # @run_before('run')
    # def set_cpus_per_task(self):
    #     self.num_cpus_per_task = self.num_threads
    #     self.env_vars = {
    #         'OMP_NUM_THREADS': str(self.num_threads),
    #         'OMP_PLACES': 'cores'
    #     }

    
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)