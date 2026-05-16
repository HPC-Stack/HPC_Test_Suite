import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import os
import subprocess


@rfm.simple_test
class HPCGRunTest(rfm.RunOnlyRegressionTest):
    descr = 'Run HPCG benchmark on different partitions'
    valid_systems = ['paramrudra.snbose:cpu', 'paramrudra.snbose:hm', 'paramrudra.snbose:gpu']
    valid_prog_environs = ['gnu']

    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])
    num_nodes = parameter([1, 2])

    @run_before('run')
    def setup_run(self):
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
        self.job.launcher = getlauncher('srun')()
        self.job.launcher.options = ['--mpi=pmix']

    @sanity_function
    def validate_run(self):
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


class BuildNvidiaHPCG(rfm.RunOnlyRegressionTest):
    descr = 'Build NVIDIA HPCG for GPU'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['spack-only']

    hpcg_source = fixture(FetchNvidiaHPCG, scope='session')

    @run_before('run')
    def setup_build(self):
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
        return sn.assert_true(
            os.path.exists(os.path.join(self.stagedir, 'bin', 'xhpcg')),
            msg='xhpcg binary not found in bin/'
        )


@rfm.simple_test
class HPCGGpuRunTest(rfm.RunOnlyRegressionTest):
    descr = 'Run NVIDIA HPCG benchmark on GPU'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['gnu']

    hpcg_build = fixture(BuildNvidiaHPCG, scope='environment')

    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])
    num_nodes = parameter([1])

    @run_before('run')
    def setup_run(self):
        self.executable = os.path.join(self.hpcg_build.stagedir, 'bin', 'xhpcg')
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

        hpcg_dat = f"""HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
{self.nx} {self.ny} {self.nz}
{self.running_time}
"""
        self.prerun_cmds = [
            f'export CUDA_HOME={cuda_home}',
            f'export PATH={cuda_home}/bin:{mpi_path}/bin:$PATH',
            f'export LD_LIBRARY_PATH={cuda_home}/lib64:{mpi_path}/lib:{mathlibs_path}/lib:$LD_LIBRARY_PATH',
            f'echo "{hpcg_dat}" > hpcg.dat',
        ]
        self.postrun_cmds = [
            'cat HPCG-Benchmark_*.txt || echo "No result file found"'
        ]
        self.num_tasks = self.num_nodes * 2
        self.num_tasks_per_node = 2
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--bind-to', 'none',
            '-x', 'CUDA_VISIBLE_DEVICES',
            '-x', 'LD_LIBRARY_PATH'
        ]
        self.time_limit = '15m'

    @sanity_function
    def validate_run(self):
        return sn.assert_found(r'HPCG result is VALID', self.stdout)

    @performance_function('GFlops')
    def extract_performance(self):
        return sn.extractsingle(
            r'Final Summary::HPCG result is VALID with a GFLOP/s rating of=(?P<gflops>[\d.]+)',
            self.stdout, 'gflops', float
        )

    @run_before('performance')
    def set_reference(self):
        self.reference = {
            'paramrudra.snbose:gpu': {
                'GFlops': (0.01, None, None, 'GFlops')
            }
        }


class PullHPCGContainer(rfm.RunOnlyRegressionTest):
    descr = 'Pull NVIDIA HPCG container from NGC (v25.09)'
    valid_systems = ['paramrudra.snbose:login']
    valid_prog_environs = ['gnu']
    local = True
    executable = 'singularity'
    executable_opts = [
        'pull', '--name', 'hpcg.sif',
        'docker://nvcr.io/nvidia/hpc-benchmarks:25.09'
    ]

    @sanity_function
    def validate_pull(self):
        return sn.all([
            sn.assert_eq(self.job.exitcode, 0),
            sn.assert_found(r'hpcg.sif', self.stdout)
        ])


@rfm.simple_test
class HPCGGpuContainerTest(rfm.RunOnlyRegressionTest):
    descr = 'Run NVIDIA HPCG GPU benchmark using NGC container (v25.09)'
    valid_systems = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['spack-only']

    container = fixture(PullHPCGContainer, scope='session')

    nx = parameter([104])
    ny = parameter([104])
    nz = parameter([104])
    running_time = parameter([60])

    @run_before('run')
    def setup_run(self):
        sif_path = os.path.join(self.container.stagedir, 'hpcg.sif')
        self.executable = 'singularity'
        self.executable_opts = [
            'exec', sif_path,
            '/opt/hpcg/xhpcg'
        ]
        hpcg_dat = f"""HPCG benchmark input file
Sandia National Laboratories; University of Tennessee, Knoxville
{self.nx} {self.ny} {self.nz}
{self.running_time}
"""
        self.prerun_cmds = [
            f'echo -e "{hpcg_dat}" > hpcg.dat'
        ]
        self.num_tasks = 2
        self.num_tasks_per_node = 2
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = []

    @sanity_function
    def validate_run(self):
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
