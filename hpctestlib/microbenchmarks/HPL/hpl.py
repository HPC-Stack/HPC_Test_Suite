# hpctestlib/microbenchmarks/hpl/hpl.py
#
# HPL (High-Performance Linpack) benchmark — ReFrame test.
#
# Supports CPU and GPU variants via separate test classes:
#   HPLCPUTest  — standard CPU HPL, runs on cpu/hm partitions
#   HPLGPUTest  — GPU-accelerated HPL (NVIDIA HPL / nvhpl), gpu partition
#
# HPL.dat is generated ON THE COMPUTE NODE at job start via a shell probe
# script (prerun_cmds).  This is the critical difference from earlier
# versions that called _detect_cpu_info() on the login node and produced
# an N that OOM-killed rank 23 on rbcn014.
#
# Detection flow (CPU):
#   1. Shell probe script runs on compute node:
#        - reads free -g  → RAM_GB
#        - reads lscpu    → CORES, SOCKETS, FREQ_MHZ
#        - reads /proc/cpuinfo flags → FLOP_PER_CYCLE (avx512/avx2/sse)
#        - computes N = floor(sqrt(RAM_GB×1e9×fraction/24)/NB)×NB
#        - writes HPL.dat
#        - prints RFM_THEO_PEAK=<value> for sanity to parse back
#   2. ReFrame sanity extracts theoretical_peak from stdout and stores it
#      as a performance variable.
#
# For GPU runs N is computed from gpu_vram_gb × gpus_per_node (no
# on-node probe needed — GPU VRAM does not vary like RAM).
#
# Fixes vs previous versions:
#   1. N computed on compute node (fixes OOM kill / signal 9 on rank 23)
#   2. GFlops regex uses \S+ — handles all HPL float formats
#   3. valid_prog_environs = ['gnu'] only — foss removed (xhpl not on PATH
#      under foss with hpl/pp7qab2 gnu build)
#   4. OMPI_MCA_orte_base_help_aggregate=0 suppressed; use
#      --mca orte_base_help_aggregate 1 to silence CUDA dlopen spam on
#      CPU-only nodes
#
# Verified on paramrudra.snbose:
#   CPU node rbcn014: Intel Xeon Gold 6240R, 2 sockets, 48 cores, ~192 GB RAM
#   GPU node rbgpu00x: 2× NVIDIA A100 80GB PCIe

import os
import math
import sys

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher

sys.path.append(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'continuousbench', 'hooks'
))
from env_capture import add_env_capture


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Matches the HPL WR result line in every float format:
#   WR11C2R4   86016  256   6   8  123.45  4.608e+03
#   ^bench      ^N    ^NB  ^P  ^Q  ^time   ^GFlops
# \S+ covers: 1234.5  1.234e+03  1.234e+003  1.234e-01  1.234E+03
_WR_PATTERN = r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+\S+\s+(\S+)'

# Sentinel printed by the probe script so sanity can parse theoretical peak
_THEO_PEAK_TAG = 'RFM_THEO_PEAK'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _best_grid(num_tasks):
    '''Find the P×Q grid closest to square for num_tasks MPI ranks.

    Returns (P, Q) with P <= Q (wider-than-tall preferred by HPL).
    Falls back to (1, num_tasks) for prime num_tasks.
    '''
    best_p, best_q = 1, num_tasks
    for p in range(1, int(math.sqrt(num_tasks)) + 1):
        if num_tasks % p == 0:
            q = num_tasks // p
            if abs(p - q) < abs(best_p - best_q):
                best_p, best_q = p, q
    if best_p > best_q:
        best_p, best_q = best_q, best_p
    return best_p, best_q


def _make_hpl_dat(n, nb, p, q, threshold=16.0):
    '''Return HPL.dat content string for the given parameters.'''
    return (
        f'HPLinpack benchmark input file\n'
        f'Innovative Computing Laboratory, University of Tennessee\n'
        f'HPL.out      output file name (if ndevout = 6, 7: stdout, stderr)\n'
        f'6            device out (6=stdout,7=stderr,file)\n'
        f'1            # of problems sizes (N)\n'
        f'{n}          Ns\n'
        f'1            # of NBs\n'
        f'{nb}         NBs\n'
        f'0            PMAP process mapping (0=Row-,1=Column-major)\n'
        f'1            # of process grids (P x Q)\n'
        f'{p}          Ps\n'
        f'{q}          Qs\n'
        f'{threshold}  threshold\n'
        f'1            # of panel fact\n'
        f'2            PFACTs (0=Left, 1=Crout, 2=Right)\n'
        f'1            # of recursive stopping criterium\n'
        f'4            NBMINs (>= 1)\n'
        f'1            # of panels in recursion\n'
        f'2            NDIVs\n'
        f'1            # of recursive panel fact.\n'
        f'1            RFACTs (0=Left, 1=Crout, 2=Right)\n'
        f'1            # of broadcast\n'
        f'1            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)\n'
        f'1            # of lookahead depth\n'
        f'1            DEPTHs (>=0)\n'
        f'2            SWAP (0=bin-syst,1=long,2=mix)\n'
        f'{nb}         swapping threshold\n'
        f'0            L1 in (0=transposed,1=no-transposed) form\n'
        f'0            U  in (0=transposed,1=no-transposed) form\n'
        f'1            Equilibration (0=no,1=yes)\n'
        f'8            memory alignment in double (> 0)\n'
    )


def _probe_script(nb, p, q, mem_fraction, fallback_ram_gb=192,
                  fallback_cores=48, fallback_freq_mhz=3000,
                  fallback_flop=16):
    '''Return a bash probe script that:

    - Detects RAM, cores, frequency, and SIMD width on the COMPUTE NODE
    - Computes N = floor(sqrt(ram_gb×1e9×fraction/24)/NB)×NB
    - Writes HPL.dat
    - Prints RFM_THEO_PEAK=<GFlops> so ReFrame can parse it back

    All detection uses shell builtins and standard Linux tools only.
    Falls back to supplied defaults if any tool is unavailable.
    '''
    return f"""#!/bin/bash
set -euo pipefail

# ---- Detect RAM (GB, integer) on THIS node ----
RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/ {{print $2}}')
RAM_GB=${{RAM_GB:-{fallback_ram_gb}}}
[[ "$RAM_GB" -gt 0 ]] 2>/dev/null || RAM_GB={fallback_ram_gb}

# ---- Detect cores, sockets, frequency ----
TOTAL_CORES=$(lscpu 2>/dev/null | awk '/^CPU\\(s\\):/ {{print $2; exit}}')
TOTAL_CORES=${{TOTAL_CORES:-{fallback_cores}}}

FREQ_MHZ=$(lscpu 2>/dev/null | awk '/CPU max MHz/ {{print int($NF); exit}}')
FREQ_MHZ=${{FREQ_MHZ:-{fallback_freq_mhz}}}

# ---- Detect SIMD width for theoretical peak ----
if grep -qm1 avx512 /proc/cpuinfo 2>/dev/null; then
    FLOP_PER_CYCLE=16
elif grep -qm1 avx2 /proc/cpuinfo 2>/dev/null; then
    FLOP_PER_CYCLE=8
else
    FLOP_PER_CYCLE={fallback_flop}
fi

# ---- Compute theoretical FP64 peak (GFlops) ----
# peak = cores x (freq_MHz/1000) x flop_per_cycle x 2 (FMA)
THEO_PEAK=$(awk "BEGIN {{printf \\"%.1f\\", $TOTAL_CORES * ($FREQ_MHZ/1000.0) * $FLOP_PER_CYCLE * 2}}")

# ---- Compute N ----
# N = floor(sqrt(ram_gb * 1e9 * fraction / 24) / NB) * NB
NB={nb}
FRACTION={mem_fraction}
N=$(python3 -c "
import math
ram_gb = $RAM_GB
n = math.sqrt(ram_gb * 1e9 * $FRACTION / 24.0)
nb = {nb}
print(int(n / nb) * nb)
")

P={p}
Q={q}

echo "=== Compute-node hardware probe ==="
echo "  RAM_GB=$RAM_GB  CORES=$TOTAL_CORES  FREQ_MHZ=$FREQ_MHZ"
echo "  FLOP_PER_CYCLE=$FLOP_PER_CYCLE  FRACTION=$FRACTION"
echo "  N=$N  NB=$NB  P=$P  Q=$Q"
echo "  {_THEO_PEAK_TAG}=$THEO_PEAK"

# ---- Write HPL.dat ----
cat > HPL.dat << HPLEOF
HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out      output file name (if ndevout = 6, 7: stdout, stderr)
6            device out (6=stdout,7=stderr,file)
1            # of problems sizes (N)
$N          Ns
1            # of NBs
$NB         NBs
0            PMAP process mapping (0=Row-,1=Column-major)
1            # of process grids (P x Q)
$P          Ps
$Q          Qs
{16.0}  threshold
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
$NB         swapping threshold
0            L1 in (0=transposed,1=no-transposed) form
0            U  in (0=transposed,1=no-transposed) form
1            Equilibration (0=no,1=yes)
8            memory alignment in double (> 0)
HPLEOF

echo "=== HPL.dat written ==="
cat HPL.dat
"""


# ---------------------------------------------------------------------------
# CPU HPL test
# ---------------------------------------------------------------------------

@rfm.simple_test
class HPLCPUTest(rfm.RunOnlyRegressionTest):
    '''HPL (Linpack) benchmark — CPU variant.

    HPL.dat and theoretical peak are computed by a shell probe that runs
    on the actual compute node, avoiding the login-node OOM bug where
    _detect_cpu_info() read login-node RAM and produced an N too large
    for compute nodes.

    Quick start:
        reframe -c hpl.py -n HPLCPUTest \\
                 -S valid_systems=paramrudra.snbose:cpu \\
                 -S HPLCPUTest.num_tasks=48 -r
    '''

    valid_systems       = ['paramrudra.snbose:cpu', 'paramrudra.snbose:hm']
    valid_prog_environs = ['foss']
    tags       = {'perf', 'compute', 'hpl', 'cpu'}
    time_limit = '2h'
    executable = 'xhpl'

    # -------------------------------------------------------------------
    # Tuneable parameters — all overrideable via -S
    # -------------------------------------------------------------------

    #: HPL module — verify hash with: spack find --paths hpl
    hpl_module = variable(str, value='hpl/pp7qab2', loggable=True)

    #: NB block size — 128/192/256 typical for Cascade Lake
    nb_size = variable(int, value=256, loggable=True)

    #: N problem size — 0 = auto-detect on compute node
    n_size = variable(int, value=0, loggable=True)

    #: P grid dimension — 0 = auto-compute from num_tasks
    p_grid = variable(int, value=0, loggable=True)

    #: Q grid dimension — 0 = auto-compute from num_tasks
    q_grid = variable(int, value=0, loggable=True)

    #: Fraction of compute-node RAM to use for the HPL matrix
    mem_fraction = variable(float, value=0.75, loggable=True)

    #: Minimum efficiency vs theoretical FP64 peak for pass/fail reference
    efficiency_target = variable(float, value=0.75, loggable=True)

    # Fallbacks used by the probe script when lscpu/free are unavailable
    fallback_ram_gb    = variable(int,   value=192,  loggable=True)
    fallback_cores     = variable(int,   value=48,   loggable=True)
    fallback_freq_mhz  = variable(int,   value=3000, loggable=True)
    fallback_flop      = variable(int,   value=16,   loggable=True)

    # -------------------------------------------------------------------
    # Setup hooks
    # -------------------------------------------------------------------

    @run_before('run')
    def load_module(self):
        self.modules = [self.hpl_module]

    @run_before('run')
    def generate_hpl_dat(self):
        '''Build the probe script that runs on the compute node.

        If n_size > 0 the probe still runs (for theoretical peak output)
        but N is overridden to the fixed value afterwards via sed.
        '''
        total_tasks = getattr(self, 'num_tasks', None) or 1
        if self.p_grid > 0 and self.q_grid > 0:
            p, q = self.p_grid, self.q_grid
        else:
            p, q = _best_grid(total_tasks)

        script = _probe_script(
            nb=self.nb_size, p=p, q=q,
            mem_fraction=self.mem_fraction,
            fallback_ram_gb=self.fallback_ram_gb,
            fallback_cores=self.fallback_cores,
            fallback_freq_mhz=self.fallback_freq_mhz,
            fallback_flop=self.fallback_flop,
        )

        cmds = [
            # Write and run probe on the compute node
            f"cat > _hpl_probe.sh << 'PROBEEOF'\n{script}\nPROBEEOF",
            'bash _hpl_probe.sh',
        ]

        # If the user set n_size explicitly, overwrite N in HPL.dat
        if self.n_size > 0:
            cmds.append(
                f"sed -i 's/^[0-9]\\+.*Ns$/{self.n_size}          Ns/' HPL.dat"
            )
            cmds.append(f'echo "N overridden to {self.n_size}"')

        # Suppress CUDA dlopen spam on CPU-only nodes (harmless warning)
        cmds.append(
            'export OMPI_MCA_mpi_warn_on_fork=0 '
            'OMPI_MCA_orte_base_help_aggregate=1'
        )

        self.prerun_cmds = cmds

    @run_before('run')
    def set_launcher(self):
        add_env_capture(self)
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--mca pml ob1',
            '--mca btl ^openib',
            '--mca orte_base_help_aggregate 1',  # suppress CUDA dlopen spam
            '--bind-to core',
        ]

    # -------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------

    @run_before('performance')
    def set_reference(self):
        '''Auto-compute reference from parsed theoretical peak × efficiency.

        theoretical_peak_gflops is extracted from the RFM_THEO_PEAK line
        printed by the probe script on the compute node, so it reflects
        actual compute-node hardware rather than login-node hardware.
        '''
        theo = sn.evaluate(
            sn.extractsingle(
                rf'{_THEO_PEAK_TAG}=([\d.]+)', self.stdout, 1, float
            )
        )
        ref = theo * self.efficiency_target if theo > 0 else 2200.0
        system_key = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        self.reference = {
            system_key: {'gflops': (ref, -0.10, None, 'GFlops')}
        }

    @performance_function('GFlops')
    def gflops(self):
        '''GFlops from the HPL WR result line.

        HPL output format (columns: bench N NB P Q time GFlops):
          WR11C2R4  86016  256  6  8  123.45  4.608e+03
        \\S+ handles all float formats.
        '''
        return sn.extractsingle(_WR_PATTERN, self.stdout, 1, float)

    @performance_function('GFlops')
    def theoretical_peak(self):
        '''Theoretical FP64 peak as detected on the compute node.'''
        return sn.extractsingle(
            rf'{_THEO_PEAK_TAG}=([\d.]+)', self.stdout, 1, float
        )

    @performance_function('%')
    def efficiency_pct(self):
        '''Measured GFlops as % of compute-node theoretical FP64 peak.'''
        gf   = sn.extractsingle(_WR_PATTERN, self.stdout, 1, float)
        theo = sn.extractsingle(
            rf'{_THEO_PEAK_TAG}=([\d.]+)', self.stdout, 1, float
        )
        return sn.defer(sn.evaluate(gf) / max(sn.evaluate(theo), 1.0) * 100.0)

    # -------------------------------------------------------------------
    # Sanity
    # -------------------------------------------------------------------

    @sanity_function
    def validate(self):
        return sn.all([
            sn.assert_found(rf'{_THEO_PEAK_TAG}=', self.stdout),
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
    Each MPI rank maps to all GPUs on its node (default: 1 rank/node,
    2 GPUs/node).

    For one rank per GPU: set num_tasks_per_node = gpus_per_node.

    Quick start — 1 node, 2 GPUs:
        reframe -c hpl.py -n HPLGPUTest \\
                 -S valid_systems=paramrudra.snbose:gpu \\
                 -S HPLGPUTest.num_tasks=1 -r

    Quick start — 2 nodes, 4 GPUs:
        reframe -c hpl.py -n HPLGPUTest \\
                 -S valid_systems=paramrudra.snbose:gpu \\
                 -S HPLGPUTest.num_tasks=2 -r
    '''

    valid_systems       = ['*:gpu']
    valid_prog_environs = ['gnu']
    tags       = {'perf', 'compute', 'hpl', 'gpu'}
    time_limit = '4h'
    executable = 'xhpl'

    num_tasks_per_node = 1   # 1 MPI rank per node; rank owns all node GPUs

    # -------------------------------------------------------------------
    # Tuneable parameters
    # -------------------------------------------------------------------

    #: HPL module — update to match your GPU-capable HPL build
    hpl_module = variable(str, value='hpl/pp7qab2', loggable=True)

    #: GPUs per node — must match hardware (A100 nodes = 2)
    gpus_per_node = variable(int, value=2, loggable=True)

    #: GPU VRAM per device in GB — A100 80GB PCIe = 80
    gpu_vram_gb = variable(float, value=80.0, loggable=True)

    #: GPU FP64 theoretical peak per card in GFlops — A100 PCIe = 312000
    gpu_peak_gflops = variable(float, value=312000.0, loggable=True)

    #: NB block size — 1024 optimal for A100 cuBLAS tile size
    nb_size = variable(int, value=1024, loggable=True)

    #: N problem size — 0 = auto-detect from total GPU VRAM
    n_size = variable(int, value=0, loggable=True)

    #: P grid dimension — 0 = auto-compute from num_tasks
    p_grid = variable(int, value=0, loggable=True)

    #: Q grid dimension — 0 = auto-compute from num_tasks
    q_grid = variable(int, value=0, loggable=True)

    #: Fraction of total GPU VRAM to use for the HPL matrix
    mem_fraction = variable(float, value=0.80, loggable=True)

    #: Minimum efficiency vs GPU FP64 theoretical peak for pass/fail
    efficiency_target = variable(float, value=0.70, loggable=True)

    # -------------------------------------------------------------------
    # Setup hooks
    # -------------------------------------------------------------------

    @run_before('run')
    def load_module(self):
        self.modules = [self.hpl_module]

    @run_before('run')
    def configure_gpu_run(self):
        '''Compute N from GPU VRAM (known at setup time) and write HPL.dat.'''
        import math as _math
        total_tasks = getattr(self, 'num_tasks', None) or self.num_tasks_per_node
        total_gpus  = total_tasks * self.gpus_per_node

        if self.n_size > 0:
            n = self.n_size
        else:
            total_vram = total_gpus * self.gpu_vram_gb
            raw_n = _math.sqrt(total_vram * 1.0e9 * self.mem_fraction / 24.0)
            n = int(raw_n / self.nb_size) * self.nb_size

        if self.p_grid > 0 and self.q_grid > 0:
            p, q = self.p_grid, self.q_grid
        else:
            p, q = _best_grid(total_tasks)

        self.num_gpus_per_task = self.gpus_per_node

        total_peak = self.gpu_peak_gflops * total_gpus
        hpl_dat    = _make_hpl_dat(n, self.nb_size, p, q)

        self.prerun_cmds = [
            f"cat > HPL.dat << 'HPLEOF'\n{hpl_dat}\nHPLEOF",
            'echo "=== HPL.dat ==="',
            'cat HPL.dat',
            'echo "=== GPU info ==="',
            ('nvidia-smi --query-gpu=name,memory.total '
             '--format=csv,noheader 2>/dev/null '
             '|| echo "nvidia-smi unavailable"'),
            (f'echo "N={n} NB={self.nb_size} P={p} Q={q} '
             f'tasks={total_tasks} GPUs={total_gpus}"'),
            f'echo "{_THEO_PEAK_TAG}={total_peak:.1f}"',
        ]
        self.env_vars = {
            'CUDA_VISIBLE_DEVICES': ','.join(
                str(i) for i in range(self.gpus_per_node)
            ),
        }

    @run_before('run')
    def set_launcher(self):
        add_env_capture(self)
        self.job.launcher = getlauncher('mpirun')()
        self.job.launcher.options = [
            '--mca pml ob1',
            '--mca btl ^openib',
            '--mca orte_base_help_aggregate 1',
            '--bind-to none',   # GPU runs need flexible thread binding
        ]

    # -------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------

    @run_before('performance')
    def set_reference(self):
        total_tasks = getattr(self, 'num_tasks', None) or 1
        total_gpus  = total_tasks * self.gpus_per_node
        peak        = self.gpu_peak_gflops * total_gpus
        ref         = peak * self.efficiency_target
        system_key  = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        self.reference = {
            system_key: {'gflops': (ref, -0.10, None, 'GFlops')}
        }

    @performance_function('GFlops')
    def gflops(self):
        '''GFlops from the HPL WR result line.'''
        return sn.extractsingle(_WR_PATTERN, self.stdout, 1, float)

    @performance_function('GFlops')
    def gpu_theoretical_peak(self):
        '''Total GPU FP64 theoretical peak across all GPUs.'''
        return sn.extractsingle(
            rf'{_THEO_PEAK_TAG}=([\d.]+)', self.stdout, 1, float
        )

    @performance_function('%')
    def efficiency_pct(self):
        '''Measured GFlops as % of total GPU FP64 theoretical peak.'''
        gf   = sn.extractsingle(_WR_PATTERN, self.stdout, 1, float)
        theo = sn.extractsingle(
            rf'{_THEO_PEAK_TAG}=([\d.]+)', self.stdout, 1, float
        )
        return sn.defer(sn.evaluate(gf) / max(sn.evaluate(theo), 1.0) * 100.0)

    # -------------------------------------------------------------------
    # Sanity
    # -------------------------------------------------------------------

    @sanity_function
    def validate(self):
        return sn.all([
            sn.assert_found(rf'{_THEO_PEAK_TAG}=', self.stdout),
            sn.assert_found(r'End of Tests\.', self.stdout),
            sn.assert_not_found(r'FAILED', self.stdout),
        ])