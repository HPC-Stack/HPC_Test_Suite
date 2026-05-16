# hpctestlib/microbenchmarks/hpl/hpl.py
#
# HPL (High-Performance Linpack) benchmark — ReFrame test.
#
# Supports CPU and GPU variants via separate test classes:
#   HPLCPUTest  — standard CPU HPL, runs on cpu/hm/login partitions
#   HPLGPUTest  — GPU-accelerated HPL (NVIDIA hpl or nvhpl), gpu partition
#
# HPL.dat is generated dynamically based on detected hardware:
#   N  : auto-computed from available memory (fills ~80% of RAM/VRAM)
#   NB : tuned per architecture (CPU: 128/192/256, GPU: 512/1024)
#   P×Q: auto-computed from num_tasks to maximise square-ness
#
# References auto-computed from theoretical peak × efficiency target.
# Theoretical peak = cores × frequency × FLOP/cycle × sockets.
#
# Verified on paramrudra.snbose:
#   CPU: Intel Xeon Gold 6240R (Cascade Lake)
#        24 cores/socket, 2 sockets, 3.0 GHz boost
#        Theoretical peak (2 sockets): ~2765 GFlops
#        Expected HPL: ~2200 GFlops (~80%)
#   GPU: 2x NVIDIA A100 80GB PCIe per node
#        312 TFLOPS FP64 per GPU
#        Expected GPU HPL: ~250 TFLOPS per GPU

import os
import re
import math
import shutil
import subprocess
import sys

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture


# ---------------------------------------------------------------------------
# Hardware detection helpers
# ---------------------------------------------------------------------------

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=isinstance(cmd, str)
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


def _detect_cpu_info():
    '''Detect CPU cores, sockets, frequency and memory from lscpu/free.'''
    lscpu = _run('lscpu')
    free  = _run('free -g')

    # Cores per socket
    m = re.search(r'Core\(s\) per socket:\s+(\d+)', lscpu)
    cores_per_socket = int(m.group(1)) if m else 24

    # Socket count
    m = re.search(r'Socket\(s\):\s+(\d+)', lscpu)
    sockets = int(m.group(1)) if m else 2

    # Total cores
    total_cores = cores_per_socket * sockets

    # Max frequency (GHz)
    m = re.search(r'CPU max MHz:\s+([\d.]+)', lscpu)
    freq_ghz = float(m.group(1)) / 1000.0 if m else 3.0

    # Total RAM in GB
    m = re.search(r'Mem:\s+(\d+)', free)
    ram_gb = int(m.group(1)) if m else 192

    # AVX-512 = 16 FP64 FLOP/cycle, AVX2 = 8, SSE = 4
    flags_line = _run('grep -m1 flags /proc/cpuinfo')
    if 'avx512' in flags_line:
        flop_per_cycle = 16
    elif 'avx2' in flags_line:
        flop_per_cycle = 8
    else:
        flop_per_cycle = 4

    return {
        'cores_per_socket': cores_per_socket,
        'sockets':          sockets,
        'total_cores':      total_cores,
        'freq_ghz':         freq_ghz,
        'ram_gb':           ram_gb,
        'flop_per_cycle':   flop_per_cycle,
    }


def _theoretical_peak_gflops(hw):
    '''Theoretical FP64 peak in GFlops.'''
    return (hw['total_cores'] * hw['freq_ghz']
            * hw['flop_per_cycle'] * 2)   # ×2 for FMA


def _optimal_n(ram_gb, fraction=0.80):
    '''Compute N such that 3×N²×8 bytes fills fraction of RAM.

    HPL uses ~3N² doubles. Solve for N:
        N = sqrt(ram_gb × 1e9 × fraction / 24)
    Round down to nearest multiple of 256 for good NB alignment.
    '''
    n = math.sqrt(ram_gb * 1e9 * fraction / 24.0)
    return int(n / 256) * 256


def _best_grid(num_tasks):
    '''Find P×Q grid closest to square for given number of tasks.

    Prefers P <= Q (wider than tall) for better HPL efficiency.
    '''
    best_p, best_q = 1, num_tasks
    for p in range(1, int(math.sqrt(num_tasks)) + 1):
        if num_tasks % p == 0:
            q = num_tasks // p
            if abs(p - q) < abs(best_p - best_q):
                best_p, best_q = p, q
    # Ensure P <= Q
    if best_p > best_q:
        best_p, best_q = best_q, best_p
    return best_p, best_q


# ---------------------------------------------------------------------------
# HPL.dat generator
# ---------------------------------------------------------------------------

def _make_hpl_dat(n, nb, p, q, threshold=16.0):
    '''Generate HPL.dat content with the given parameters.'''
    return f"""HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out      output file name (if ndevout = 6, 7: stdout, stderr)
6            device out (6=stdout,7=stderr,file)
1            # of problems sizes (N)
{n}          Ns
1            # of NBs
{nb}         NBs
0            PMAP process mapping (0=Row-,1=Column-major)
1            # of process grids (P x Q)
{p}          Ps
{q}          Qs
{threshold}  threshold
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
{nb}         swapping threshold
0            L1 in (0=transposed,1=no-transposed) form
0            U  in (0=transposed,1=no-transposed) form
1            Equilibration (0=no,1=yes)
8            memory alignment in double (> 0)
"""


# ---------------------------------------------------------------------------
# CPU HPL test
# ---------------------------------------------------------------------------

@rfm.simple_test
class HPLCPUTest(rfm.RunOnlyRegressionTest):
    '''HPL (Linpack) benchmark — CPU variant.

    Runs standard CPU HPL using xhpl from the installed HPL module.

    HPL.dat is auto-generated:
      N  = computed from available RAM (fills ~80%)
      NB = 256 (tunable via nb_size variable)
      P×Q = closest-to-square grid from num_tasks

    References auto-computed from theoretical FP64 peak × efficiency.

    Benchmark selects partitions based on valid_systems.
    Override N, NB, P, Q via -S flags if auto-detection is wrong.

    Example — run on CPU partition, 4 MPI ranks:
        reframe -c hpl.py -n HPLCPUTest \
                 -S valid_systems=paramrudra.snbose:cpu \
                 -S valid_prog_environs=gnu \
                 -S HPLCPUTest.num_tasks=4 -r
    '''

    valid_systems = [
        'paramrudra.snbose:cpu',
        'paramrudra.snbose:hm',
    ]
    valid_prog_environs = ['gnu', 'foss', 'builtin']
    tags = {'perf', 'compute', 'hpl', 'cpu'}
    time_limit = '2h'

    # -------------------------------------------------------------------
    # Tuneable parameters — all overrideable via -S
    # -------------------------------------------------------------------

    #: HPL module to load — update to match your spack hash
    #: Check with: spack find --paths hpl
    #: :type: `str`
    hpl_module = variable(str, value='hpl/pp7qab2', loggable=True)

    #: Number of MPI tasks — P×Q must equal this
    #: If left at 0, auto-set from p_grid × q_grid
    #: ReFrame built-in — override via -S HPLCPUTest.num_tasks=N
    # num_tasks is built-in — do NOT redeclare

    #: Tasks per node

    #: Block size NB — 128/192/256 for CPU, 512/1024 for GPU
    #: :type: `int`
    nb_size = variable(int, value=256, loggable=True)

    #: N problem size — 0 = auto-detect from RAM
    #: :type: `int`
    n_size = variable(int, value=0, loggable=True)

    #: P grid dimension — 0 = auto-compute from num_tasks
    #: :type: `int`
    p_grid = variable(int, value=0, loggable=True)

    #: Q grid dimension — 0 = auto-compute from num_tasks
    #: :type: `int`
    q_grid = variable(int, value=0, loggable=True)

    #: Memory fraction for auto-N computation
    #: :type: `float`
    mem_fraction = variable(float, value=0.80, loggable=True)

    #: Minimum efficiency % vs theoretical peak for reference
    #: :type: `float`
    efficiency_target = variable(float, value=0.75, loggable=True)

    #: Detected theoretical peak GFlops — populated at run time
    theoretical_peak_gflops = variable(float, value=0.0, loggable=True)

    executable = 'xhpl'

    @run_before('run')
    def load_module(self):
        self.modules = [self.hpl_module]

    @run_before('run')
    def generate_hpl_dat(self):
        '''Auto-compute N, NB, P, Q and write HPL.dat.'''
        hw = _detect_cpu_info()

        # N: use explicit value or auto-compute from RAM
        n = self.n_size if self.n_size > 0 else _optimal_n(
            hw['ram_gb'], self.mem_fraction
        )

        # P×Q: use explicit values or auto-compute from num_tasks
        total_tasks = (
            self.num_tasks
            if getattr(self, 'num_tasks', 0)
            else self.num_tasks_per_node
        )
        if self.p_grid > 0 and self.q_grid > 0:
            p, q = self.p_grid, self.q_grid
        else:
            p, q = _best_grid(total_tasks)

        # Store theoretical peak for reference computation
        self.theoretical_peak_gflops = _theoretical_peak_gflops(hw)

        hpl_dat = _make_hpl_dat(n, self.nb_size, p, q)

        self.prerun_cmds = [
            f"cat > HPL.dat << 'HPLEOF'\n{hpl_dat}\nHPLEOF",
            'echo "=== HPL.dat ==="',
            'cat HPL.dat',
            'echo "=== System info ==="',
            f'echo "N={n} NB={self.nb_size} P={p} Q={q} '
            f'tasks={total_tasks}"',
            f'echo "RAM={hw["ram_gb"]}GB cores={hw["total_cores"]} '
            f'freq={hw["freq_ghz"]:.2f}GHz"',
            f'echo "Theoretical peak: '
            f'{self.theoretical_peak_gflops:.1f} GFlops"',
        ]

    @run_before('run')
    def set_mpirun_launcher(self):
        '''Use mpirun to avoid PMI issues with srun.'''
        add_env_capture(self)
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--mca pml ob1',
            '--mca btl ^openib',
            '--bind-to core',
        ]

    @run_before('performance')
    def set_reference(self):
        '''Auto-compute reference from theoretical peak × efficiency target.'''
        if self.theoretical_peak_gflops > 0:
            ref = self.theoretical_peak_gflops * self.efficiency_target
        else:
            # Fallback: Gold 6240R 2-socket estimate
            ref = 2200.0

        system_key = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        self.reference = {
            system_key: {
                'gflops': (ref, -0.10, None, 'GFlops')
            }
        }

    @performance_function('GFlops')
    def gflops(self):
        '''Extract GFlops from HPL WR line.

        HPL output format:
          WR11C2R4       10000  256     2     2  123.45  1.234e+03
          ^bench         ^N     ^NB     ^P    ^Q  ^time   ^GFlops
        '''
        return sn.extractsingle(
            r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+([\d.Ee+]+)',
            self.stdout, 1, float
        )

    @performance_function('GFlops')
    def theoretical_peak(self):
        return sn.defer(self.theoretical_peak_gflops)

    @performance_function('%')
    def efficiency_pct(self):
        gf   = sn.extractsingle(
            r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+([\d.Ee+]+)',
            self.stdout, 1, float
        )
        return sn.defer(
            sn.evaluate(gf) / max(self.theoretical_peak_gflops, 1.0) * 100.0
        )

    @sanity_function
    def validate(self):
        return sn.all([
            sn.assert_found(r'End of Tests\.', self.stdout),
            sn.assert_not_found(r'FAILED', self.stdout),
        ])


# ---------------------------------------------------------------------------
# GPU HPL test
# ---------------------------------------------------------------------------

@rfm.simple_test
class HPLGPUTest(rfm.RunOnlyRegressionTest):
    '''HPL benchmark — GPU-accelerated variant (NVIDIA HPL / nvhpl).

    Uses NVIDIA-optimised HPL which offloads DGEMM to GPU via cuBLAS.
    Each MPI rank uses one GPU. Typically 1-2 ranks per GPU node.

    HPL.dat auto-generated:
      N  = computed from GPU VRAM (fills ~80% of total VRAM across ranks)
      NB = 1024 (optimal for GPU cuBLAS tile size)
      P×Q = auto-computed from num_tasks

    References based on A100 80GB PCIe FP64 theoretical:
      Single GPU:  312 TFlops (0.312 PFlops)
      Dual GPU:    624 TFlops
      Expected HPL efficiency: ~70-80%

    Example — run on GPU partition, 2 ranks (one per GPU):
        reframe -c hpl.py -n HPLGPUTest \
                 -S valid_systems=paramrudra.snbose:gpu \
                 -S valid_prog_environs=gnu \
                 -S HPLGPUTest.num_tasks=2 -r
    '''

    valid_systems       = ['*:gpu']
    valid_prog_environs = ['gnu', 'foss', 'builtin']
    tags = {'perf', 'compute', 'hpl', 'gpu'}
    time_limit = '4h'

    # -------------------------------------------------------------------
    # Tuneable parameters
    # -------------------------------------------------------------------

    #: HPL module — NVIDIA HPL (hpl-nvidia) or standard HPL with GPU support
    #: Check: spack find --paths hpl
    #: :type: `str`
    hpl_module = variable(str, value='hpl/pp7qab2', loggable=True)

    #: Number of GPUs per node — matches your hardware (A100 nodes = 2)
    #: :type: `int`
    gpus_per_node = variable(int, value=2, loggable=True)

    #: GPU VRAM per device in GB — A100 80GB = 80
    #: :type: `float`
    gpu_vram_gb = variable(float, value=80.0, loggable=True)

    #: GPU FP64 theoretical peak in GFlops — A100 PCIe = 312000
    #: :type: `float`
    gpu_peak_gflops = variable(float, value=312000.0, loggable=True)

    #: NB block size — 1024 optimal for A100 cuBLAS
    #: :type: `int`
    nb_size = variable(int, value=1024, loggable=True)

    #: N problem size — 0 = auto-detect from GPU VRAM
    #: :type: `int`
    n_size = variable(int, value=0, loggable=True)

    #: P grid dimension — 0 = auto-compute
    #: :type: `int`
    p_grid = variable(int, value=0, loggable=True)

    #: Q grid dimension — 0 = auto-compute
    #: :type: `int`
    q_grid = variable(int, value=0, loggable=True)

    #: Memory fraction of GPU VRAM to use
    #: :type: `float`
    mem_fraction = variable(float, value=0.80, loggable=True)

    #: Minimum efficiency % vs GPU FP64 theoretical peak
    #: :type: `float`
    efficiency_target = variable(float, value=0.70, loggable=True)

    num_tasks_per_node = 1   # 1 MPI rank per node by default
    executable = 'xhpl'

    @run_before('run')
    def load_module(self):
        self.modules = [self.hpl_module]

    @run_before('run')
    def configure_gpu_run(self):
        '''Set GPU layout and generate HPL.dat for GPU run.

        Each MPI rank uses all GPUs on its node.
        For 2 GPUs per node with 1 rank per node: P×Q covers all nodes.
        For 1 GPU per rank: set num_tasks_per_node = gpus_per_node.
        '''
        total_tasks = getattr(self, 'num_tasks', None) or self.num_tasks_per_node
        total_gpus  = total_tasks * self.gpus_per_node

        # N from total GPU VRAM across all GPUs
        if self.n_size > 0:
            n = self.n_size
        else:
            total_vram = total_gpus * self.gpu_vram_gb
            n = _optimal_n(total_vram, self.mem_fraction)

        # P×Q grid
        if self.p_grid > 0 and self.q_grid > 0:
            p, q = self.p_grid, self.q_grid
        else:
            p, q = _best_grid(total_tasks)

        self.num_gpus_per_task = self.gpus_per_node

        hpl_dat = _make_hpl_dat(n, self.nb_size, p, q)

        self.prerun_cmds = [
            f"cat > HPL.dat << 'HPLEOF'\n{hpl_dat}\nHPLEOF",
            'echo "=== HPL.dat ==="',
            'cat HPL.dat',
            'echo "=== GPU info ==="',
            'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader '
            '2>/dev/null || echo "nvidia-smi unavailable"',
            f'echo "N={n} NB={self.nb_size} P={p} Q={q} '
            f'tasks={total_tasks} GPUs={total_gpus}"',
        ]

        self.env_vars = {
            'CUDA_VISIBLE_DEVICES': ','.join(
                str(i) for i in range(self.gpus_per_node)
            ),
        }

    @run_before('run')
    def set_mpirun_launcher(self):
        add_env_capture(self)
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--mca pml ob1',
            '--mca btl ^openib',
            '--bind-to none',   # GPU runs need flexible binding
        ]

    @run_before('performance')
    def set_reference(self):
        '''Auto-compute reference from GPU FP64 peak × efficiency.'''
        total_tasks = getattr(self, 'num_tasks', None) or 1
        total_gpus  = total_tasks * self.gpus_per_node
        peak        = self.gpu_peak_gflops * total_gpus
        ref         = peak * self.efficiency_target

        system_key  = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        self.reference = {
            system_key: {
                'gflops': (ref, -0.10, None, 'GFlops')
            }
        }

    @performance_function('GFlops')
    def gflops(self):
        return sn.extractsingle(
            r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+([\d.Ee+]+)',
            self.stdout, 1, float
        )

    @performance_function('GFlops')
    def gpu_theoretical_peak(self):
        total_tasks = getattr(self, 'num_tasks', None) or 1
        total_gpus  = total_tasks * self.gpus_per_node
        return sn.defer(self.gpu_peak_gflops * total_gpus)

    @performance_function('%')
    def efficiency_pct(self):
        total_tasks = getattr(self, 'num_tasks', None) or 1
        total_gpus  = total_tasks * self.gpus_per_node
        peak        = self.gpu_peak_gflops * total_gpus
        gf = sn.extractsingle(
            r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+([\d.Ee+]+)',
            self.stdout, 1, float
        )
        return sn.defer(sn.evaluate(gf) / peak * 100.0)

    @sanity_function
    def validate(self):
        return sn.all([
            sn.assert_found(r'End of Tests\.', self.stdout),
            sn.assert_not_found(r'FAILED', self.stdout),
        ])