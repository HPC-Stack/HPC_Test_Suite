import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os

# ----------------------------------------------------------------------
# 1. Fixture to pull the NGC container image (singularity)
# ----------------------------------------------------------------------
class PullHPCGContainer(rfm.RunOnlyRegressionTest):
    descr = 'Pull NVIDIA HPCG container from NGC (v25.09)'
    valid_systems = ['paramrudra.snbose:login']
    valid_prog_environs = ['gnu']
    # No modules needed – we rely on singularity being available on the system
    local = True
    # Use singularity to pull the image; the image will be stored in the stage dir
    executable = 'singularity'
    # Pull the container from NGC (docker registry) and name it hpcg.sif
    # The version 25.09 corresponds to tag "25.09" in the NGC repo
    executable_opts = [
        'pull', '--name', 'hpcg.sif',
        'docker://nvcr.io/nvidia/hpc-benchmarks:25.09'
    ]

    @sanity_function
    def validate_pull(self):
        # The pull should exit with 0 and the file should exist
        return sn.all([
            sn.assert_eq(self.job.exitcode, 0),
            sn.assert_found(r'hpcg.sif', self.stdout)
        ])

# ----------------------------------------------------------------------
# 2. Run the HPCG benchmark inside the container
# ----------------------------------------------------------------------
@rfm.simple_test
class HPCGGpuContainerTest(rfm.RunOnlyRegressionTest):
    descr = 'Run NVIDIA HPCG GPU benchmark using NGC container (v25.09)'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['spack-only']

    # Pull the container once per session
    container = fixture(PullHPCGContainer, scope='session')

    # Problem size – keep the same as the native tests for comparability
    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])

    @run_before('run')
    def setup_run(self):
        # The container image lives in the stage directory of the fixture
        sif_path = os.path.join(self.container.stagedir, 'hpcg.sif')
        # Inside the container the HPCG binary is typically located at /opt/hpcg/xhpcg
        self.executable = 'singularity'
        self.executable_opts = [
            'exec', sif_path,
            '/opt/hpcg/xhpcg'
        ]
        # Create the required hpcg.dat input file (same format as the native test)
        hpcg_dat = f"""HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
{self.nx} {self.ny} {self.nz}
{self.running_time}
"""
        self.prerun_cmds = [
            f'echo -e "{hpcg_dat}" > hpcg.dat'
        ]
        # Two GPUs per node → two MPI tasks (one per GPU)
        self.num_tasks = 2
        self.num_tasks_per_node = 2
        # Use the standard mpirun launcher – the container already contains the MPI library
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = []

    @sanity_function
    def validate_run(self):
        # The container writes a file named HPCG-Benchmark_*.txt in the working directory
        result_files = sn.glob('HPCG-Benchmark_*.txt')
        return sn.all([
            sn.assert_true(sn.count(result_files) > 0,
                           msg='HPCG result file not found'),
            sn.assert_found(r'HPCG result is VALID', sn.last(result_files))
        ])

    @performance_function('GFlops')
    def extract_performance(self):
        result_files = sn.glob('HPCG-Benchmark_*.txt')
        return sn.extractsingle(
            r'Final Summary::HPCG result is VALID with a GFLOP/s rating of=(?P<gflops>[\d.]+)',
            sn.last(result_files), 'gflops', float
        )
