import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture


@rfm.simple_test
class castroTest(rfm.RunOnlyRegressionTest):
    descr = 'Castro/AMReX 2D CPU benchmark — Sedov (OMP)'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'amrex', 'castro', 'cpu'}
    num_threads = parameter([1, 2, 4, 8, 16, 30, 32, 40, 46])
    num_tasks_per_node = 1
    num_cpus_per_task = 48
    sourcesdir = 'src'
    exclusive_access = True

    executable = 'Castro2d.gnu.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def set_cpus_per_task(self):
        self.num_cpus_per_task = self.num_threads
        self.env_vars = {
            'OMP_NUM_THREADS': str(self.num_threads),
            'OMP_PLACES': 'cores',
            'AMREX_HOME': os.environ.get('AMREX_HOME', ''),
            'CASTRO_HOME': os.environ.get('CASTRO_HOME', ''),
            'MICROPHYSICS_HOME': os.environ.get('MICROPHYSICS_HOME', ''),
        }
        amrex_path = os.environ.get('CASTRO_HOME', '')
        if amrex_path:
            self.prerun_cmds = [
                f'export PATH={amrex_path}/Exec/hydro_tests/Sedov:$PATH',
                'time \\',
            ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)


@rfm.simple_test
class castro_mpi_Test(rfm.RunOnlyRegressionTest):
    descr = 'Castro/AMReX 2D CPU benchmark — Sedov (MPI)'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'amrex', 'castro', 'cpu'}
    num_process = parameter([46])
    num_tasks_per_node = 48
    sourcesdir = 'src'
    exclusive_access = True

    executable = 'Castro2d.gnu.MPI.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def setup_env(self):
        self.num_tasks = self.num_process
        self.env_vars = {
            'OMP_NUM_THREADS': '1',
            'AMREX_HOME': os.environ.get('AMREX_HOME', ''),
            'CASTRO_HOME': os.environ.get('CASTRO_HOME', ''),
            'MICROPHYSICS_HOME': os.environ.get('MICROPHYSICS_HOME', ''),
        }
        amrex_path = os.environ.get('CASTRO_HOME', '')
        if amrex_path:
            self.prerun_cmds = [
                f'export PATH={amrex_path}/Exec/hydro_tests/Sedov:$PATH',
                'time \\',
            ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [f'-npernode {self.num_process}']

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)


@rfm.simple_test
class castro_intelTest(rfm.RunOnlyRegressionTest):
    descr = 'Castro/AMReX 2D CPU benchmark — Intel (OMP)'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'amrex', 'castro', 'cpu'}
    num_threads = parameter([1, 2, 4, 8, 16, 30, 32, 40, 46])
    num_tasks_per_node = 1
    num_cpus_per_task = 48
    sourcesdir = 'src'
    exclusive_access = True

    executable = 'Castro2d.intel-llvm.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def set_cpus_per_task(self):
        self.num_cpus_per_task = self.num_threads
        self.env_vars = {
            'OMP_NUM_THREADS': str(self.num_threads),
            'OMP_PLACES': 'cores',
            'AMREX_HOME': os.environ.get('AMREX_HOME_INTEL', ''),
            'CASTRO_HOME': os.environ.get('CASTRO_HOME_INTEL', ''),
            'MICROPHYSICS_HOME': os.environ.get('MICROPHYSICS_HOME_INTEL', ''),
        }
        amrex_path = os.environ.get('CASTRO_HOME_INTEL', '')
        if amrex_path:
            self.prerun_cmds = [
                f'export PATH={amrex_path}/Exec/hydro_tests/Sedov:$PATH',
                'time \\',
            ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)


@rfm.simple_test
class castro_intel_mpiTest(rfm.RunOnlyRegressionTest):
    descr = 'Castro/AMReX 2D CPU benchmark — Intel (MPI)'
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'amrex', 'castro', 'cpu'}
    num_process = parameter([46])
    num_tasks_per_node = 48
    sourcesdir = 'src'
    exclusive_access = True

    executable = 'Castro2d.intel-llvm.MPI.OMP.ex'
    executable_opts = ["inputs.2d.sph_in_cylcoords"]

    @run_before('run')
    def setup_env(self):
        self.num_tasks = self.num_process
        self.env_vars = {
            'OMP_NUM_THREADS': '1',
            'AMREX_HOME': os.environ.get('AMREX_HOME_INTEL', ''),
            'CASTRO_HOME': os.environ.get('CASTRO_HOME_INTEL', ''),
            'MICROPHYSICS_HOME': os.environ.get('MICROPHYSICS_HOME_INTEL', ''),
        }
        amrex_path = os.environ.get('CASTRO_HOME_INTEL', '')
        if amrex_path:
            self.prerun_cmds = [
                f'export PATH={amrex_path}/Exec/hydro_tests/Sedov:$PATH',
                'time \\',
            ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_runtime(self):
        return sn.extractsingle(r'Run time\s*=\s*(\S+)', self.stdout, 1, float)
