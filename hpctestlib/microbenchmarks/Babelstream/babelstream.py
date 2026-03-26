# hpctestlib/microbenchmarks/gpu/babelstream.py
#
# BabelStream GPU memory bandwidth benchmark — Spack build.
#
# Build strategy:
#   build_babelstream   — installs via `spack install babelstream +cuda
#                         cuda_arch=80` on the login node (build_locally=True)
#                         Binary on Lustre/NFS — visible to all GPU nodes.
#   BabelStreamCUDATest — loads spack env and runs binary on GPU node.
#   NVBandwidthTest     — runs pre-built bandwidthTest from CUDA extras.
#
# Why spack build:
#   spack handles all cmake flags, compiler selection, CUDA arch,
#   and dependency resolution automatically. No manual cmake invocation,
#   no gcc compatibility issues, no missing flags.
#
# Verified on paramrudra.snbose:
#   2x NVIDIA A100 80GB PCIe, cuda_arch=80, BabelStream 5.0

import os
import re
import shutil
import subprocess

import reframe as rfm
import reframe.utility.sanity as sn
import reframe.utility.udeps as udeps
import reframe.utility.typecheck as typ


# ---------------------------------------------------------------------------
# Spack-aware CUDA detection
# ---------------------------------------------------------------------------

def _run(cmd, timeout=30):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=isinstance(cmd, str)
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


def _spack_find_cuda():
    results = []
    out = _run(['spack', 'find', '--paths', 'cuda'])
    if not out:
        return results
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith('--') or line.startswith('==>'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        spec_str, prefix = parts[0], parts[-1]
        if not os.path.isdir(prefix):
            continue
        m = re.search(r'cuda@(\d+)\.(\d+)\.?(\d*)', spec_str)
        if not m:
            continue
        ver   = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
        hm    = re.search(r'/([a-z0-9]{7,})', spec_str)
        shash = hm.group(1) if hm else ''
        results.append((ver, shash, prefix))
    results.sort(key=lambda x: x[0], reverse=True)
    return results


def _find_cuda_prefix():
    for var in ('CUDA_HOME', 'CUDA_PATH', 'CUDA_ROOT'):
        path = os.environ.get(var, '').strip()
        if path and os.path.isdir(path):
            return path, 'env_var', var
    active = _run(['spack', 'env', 'status'])
    if active and 'No active environment' not in active:
        out = _run(['spack', 'find', '--paths', 'cuda'])
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and os.path.isdir(parts[-1]):
                return parts[-1], 'spack_active_env', parts[0]
    candidates = _spack_find_cuda()
    if candidates:
        cuda_home = os.environ.get('CUDA_HOME', '')
        if cuda_home:
            for ver, shash, prefix in candidates:
                if shash and shash in cuda_home:
                    return prefix, 'spack_hash_match', shash
        ver, shash, prefix = candidates[0]
        return prefix, 'spack_newest', f'cuda@{".".join(str(v) for v in ver)}/{shash}'
    nvcc = shutil.which('nvcc')
    if nvcc:
        return os.path.dirname(os.path.dirname(os.path.realpath(nvcc))), 'which_nvcc', nvcc
    for path in ['/usr/local/cuda', '/usr/cuda', '/opt/cuda']:
        if os.path.isdir(path):
            return path, 'fixed_path', path
    return '', 'not_found', ''


def _find_bandwidth_test(prefix):
    for c in [
        os.path.join(prefix, 'extras', 'demo_suite', 'bandwidthTest'),
        os.path.join(prefix, 'bin', 'bandwidthTest'),
    ]:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    out = _run('find /home/apps/spack/opt/spack -name bandwidthTest '
               '-type f 2>/dev/null', timeout=60)
    hits = [l.strip() for l in out.splitlines()
            if l.strip() and os.access(l.strip(), os.X_OK)]
    if hits:
        for h in hits:
            if CUDA_DETECT_SOURCE and CUDA_DETECT_SOURCE[:7] in h:
                return h
        return hits[0]
    return ''


def _find_spack():
    spack = shutil.which('spack')
    if spack:
        return spack
    for path in [
        '/home/apps/spack/bin/spack',
        '/opt/spack/bin/spack',
        os.path.expanduser('~/spack/bin/spack'),
    ]:
        if os.path.isfile(path):
            return path
    return 'spack'


# Evaluated at import on login node
CUDA_PREFIX, CUDA_DETECT_METHOD, CUDA_DETECT_SOURCE = _find_cuda_prefix()
BANDWIDTH_TEST_BIN = _find_bandwidth_test(CUDA_PREFIX) if CUDA_PREFIX else ''
SPACK_BIN          = _find_spack()

# print(f'[babelstream] CUDA prefix     : {CUDA_PREFIX or "NOT FOUND"}')
# print(f'[babelstream] Detection method: {CUDA_DETECT_METHOD} ({CUDA_DETECT_SOURCE})')
# print(f'[babelstream] bandwidthTest   : {BANDWIDTH_TEST_BIN or "NOT FOUND"}')
# print(f'[babelstream] spack           : {SPACK_BIN}')


# ---------------------------------------------------------------------------
# Theoretical bandwidth lookup
# ---------------------------------------------------------------------------

GPU_THEORETICAL_BW_GBS = {
    'a100 80gb pcie': 1935.0, 'a100 sxm': 2000.0,
    'a100 pcie':      1935.0, 'a100':     1935.0,
    'h100 sxm':       3350.0, 'h100 pcie': 2000.0,
    'h100':           3350.0, 'gh200':    4000.0,
    'v100 sxm2':       900.0, 'v100 pcie': 900.0,
    'v100':            900.0, 'mi300x':   5300.0,
    'mi250x':         3276.0, 'max 1550': 3276.0,
    'max 1100':       1229.0,
}

GPU_CUDA_ARCH = {
    'h100': '90', 'gh200': '90', 'a100': '80',
    'a30':  '80', 'a40':   '86', 'v100': '70',
}


def _lookup_gpu_bw(name_lower):
    for key, bw in GPU_THEORETICAL_BW_GBS.items():
        if key in name_lower:
            return bw
    return 0.0


def _lookup_cuda_arch(name_lower):
    for key, arch in GPU_CUDA_ARCH.items():
        if key in name_lower:
            return arch
    return '80'


def _extract_last_bw(content, section_start, section_end):
    '''Extract last BW value from a bandwidthTest table section.

    Verified output format on paramrudra.snbose:
      Transfer Size (Bytes)        Bandwidth(MB/s)
      1048576                      11265.2
      ...
      67108864                     12890.1   <- last = most stable
    '''
    start = content.find(section_start)
    if start == -1:
        return 0.0
    end = content.find(section_end, start)
    section = content[start:end] if end != -1 else content[start:]
    numbers = re.findall(r'^\s+\d+\s+(\d+\.?\d*)\s*$', section, re.MULTILINE)
    return float(numbers[-1]) if numbers else 0.0


# ---------------------------------------------------------------------------
# Fixture — build BabelStream via spack on LOGIN node
# ---------------------------------------------------------------------------

class build_babelstream(rfm.CompileOnlyRegressionTest):
    '''Build BabelStream using spack on the login node.

    build_locally=True — runs directly on login node, no Slurm job.
    spack handles all cmake flags, compiler selection, CUDA arch,
    and C++ compatibility automatically.

    Binary installed to spack store on Lustre — immediately visible
    on all GPU compute nodes via shared filesystem.

    Spack spec: babelstream@5.0 +cuda cuda_arch=XX
    cuda_arch is detected from GPU name or set via variable.
    '''

    valid_systems       = ['paramrudra.snbose:login']
    valid_prog_environs = ['builtin']
    tags = {'build', 'gpu', 'microbenchmark'}

    #: BabelStream version to install via spack
    #: :type: `str`
    babelstream_version = variable(str, value='5.0', loggable=True)

    #: CUDA architecture — auto-detected from GPU name
    #: Override via: -S build_babelstream.cuda_arch=90
    #: :type: `str`
    cuda_arch = variable(str, value='80', loggable=True)

    #: Populated after spack install — path to cuda-stream binary
    #: :type: `str`
    binary_path = variable(str, value='', loggable=True)

    build_system  = 'Make'
    build_locally = True    # compile on login node — no Slurm job

    @run_before('compile')
    def spack_install(self):
        '''Install BabelStream via spack and record the binary path.'''

        # Detect GPU arch from nvidia-smi if available on login node
        try:
            r = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                name = r.stdout.strip().split('\n')[0]
                self.cuda_arch = _lookup_cuda_arch(name.lower())
        except Exception:
            pass   # keep default arch=80 for A100

        spec = (
            f'babelstream@{self.babelstream_version} '
            f'+cuda '
            f'cuda_arch={self.cuda_arch} '
            f'^cuda@{CUDA_DETECT_SOURCE.split("/")[0].replace("cuda@","") if "cuda@" in CUDA_DETECT_SOURCE else "12.9.0"}'
        )

        self.prebuild_cmds = [
            f'echo "Installing: {spec}"',
            f'echo "Spack    : {SPACK_BIN}"',
            f'echo "CUDA     : {CUDA_PREFIX}"',

            # Install BabelStream via spack
            # --no-checksum needed for main branch
            # reuse=True avoids rebuilding if already installed
            f'{SPACK_BIN} install -j30 --reuse {spec} 2>&1 || '
            f'{SPACK_BIN} install -j30 {spec} 2>&1',

            # Find the installed binary and print its path
            f'BINARY=$({SPACK_BIN} find --paths '
            f'babelstream@{self.babelstream_version} +cuda '
            f'cuda_arch={self.cuda_arch} 2>/dev/null | '
            r"grep -v '^--\|^==>' | awk '{print $NF}' | head -1)",
            f'BINARY="$BINARY/bin/cuda-stream"',
            f'echo "BABELSTREAM_BINARY=$BINARY"',
            f'ls -la "$BINARY"',
        ]

        self.build_system.max_concurrency = 1
        self.build_system.make_opts       = ['--version']

    @run_before('sanity')
    def find_binary(self):
        '''Parse spack find output to get the binary path.'''
        stdout_path = os.path.join(self.stagedir, sn.evaluate(self.stdout))
        if not os.path.exists(stdout_path):
            return
        with open(stdout_path) as f:
            content = f.read()
        m = re.search(r'BABELSTREAM_BINARY=(.+)', content)
        if m:
            self.binary_path = m.group(1).strip()

    @sanity_function
    def validate_build(self):
        return sn.assert_found(r'BABELSTREAM_BINARY=', self.stdout)


# ---------------------------------------------------------------------------
# GPU hardware detection
# ---------------------------------------------------------------------------

@rfm.simple_test
class GPUDetectTest(rfm.RunOnlyRegressionTest):
    '''Detect GPU hardware specs on the compute node via nvidia-smi.'''

    valid_systems       = ['*']
    valid_prog_environs = ['builtin']
    tags = {'hw', 'smoke', 'gpu', 'microbenchmark'}
    time_limit = '5m'
    executable = 'bash'

    @run_before('run')
    def write_detect_script(self):
        lines = [
            '#!/bin/bash', 'set +e', '',
            'echo "=== nvidia-smi csv ==="',
            'nvidia-smi --query-gpu=index,name,memory.total,'
            'driver_version,compute_cap '
            '--format=csv,noheader 2>/dev/null '
            '|| echo "NVIDIA_SMI_UNAVAILABLE"',
            'echo "=== nvidia-smi full ==="',
            'nvidia-smi 2>/dev/null || echo "NVIDIA_SMI_UNAVAILABLE"',
            'echo "=== CUDA detection ==="',
            f'echo "method : {CUDA_DETECT_METHOD}"',
            f'echo "source : {CUDA_DETECT_SOURCE}"',
            f'echo "prefix : {CUDA_PREFIX}"',
            'echo "GPU_DETECT_DONE"',
        ]
        script = os.path.join(self.stagedir, 'gpu_detect.sh')
        with open(script, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.chmod(script, 0o755)
        self.executable_opts = [script]

    @sanity_function
    def validate(self):
        return sn.assert_found(r'GPU_DETECT_DONE', self.stdout)


# ---------------------------------------------------------------------------
# BabelStream benchmark
# ---------------------------------------------------------------------------

@rfm.simple_test
class BabelStreamCUDATest(rfm.RunOnlyRegressionTest):
    '''BabelStream GPU HBM bandwidth — CUDA backend.

    Binary installed by spack on login node, stored on Lustre.
    GPU node runs it directly via shared filesystem.

    References auto-computed:
        ref_GB_s = theoretical_HBM_peak x efficiency_target

    A100 80GB PCIe (1935 GB/s): Triad ref = 1935 x 0.75 = 1451 GB/s
    '''

    valid_systems       = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['builtin']
    tags = {'perf', 'memory', 'gpu', 'microbenchmark', 'babelstream', 'cuda'}
    time_limit = '30m'

    babelstream_build = fixture(build_babelstream, scope='environment')
    gpu_info          = fixture(GPUDetectTest,     scope='environment')

    # num_gpus_per_node is ReFrame 4.x built-in — do NOT redeclare
    array_size = variable(int, value=33554432, loggable=True)
    fallback_theoretical_bw_gbs = variable(float, value=1935.0, loggable=True)
    efficiency_targets = variable(dict, value={
        'Copy':  0.75, 'Scale': 0.75,
        'Add':   0.75, 'Triad': 0.75,
    })
    gpu_name           = variable(str,   value='unknown', loggable=True)
    theoretical_bw_gbs = variable(float, value=0.0,       loggable=True)

    @run_before('run')
    def set_executable_and_gpu(self):
        # Get binary path from spack build fixture
        binary = self.babelstream_build.binary_path

        # Fallback: search spack store directly
        if not binary or not os.path.isfile(binary):
            out = _run(
                f'{SPACK_BIN} find --paths babelstream +cuda 2>/dev/null',
                timeout=30
            )
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and os.path.isdir(parts[-1]):
                    candidate = os.path.join(parts[-1], 'bin', 'cuda-stream')
                    if os.path.isfile(candidate):
                        binary = candidate
                        break

        self.executable      = binary
        self.executable_opts = [
            f'--arraysize {self.array_size}',
            '--numtimes 20',
        ]

        ngpu = self.num_gpus_per_node or 1
        self.num_tasks          = ngpu
        self.num_tasks_per_node = ngpu
        self.num_gpus_per_task  = 1
        self.num_cpus_per_task  = 4
        self.env_vars = {
            'CUDA_VISIBLE_DEVICES': ','.join(str(i) for i in range(ngpu))
        }

        # Read GPU name from GPUDetectTest fixture
        hw_stdout = os.path.join(
            self.gpu_info.stagedir,
            sn.evaluate(self.gpu_info.stdout)
        )
        gpu_name_lower = 'a100 80gb pcie'
        if os.path.exists(hw_stdout):
            with open(hw_stdout) as f:
                content = f.read()
            m = re.search(r'=== nvidia-smi csv ===\n\d+,\s*([^,\n]+),', content)
            if m:
                gpu_name_lower = m.group(1).strip().lower()
                self.gpu_name  = m.group(1).strip()

        self.theoretical_bw_gbs = (
            _lookup_gpu_bw(gpu_name_lower) or self.fallback_theoretical_bw_gbs
        )

    @performance_function('GB/s')
    def extract_bw(self, kind='Copy'):
        if kind not in {'Copy', 'Scale', 'Add', 'Triad', 'Dot'}:
            raise ValueError(f'illegal kind: {kind!r}')
        return sn.extractsingle(
            rf'^{kind}\s+(\S+)', self.stdout, 1, float, re.MULTILINE
        )

    @performance_function('%')
    def triad_efficiency_pct(self):
        triad = sn.extractsingle(
            r'^Triad\s+(\S+)', self.stdout, 1, float, re.MULTILINE
        )
        return sn.defer(sn.evaluate(triad) / self.theoretical_bw_gbs * 100.0)

    @performance_function('%')
    def copy_efficiency_pct(self):
        copy = sn.extractsingle(
            r'^Copy\s+(\S+)', self.stdout, 1, float, re.MULTILINE
        )
        return sn.defer(sn.evaluate(copy) / self.theoretical_bw_gbs * 100.0)

    @performance_function('GB/s')
    def theoretical_peak_gbs(self):
        return sn.defer(self.theoretical_bw_gbs)

    @run_before('performance')
    def set_perf_variables_and_reference(self):
        self.perf_variables = {
            'Copy':                 self.extract_bw('Copy'),
            'Scale':                self.extract_bw('Scale'),
            'Add':                  self.extract_bw('Add'),
            'Triad':                self.extract_bw('Triad'),
            'triad_efficiency_pct': self.triad_efficiency_pct(),
            'copy_efficiency_pct':  self.copy_efficiency_pct(),
            'theoretical_peak_gbs': self.theoretical_peak_gbs(),
            'gpu_name':             sn.defer(self.gpu_name),
            'cuda_detect_method':   sn.defer(CUDA_DETECT_METHOD),
        }
        system_key = f'{self.current_system.name}:{self.current_partition.name}'
        self.reference = {
            system_key: {
                kernel: (self.theoretical_bw_gbs * target, -0.10, None, 'GB/s')
                for kernel, target in self.efficiency_targets.items()
            }
        }

    @sanity_function
    def validate(self):
        return sn.all([
            sn.assert_found(r'BabelStream', self.stdout),
            sn.assert_found(r'Triad',       self.stdout),
            sn.assert_found(r'Solution',    self.stdout),
        ])


# ---------------------------------------------------------------------------
# NVIDIA bandwidthTest — PCIe H2D/D2H
# ---------------------------------------------------------------------------

@rfm.simple_test
class NVBandwidthTest(rfm.RunOnlyRegressionTest):
    '''NVIDIA bandwidthTest — CPU↔GPU PCIe transfer speed.

    Pre-built binary from CUDA extras/demo_suite — no compilation.
    Binary auto-detected via spack — path on Lustre, shared across nodes.

    Verified output format on paramrudra.snbose:
      Transfer Size (Bytes)        Bandwidth(MB/s)
      1048576                      11265.2
      ...
      67108864                     12890.1

    We take the LAST row (largest transfer = most stable reading).

    Verified measurements:
      H2D: ~11000-13000 MB/s   D2H: ~12000-13000 MB/s
      D2D: ~1400000+ MB/s (HBM internal, both GPUs combined)
    '''

    valid_systems       = ['paramrudra.snbose:gpu']
    valid_prog_environs = ['builtin']
    tags = {'perf', 'gpu', 'microbenchmark', 'pcie'}
    time_limit = '15m'

    pcie_ref_mbs = variable(float, value=10000.0,   loggable=True)
    d2d_ref_mbs  = variable(float, value=300000.0,  loggable=True)

    executable      = BANDWIDTH_TEST_BIN or 'bandwidthTest'
    executable_opts = [
        '--memory=pinned',
        '--mode=range',
        '--start=1048576',
        '--end=67108864',
        '--increment=1048576',
    ]

    @run_before('run')
    def set_gpu_options(self):
        self.num_tasks         = 1
        self.num_gpus_per_task = 1
        self.num_cpus_per_task = 2
        self.env_vars          = {'CUDA_VISIBLE_DEVICES': '0'}
        self.prerun_cmds = [
            f'echo "bandwidthTest: {BANDWIDTH_TEST_BIN or "NOT FOUND"}"',
            f'echo "CUDA: {CUDA_DETECT_METHOD} ({CUDA_DETECT_SOURCE})"',
        ]

    @performance_function('MB/s')
    def h2d_bandwidth(self):
        return sn.defer(
            _extract_last_bw(
                open(os.path.join(
                    self.stagedir, sn.evaluate(self.stdout)
                )).read(),
                'Host to Device Bandwidth',
                'Device to Host Bandwidth',
            )
        )

    @performance_function('MB/s')
    def d2h_bandwidth(self):
        return sn.defer(
            _extract_last_bw(
                open(os.path.join(
                    self.stagedir, sn.evaluate(self.stdout)
                )).read(),
                'Device to Host Bandwidth',
                'Device to Device Bandwidth',
            )
        )

    @performance_function('MB/s')
    def d2d_bandwidth(self):
        return sn.defer(
            _extract_last_bw(
                open(os.path.join(
                    self.stagedir, sn.evaluate(self.stdout)
                )).read(),
                'Device to Device Bandwidth',
                'Result =',
            )
        )

    @run_before('performance')
    def set_perf_variables_and_reference(self):
        self.perf_variables = {
            'h2d_bw': self.h2d_bandwidth(),
            'd2h_bw': self.d2h_bandwidth(),
            'd2d_bw': self.d2d_bandwidth(),
        }
        system_key = f'{self.current_system.name}:{self.current_partition.name}'
        self.reference = {
            system_key: {
                'h2d_bw': (self.pcie_ref_mbs, -0.10, None, 'MB/s'),
                'd2h_bw': (self.pcie_ref_mbs, -0.10, None, 'MB/s'),
                'd2d_bw': (self.d2d_ref_mbs,  -0.10, None, 'MB/s'),
            }
        }

    @sanity_function
    def validate(self):
        return sn.assert_found(r'Result = PASS', self.stdout)