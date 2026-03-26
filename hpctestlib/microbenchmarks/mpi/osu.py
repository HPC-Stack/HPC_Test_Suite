# hpctestlib/microbenchmarks/mpi/osu.py
#
# OSU Micro-Benchmarks — MPI point-to-point and collective tests.
# Supports both CPU (host memory) and GPU (CUDA device memory) buffers.
#
# Pre-built binaries from NVHPC 24.5 / HPC-X 2.19 spack installation.
# No build step needed — binaries already exist on shared filesystem.
#
# Verified paths on paramrudra.snbose:
#   NVHPC : .../nvhpc-24.5-tdc6iex.../Linux_x86_64/24.5/
#   HPC-X : comm_libs/12.4/hpcx/hpcx-2.19/
#   mpirun: ...hpcx-2.19/ompi/bin/mpirun
#   init  : ...hpcx-2.19/hpcx-init.sh
#   CPU   : ...hpcx-2.19/ompi/tests/osu-micro-benchmarks/
#   GPU   : ...hpcx-2.19/ompi/tests/osu-micro-benchmarks-cuda/
#
# IMPORTANT — MPI consistency:
#   OSU binaries are linked against HPC-X OpenMPI.
#   Must use HPC-X mpirun — NOT the gnu env openmpi@4.1.6.
#   Mixing MPI libraries causes "2 total processes failed to start".
#
# GPU tests use CUDA device buffers (-d cuda D D).
# Data stays in GPU memory — measures inter-GPU bandwidth via IB/NVLink.

import os
import re
import shutil

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher


# ---------------------------------------------------------------------------
# Verified paths — paramrudra.snbose cascadelake gcc-13.2.0 nvhpc-24.5
# ---------------------------------------------------------------------------

_NVHPC_BASE = (
    '/home/apps/spack/opt/spack/linux-almalinux8-cascadelake'
    '/gcc-13.2.0/nvhpc-24.5-tdc6iexttubxc42znfv3hxpeoq2wiab7'
    '/Linux_x86_64/24.5'
)

_HPCX_ROOT = f'{_NVHPC_BASE}/comm_libs/12.4/hpcx/hpcx-2.19'
_OMPI_ROOT  = f'{_HPCX_ROOT}/ompi'
_OSU_BASE   = f'{_OMPI_ROOT}/tests'

# HPC-X mpirun — must match the OSU binary link-time MPI
MPIRUN_BIN    = f'{_OMPI_ROOT}/bin/mpirun'

# hpcx-init.sh — sources HPC-X environment variables
HPCX_INIT_SH  = f'{_HPCX_ROOT}/hpcx-init.sh'

# OSU binary directories
OSU_CPU_DIR   = f'{_OSU_BASE}/osu-micro-benchmarks'
OSU_CUDA_DIR  = f'{_OSU_BASE}/osu-micro-benchmarks-cuda'

# Fallback: use older HPC-X 2.14 if 2.19 dirs are missing
_HPCX_FALLBACK = f'{_NVHPC_BASE}/comm_libs/11.8/hpcx/hpcx-2.14'
if not os.path.isdir(OSU_CPU_DIR):
    OSU_CPU_DIR  = f'{_HPCX_FALLBACK}/ompi/tests/osu-micro-benchmarks-5.8'
    OSU_CUDA_DIR = f'{_HPCX_FALLBACK}/ompi/tests/osu-micro-benchmarks-5.8-cuda'
    MPIRUN_BIN   = f'{_HPCX_FALLBACK}/ompi/bin/mpirun'
    HPCX_INIT_SH = f'{_HPCX_FALLBACK}/hpcx-init.sh'


# ---------------------------------------------------------------------------
# Performance references
# ---------------------------------------------------------------------------

# Latency (us) — upper bound only (lower is better)
# Bandwidth (MB/s) — lower bound only (higher is better)
# Values based on expected InfiniBand EDR/HDR performance

OSU_REFERENCE = {
    # intra-cluster CPU nodes
    'paramrudra.snbose:cpu': {
        'latency':   (None, None, 5.0,    'us'),
        'bandwidth': (8000, -0.1, None,   'MB/s'),
    },
    # high-memory nodes
    'paramrudra.snbose:hm': {
        'latency':   (None, None, 8.0,    'us'),
        'bandwidth': (8000, -0.1, None,   'MB/s'),
    },
    # GPU nodes — CPU buffers
    'paramrudra.snbose:gpu': {
        'latency':   (None, None, 5.0,    'us'),
        'bandwidth': (8000, -0.1, None,   'MB/s'),
    },
}

# GPU-to-GPU (CUDA buffers) — slightly higher latency due to GPU buffer setup
OSU_GPU_REFERENCE = {
    'paramrudra.snbose:gpu': {
        'latency':   (None, None, 15.0,   'us'),
        'bandwidth': (4000, -0.1, None,   'MB/s'),
    },
}


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class osu_base(rfm.RunOnlyRegressionTest):
    '''OSU benchmark base class — handles MPI setup and output parsing.

    Subclasses set osu_bin_dir, device_buffers, valid_systems.

    Key design:
      - Uses HPC-X mpirun (not system openmpi) to match OSU link-time MPI
      - hpcx-init.sh loaded in prerun_cmds to set LD_LIBRARY_PATH
      - Sanity checks for message size line, not "Pass" (OSU never prints it)
      - Performance regex extracts last measurement at target message size
    '''

    #: Warmup iterations passed via -x
    num_warmup_iters = variable(int, value=10)

    #: Measurement iterations passed via -i
    num_iters = variable(int, value=1000)

    #: Message size for perf extraction and sanity check
    message_size = variable(int)

    #: OSU binary directory — set by subclass
    osu_bin_dir = variable(str, value=OSU_CPU_DIR)

    #: Device buffers: 'cpu' or 'cuda'
    device_buffers = variable(str, value='cpu')

    #: Benchmark to run — (relative_path, metric) tuple
    #: relative_path is relative to osu_bin_dir
    benchmark_info = parameter([
        ('mpi/pt2pt/osu_latency',        'latency'),
        ('mpi/pt2pt/osu_bw',             'bandwidth'),
        ('mpi/collective/osu_allreduce', 'latency'),
        ('mpi/collective/osu_alltoall',  'latency'),
    ], fmt=lambda x: x[0].split('/')[-1], loggable=True)

    num_tasks_per_node = 1

    @run_before('run')
    def configure_benchmark(self):
        bench_path, bench_metric = self.benchmark_info
        bench_name = bench_path.split('/')[-1]

        # Message size and unit per metric type
        if bench_metric == 'latency':
            self.message_size = 2097152
            unit = 'us'
        else:
            self.message_size = 4194304
            unit = 'MB/s'

        # Full path to binary
        self.executable = os.path.join(self.osu_bin_dir, bench_path)

        self.executable_opts = [
            '-m', f'{self.message_size}',
            '-x', str(self.num_warmup_iters),
            '-i', str(self.num_iters),
        ]

        # GPU device buffer flags
        if self.device_buffers == 'cuda':
            if 'pt2pt' in bench_path:
                # D D = both sender and receiver use device buffers
                self.executable_opts += ['-d', 'cuda', 'D', 'D']
            else:
                self.executable_opts += ['-d', 'cuda']

        # Task count — pt2pt needs exactly 2, collectives 4+
        if 'pt2pt' in bench_path:
            self.num_tasks = 2
        else:
            if not getattr(self, 'num_tasks', None):
                self.num_tasks = 4

        # Performance variable
        self.perf_variables = {
            bench_metric: sn.make_performance_function(
                self._extract_metric, unit
            )
        }

        # Reference
        ref_table = (
            OSU_GPU_REFERENCE if self.device_buffers == 'cuda'
            else OSU_REFERENCE
        )
        system_key = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        part_ref = ref_table.get(system_key, {}).get(
            bench_metric, (None, None, None, unit)
        )
        self.reference = {system_key: {bench_metric: part_ref}}

    @run_before('run')
    def setup_hpcx_env(self):
        '''Load HPC-X environment so OSU binaries find their MPI libraries.

        OSU binaries are linked against HPC-X OpenMPI. The HPC-X mpirun
        and shared libraries must be in PATH/LD_LIBRARY_PATH before launch.
        hpcx-init.sh + hpcx_load handles this cleanly.

        This runs in the Slurm job on the compute node — uses the absolute
        path to hpcx-init.sh which is on shared Lustre.
        '''
        ompi_lib = os.path.join(_OMPI_ROOT, 'lib')
        ompi_bin = os.path.join(_OMPI_ROOT, 'bin')

        if os.path.isfile(HPCX_INIT_SH):
            self.prerun_cmds = [
                f'source {HPCX_INIT_SH}',
                'hpcx_load',
                f'export PATH={ompi_bin}:$PATH',
                f'export LD_LIBRARY_PATH={ompi_lib}:$LD_LIBRARY_PATH',
                f'echo "mpirun : $(which mpirun)"',
                f'echo "HPC-X  : {_HPCX_ROOT}"',
            ]
        else:
            # Fallback — add ompi dirs directly
            self.prerun_cmds = [
                f'export PATH={ompi_bin}:$PATH',
                f'export LD_LIBRARY_PATH={ompi_lib}:$LD_LIBRARY_PATH',
                f'echo "mpirun : $(which mpirun)"',
                f'echo "WARNING: hpcx-init.sh not found, using direct PATH"',
            ]

    @run_before('run')
    def set_mpirun_launcher(self):
        '''Replace srun with HPC-X mpirun.

        OSU benchmarks must be launched with mpirun from the same
        MPI installation they were compiled against.
        Using srun or a different mpirun causes library mismatch errors.
        '''
        self.job.launcher = getlauncher('mpirun')()
        # Point to HPC-X mpirun explicitly
        if os.path.isfile(MPIRUN_BIN):
            self.job.launcher.executable = MPIRUN_BIN

    @deferrable
    def _extract_metric(self):
        return sn.extractsingle(
            rf'^{self.message_size}\s+(\S+)',
            self.stdout, 1, float
        )

    @sanity_function
    def validate(self):
        '''Check output contains a line starting with the target message size.

        OSU output format:
          # OSU MPI Bandwidth Test v5.8
          # Size      Bandwidth (MB/s)
          1           1234.56
          2           2345.67
          ...
          4194304     9876.54   <- we look for this line

        Note: OSU does NOT print "Pass" — original sanity check was wrong.
        '''
        return sn.assert_found(
            rf'^{self.message_size}\s+\S+',
            self.stdout,
            msg=(
                f'Message size {self.message_size} not found in output.\n'
                f'Binary: {self.executable}\n'
                f'MPI may have failed — check that HPC-X is loaded correctly.'
            )
        )


# ---------------------------------------------------------------------------
# CPU test — standard host memory buffers
# ---------------------------------------------------------------------------

@rfm.simple_test
class osu_cpu_test(osu_base):
    '''OSU benchmarks with standard CPU (host) memory buffers.

    Measures MPI bandwidth and latency between CPU nodes.
    Uses HPC-X 2.19 OpenMPI and the pre-built osu-micro-benchmarks
    binaries bundled with NVHPC 24.5.

    Benchmarks:
      osu_latency   — point-to-point latency (us)     2 ranks, 1 per node
      osu_bw        — point-to-point bandwidth (MB/s)  2 ranks, 1 per node
      osu_allreduce — collective latency (us)          4 ranks, 1 per node
      osu_alltoall  — collective latency (us)          4 ranks, 1 per node
    '''

    valid_systems = [
        'paramrudra.snbose:cpu',
        'paramrudra.snbose:hm',
        'paramrudra.snbose:gpu',
    ]
    valid_prog_environs = ['builtin', 'gnu']
    tags = {'mpi', 'perf', 'microbenchmark', 'cpu', 'network'}
    time_limit = '30m'

    osu_bin_dir    = variable(str, value=OSU_CPU_DIR)
    device_buffers = variable(str, value='cpu')

    @run_before('run')
    def set_cpu_tasks(self):
        bench_path = self.benchmark_info[0]
        if 'pt2pt' in bench_path:
            self.num_tasks          = 2
            self.num_tasks_per_node = 1
            self.num_cpus_per_task  = 1
        else:
            self.num_tasks          = 4
            self.num_tasks_per_node = 1
            self.num_cpus_per_task  = 1


# ---------------------------------------------------------------------------
# GPU test — CUDA device memory buffers
# ---------------------------------------------------------------------------

@rfm.simple_test
class osu_gpu_test(osu_base):
    '''OSU benchmarks with CUDA device (GPU) memory buffers.

    Measures GPU-to-GPU MPI bandwidth and latency.
    Data stays in GPU HBM — tests inter-GPU transfer via InfiniBand
    or NVLink without bouncing through CPU memory.

    Requires CUDA-aware MPI (HPC-X with CUDA support — verified in
    the osu-micro-benchmarks-cuda build).

    UCX settings ensure GPU-direct RDMA is used when available:
      UCX_TLS=rc,cuda_copy,cuda_ipc,gdr_copy

    Benchmarks:
      osu_latency   — GPU-to-GPU latency (us)          2 ranks, 1 per node
      osu_bw        — GPU-to-GPU bandwidth (MB/s)       2 ranks, 1 per node
      osu_allreduce — GPU collective latency (us)       4 ranks, 1 per node
      osu_alltoall  — GPU collective latency (us)       4 ranks, 1 per node
    '''

    valid_systems       = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['builtin', 'gnu']
    tags = {'mpi', 'perf', 'microbenchmark', 'gpu', 'cuda', 'network'}
    time_limit = '30m'

    osu_bin_dir    = variable(str, value=OSU_CUDA_DIR)
    device_buffers = variable(str, value='cuda')

    @run_before('run')
    def set_gpu_tasks(self):
        bench_path = self.benchmark_info[0]
        if 'pt2pt' in bench_path:
            self.num_tasks          = 2
            self.num_tasks_per_node = 1
            self.num_gpus_per_task  = 1
            self.num_cpus_per_task  = 4
        else:
            self.num_tasks          = 4
            self.num_tasks_per_node = 1
            self.num_gpus_per_task  = 1
            self.num_cpus_per_task  = 4

    @run_before('run')
    def set_cuda_env(self):
        '''Configure CUDA-aware MPI environment.

        OMPI_MCA_opal_cuda_support: enables CUDA in OpenMPI
        UCX_TLS: prefer GPU-direct RDMA paths for inter-node transfers
        CUDA_VISIBLE_DEVICES: one GPU per rank (rank 0 uses GPU 0)
        '''
        self.env_vars.update({
            'OMPI_MCA_opal_cuda_support': 'true',
            'UCX_TLS':                    'rc,cuda_copy,cuda_ipc,gdr_copy',
            'CUDA_VISIBLE_DEVICES':       '0',
        })
