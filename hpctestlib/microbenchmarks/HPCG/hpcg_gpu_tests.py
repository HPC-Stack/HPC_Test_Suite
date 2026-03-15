import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import subprocess

# ----------------------------------------------------------------------
# Fixture 1: Fetch NVIDIA HPCG source
# ----------------------------------------------------------------------
class FetchNvidiaHPCG(rfm.RunOnlyRegressionTest):
    descr = 'Fetch NVIDIA HPCG source from GitHub'
    valid_systems = ['paramrudra.snbose:login']
    valid_prog_environs = ['gnu']
    local = True
    
    executable = 'git'
    executable_opts = ['clone', 'https://github.com/NVIDIA/nvidia-hpcg.git']
    
    @sanity_function
    def validate_download(self):
        return sn.assert_eq(self.job.exitcode, 0)


# ----------------------------------------------------------------------
# Fixture 2: Build NVIDIA HPCG
# ----------------------------------------------------------------------
class BuildNvidiaHPCG(rfm.RunOnlyRegressionTest):
    descr = 'Build NVIDIA HPCG for GPU'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['spack-only']
    
    # Depend on the source fetch
    hpcg_source = fixture(FetchNvidiaHPCG, scope='session')
    
    @run_before('run')
    def setup_build(self):
        # Discover paths on login node where spack is available
        try:
            nvhpc_path = subprocess.check_output(
                ['spack', 'location', '-i', 'nvhpc@24.5/tdc6iex'],
                text=True
            ).strip()
            
            cuda_home = f'{nvhpc_path}/Linux_x86_64/24.5/cuda/12.4'
            hpcx_root = f'{nvhpc_path}/Linux_x86_64/24.5/comm_libs/12.4/hpcx/hpcx-2.19'
            mpi_path = f'{hpcx_root}/ompi'
            mathlibs_path = f'{nvhpc_path}/Linux_x86_64/24.5/math_libs/12.4/targets/x86_64-linux'
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to locate NVHPC: {e}')
        
        # Prepare build script
        build_cmds = [
            f'cp -r {self.hpcg_source.stagedir}/nvidia-hpcg/* .',
            'mkdir -p build',
            'cd build',
            '../configure CUDA_X86',
            f'make -j 8 -f Makefile USE_CUDA=1 USE_GRACE=0 USE_NCCL=0 MPdir={mpi_path} MPlib={mpi_path}/lib Mathdir={mathlibs_path} CUDA_HOME={cuda_home} NVPL_PATH={mathlibs_path}',
            'make install'
        ]
        
        self.executable = 'bash'
        self.executable_opts = ['-c', ' && '.join(build_cmds)]
    
    @sanity_function
    def validate_build(self):
        # Check if binary was created in bin directory (after make install)
        return sn.assert_true(
            os.path.exists(os.path.join(self.stagedir, 'bin', 'xhpcg')),
            msg='xhpcg binary not found in bin/'
        )


# ----------------------------------------------------------------------
# Main Test: Run NVIDIA HPCG on GPU
# ----------------------------------------------------------------------
@rfm.simple_test
class HPCGGpuRunTest(rfm.RunOnlyRegressionTest):
    descr = 'Run NVIDIA HPCG benchmark on GPU'
    
    # Depend on the build
    hpcg_build = fixture(BuildNvidiaHPCG, scope='environment')
    
    # Test parameters
    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])
    num_nodes = parameter([1])
    
    @run_before('run')
    def setup_run(self):
        # Set executable from build fixture
        self.executable = os.path.join(self.hpcg_build.stagedir, 'bin', 'xhpcg')
        
        # Discover paths dynamically (same as build step)
        try:
            nvhpc_path = subprocess.check_output(
                ['spack', 'location', '-i', 'nvhpc@24.5/tdc6iex'],
                text=True
            ).strip()
            
            cuda_home = f'{nvhpc_path}/Linux_x86_64/24.5/cuda/12.4'
            hpcx_root = f'{nvhpc_path}/Linux_x86_64/24.5/comm_libs/12.4/hpcx/hpcx-2.19'
            mpi_path = f'{hpcx_root}/ompi'
            mathlibs_path = f'{nvhpc_path}/Linux_x86_64/24.5/math_libs/12.4/targets/x86_64-linux'
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to locate NVHPC: {e}')
        
        # Create hpcg.dat input file
        hpcg_dat = f"""HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
{self.nx} {self.ny} {self.nz}
{self.running_time}
"""
        
        # Setup environment and create input file
        # We need to ensure LD_LIBRARY_PATH includes CUDA and MPI libs
        self.prerun_cmds = [
            f'export CUDA_HOME={cuda_home}',
            f'export PATH={cuda_home}/bin:{mpi_path}/bin:$PATH',
            f'export LD_LIBRARY_PATH={cuda_home}/lib64:{mpi_path}/lib:{mathlibs_path}/lib:$LD_LIBRARY_PATH',
            f'echo "{hpcg_dat}" > hpcg.dat',
        ]
        
        # Cat result file to stdout for easier parsing
        self.postrun_cmds = [
            'cat HPCG-Benchmark_*.txt || echo "No result file found"'
        ]
        
        # Configure MPI tasks (2 GPUs per node)
        self.num_tasks = self.num_nodes * 2
        self.num_tasks_per_node = 2
        
        # Use mpirun launcher (HPC-X MPI)
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--bind-to', 'none',
            '-x', 'CUDA_VISIBLE_DEVICES',
            '-x', 'LD_LIBRARY_PATH'
        ]
        
        # Set time limit
        self.time_limit = '15m'
    
    @sanity_function
    def validate_run(self):
        # Check for valid result in stdout (from cat command)
        return sn.assert_found(r'HPCG result is VALID', self.stdout)
    
    @performance_function('GFlops')
    def extract_performance(self):
        # Extract performance from stdout
        return sn.extractsingle(
            r'Final Summary::HPCG result is VALID with a GFLOP/s rating of=(?P<gflops>[\d.]+)',
            self.stdout, 'gflops', float
        )
    
    @run_before('performance')
    def set_reference(self):
        # Set reference values (update based on actual results)
        self.reference = {
            'paramrudra.snbose:gpu': {
                'GFlops': (0.01, None, None, 'GFlops')
            }
        }
