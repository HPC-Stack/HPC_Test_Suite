# Copyright 2016-2022 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Extended with hardware detection + theoretical bandwidth calculation.
#
# Verified hardware — paramrudra.snbose (all partitions):
#   CPU:     Intel Xeon Gold 6240R (Cascade Lake)
#   Sockets: 2,  Cores: 24 per socket (48 total, no HT)
#   Memory:  DDR4-2933, 6 channels per socket
#
# Theoretical peak (per socket, 24 threads):
#   6ch x 8B x 2933 MHz x 2 / 1e9 = 281.6 GB/s
#
# Theoretical peak (both sockets, 48 threads):
#   12ch x 8B x 2933 MHz x 2 / 1e9 = 563.2 GB/s
#
# Measured on rbgpu004/rbgpu005 (24 threads, 1 socket):
#   Copy:  ~198000 MB/s  (~70% of 281.6 GB/s)
#   Scale: ~143000 MB/s  (~51%)
#   Add:   ~165000 MB/s  (~59%)
#   Triad: ~172000 MB/s  (~61%)

import re
import os

import reframe as rfm
import reframe.utility.sanity as sn
import reframe.utility.udeps as udeps
import reframe.utility.typecheck as typ


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _theoretical_bw_gbs(channels, freq_mhz, bus_bits=64, transfers=2):
    '''
    Compute theoretical peak DRAM bandwidth in GB/s.

    Formula:
        peak = channels x (bus_bits/8) x freq_MHz x 1e6 x transfers / 1e9

    Use channels for the sockets being benchmarked, not total system
    channels. STREAM with 24 threads uses 1 socket = 6 channels.
    '''
    return channels * (bus_bits / 8) * freq_mhz * 1e6 * transfers / 1e9


# ---------------------------------------------------------------------------
# Test 1 — Hardware detection
# ---------------------------------------------------------------------------

@rfm.simple_test
class HardwareDetectTest(rfm.RunOnlyRegressionTest):
    '''Detect CPU and memory hardware on the actual compute node.

    Runs lscpu, dmidecode, and numactl. TheoreticalBWTest reads this
    output to compute peak bandwidth.
    '''

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    tags = {'hw', 'smoke', 'microbenchmark'}
    time_limit = '5m'
    executable = 'bash'

    @run_before('run')
    def write_detect_script(self):
        lines = [
            '#!/bin/bash',
            'set +e',
            '',
            'echo "=== lscpu ==="',
            'lscpu',
            'echo "=== dmidecode memory ==="',
            'dmidecode -t memory 2>/dev/null || echo "DMIDECODE_UNAVAILABLE"',
            'echo "=== numactl ==="',
            'numactl --hardware 2>/dev/null || echo "NUMACTL_UNAVAILABLE"',
            'echo "HW_DETECT_DONE"',
        ]
        script = os.path.join(self.stagedir, 'hw_detect.sh')
        with open(script, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.chmod(script, 0o755)
        self.executable_opts = [script]

    @sanity_function
    def validate(self):
        return sn.assert_found(r'HW_DETECT_DONE', self.stdout)


# ---------------------------------------------------------------------------
# Test 2 — Theoretical bandwidth calculator
# ---------------------------------------------------------------------------

@rfm.simple_test
class TheoreticalBWTest(rfm.RunOnlyRegressionTest):
    '''Compute theoretical peak memory bandwidth from hardware specs.

    Detection priority:
      1. dmidecode DIMM count  (most accurate — needs root/cap)
      2. CPU model string      (lookup table)
      3. User fallback values  (always succeeds)

    Verified for paramrudra.snbose (Gold 6240R):
      6 channels/socket, DDR4-2933
      Per-socket peak  = 281.6 GB/s
      Dual-socket peak = 563.2 GB/s
    '''

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    tags = {'hw', 'microbenchmark'}
    time_limit = '2m'

    # Fallback values tuned for paramrudra.snbose Gold 6240R
    fallback_channels = variable(int,   value=6,      loggable=True)
    fallback_freq_mhz = variable(float, value=2933.0, loggable=True)
    fallback_sockets  = variable(int,   value=2,      loggable=True)

    # Populated during parse_hw_output — do not set manually
    memory_channels  = variable(int,   value=0,      loggable=True)
    ddr_freq_mhz     = variable(float, value=0.0,    loggable=True)
    num_sockets      = variable(int,   value=0,      loggable=True)
    detection_method = variable(str,   value='none', loggable=True)

    executable      = 'echo'
    executable_opts = ['"TheoreticalBWTest"']

    @run_after('init')
    def set_dependency(self):
        self.depends_on('HardwareDetectTest', udeps.by_env)

    @run_before('sanity')
    def parse_hw_output(self):
        hw_test   = self.getdep('HardwareDetectTest')
        hw_stdout = os.path.join(
            hw_test.stagedir, sn.evaluate(hw_test.stdout)
        )

        if not os.path.exists(hw_stdout):
            self._apply_fallback('hw_output_not_found')
            return

        with open(hw_stdout) as f:
            content = f.read()

        # 1. Sockets from lscpu
        m = re.search(r'Socket\(s\):\s+(\d+)', content)
        self.num_sockets = int(m.group(1)) if m else self.fallback_sockets

        # 2. DDR frequency from dmidecode
        speeds = re.findall(
            r'(?:Configured Memory Speed|^Speed):\s+(\d+)\s+MT/s',
            content, re.MULTILINE
        )
        valid_speeds = [int(s) for s in speeds if int(s) > 0]
        if valid_speeds:
            self.ddr_freq_mhz = float(
                max(set(valid_speeds), key=valid_speeds.count)
            )

        # 3. Channels from dmidecode DIMM count
        if 'DMIDECODE_UNAVAILABLE' not in content:
            populated = re.findall(
                r'Size:\s+(?!No Module)(\d+\s+(?:GB|MB|TB))',
                content
            )
            if populated and self.num_sockets > 0:
                self.memory_channels  = len(populated) // self.num_sockets
                self.detection_method = 'dmidecode_dimm_count'

        # 4. CPU model lookup
        if self.memory_channels == 0:
            self._detect_from_cpu_model(content)

        # 5. Final fallback
        if self.memory_channels == 0:
            self._apply_fallback('no_cpu_match')

        if self.ddr_freq_mhz == 0.0:
            self.ddr_freq_mhz     = self.fallback_freq_mhz
            self.detection_method += '+freq_fallback'

    def _detect_from_cpu_model(self, content):
        cpu_map = [
            # Intel Cascade Lake (verified on paramrudra)
            (r'gold\s+6240r',              6, 2933, 'CascadeLake Gold 6240R'),
            (r'gold\s+6240\b',             6, 2933, 'CascadeLake Gold 6240'),
            (r'gold\s+6230r',              6, 2933, 'CascadeLake Gold 6230R'),
            (r'gold\s+62[0-9]{2}r?',       6, 2933, 'CascadeLake Gold 62xx'),
            (r'platinum\s+82[0-9]{2}',     6, 2933, 'CascadeLake Platinum'),
            (r'silver\s+42[0-9]{2}',       6, 2933, 'CascadeLake Silver'),
            # Intel Ice Lake
            (r'gold\s+6[3-9][0-9]{2}',     8, 3200, 'IceLake Gold'),
            (r'platinum\s+8[3-5][0-9]{2}', 8, 3200, 'IceLake Platinum'),
            # Intel Sapphire Rapids
            (r'platinum\s+8[4-9][0-9]{2}', 8, 4800, 'SapphireRapids Platinum'),
            (r'gold\s+6[4-9][0-9]{2}',     8, 4800, 'SapphireRapids Gold'),
            # Intel generic
            (r'cascadelake',               6, 2933, 'CascadeLake generic'),
            (r'icelake',                   8, 3200, 'IceLake generic'),
            (r'sapphirerapids',            8, 4800, 'SapphireRapids generic'),
            # AMD EPYC
            (r'epyc\s+9[0-9]{3}',         12, 4800, 'Genoa'),
            (r'epyc\s+7[5-9][0-9]{2}',     8, 3200, 'Milan'),
            (r'epyc\s+7[0-4][0-9]{2}',     8, 3200, 'Rome'),
            (r'epyc',                       8, 3200, 'EPYC generic'),
            # ARM
            (r'neoverse.?v2',              8, 4800, 'NeoV2'),
            (r'neoverse.?v1',              8, 3200, 'NeoV1'),
            (r'grace',                     8, 6400, 'Grace LPDDR5X'),
            (r'graviton3',                 8, 3200, 'Graviton3'),
        ]
        content_lower = content.lower()
        for pattern, channels, freq, label in cpu_map:
            if re.search(pattern, content_lower):
                self.memory_channels = channels
                if self.ddr_freq_mhz == 0.0:
                    self.ddr_freq_mhz = float(freq)
                self.detection_method = f'cpu_model_map:{label}'
                return

    def _apply_fallback(self, reason):
        self.memory_channels = self.fallback_channels
        if self.ddr_freq_mhz == 0.0:
            self.ddr_freq_mhz = self.fallback_freq_mhz
        if self.num_sockets == 0:
            self.num_sockets = self.fallback_sockets
        self.detection_method = f'fallback:{reason}'

    @performance_function('GB/s')
    def theoretical_peak_bw(self):
        '''Total theoretical peak across all sockets.'''
        return sn.defer(
            _theoretical_bw_gbs(self.memory_channels, self.ddr_freq_mhz)
            * max(self.num_sockets, 1)
        )

    @performance_function('GB/s')
    def theoretical_peak_bw_per_socket(self):
        '''Theoretical peak for one socket — reference for single-socket STREAM.'''
        return sn.defer(
            _theoretical_bw_gbs(self.memory_channels, self.ddr_freq_mhz)
        )

    @sanity_function
    def validate(self):
        return sn.assert_true(
            self.memory_channels > 0,
            msg=(
                f'Could not detect memory channels '
                f'(method={self.detection_method}). '
                f'Set via: -S TheoreticalBWTest.fallback_channels=6'
            )
        )


# ---------------------------------------------------------------------------
# Test 3 — STREAM benchmark
# ---------------------------------------------------------------------------

@rfm.simple_test
class StreamMultiSysTest(rfm.RegressionTest):
    '''STREAM memory bandwidth benchmark with auto-computed references.

    References are computed from theoretical peak x efficiency target —
    no hardcoded MB/s values needed. Automatically adapts to any hardware
    detected by TheoreticalBWTest.

    Formula:
        reference_MB_s = theoretical_per_socket_GB_s x target x 1000

    Example for Gold 6240R (281.6 GB/s per socket):
        Copy  ref = 281.6 x 0.65 x 1000 = 183,040 MB/s
        Triad ref = 281.6 x 0.56 x 1000 = 157,696 MB/s

    Test fails if any kernel drops >10% below its efficiency-derived reference.

    Measured on paramrudra.snbose (24 threads, 1 socket):
        Copy:  ~198000 MB/s (~70%)   Scale: ~143000 MB/s (~51%)
        Add:   ~165000 MB/s (~59%)   Triad: ~172000 MB/s (~61%)
    '''

    valid_systems = ['*']
    valid_prog_environs = ['gnu', 'intel']

    prebuild_cmds = [
        'wget -q https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c'
    ]
    build_system = 'SingleSource'
    sourcepath   = 'stream.c'
    tags = {'perf', 'memory', 'microbenchmark', 'stream'}
    time_limit   = '30m'

    # -------------------------------------------------------------------
    # Efficiency targets — reference = theoretical_per_socket x target.
    # Derived from measured values on Gold 6240R with -10% margin:
    #   Copy  measured ~70% → target 60%  (conservative)
    #   Scale measured ~51% → target 41%
    #   Add   measured ~59% → target 49%
    #   Triad measured ~61% → target 51%
    # Increase these once you have stable repeated measurements.
    # -------------------------------------------------------------------
    efficiency_targets = variable(dict, value={
        'Copy':  0.60,
        'Scale': 0.41,
        'Add':   0.49,
        'Triad': 0.51,
    })

    # Compiler flags per environment
    flags = variable(dict, value={
        'gnu':   ['-fopenmp', '-O3', '-march=native', '-Wall'],
        'intel': ['-qopenmp', '-O3', '-xHost',        '-Wall'],
        'foss':  ['-fopenmp', '-O3', '-march=native', '-Wall'],
    })

    # Physical cores per partition — 24 fills one socket on Gold 6240R
    cores = variable(dict, value={
        'paramrudra.snbose:login': 4,
        'paramrudra.snbose:cpu':   24,
        'paramrudra.snbose:hm':    24,
        'paramrudra.snbose:gpu':   24,
    })

    @run_after('init')
    def set_dependency(self):
        self.depends_on('TheoreticalBWTest', udeps.by_env)

    @run_before('compile')
    def set_compiler_flags(self):
        self.build_system.cppflags = [
            '-DSTREAM_ARRAY_SIZE=$((1 << 25))',
            '-DNTIMES=20',
        ]
        environ = self.current_environ.name
        self.build_system.cflags = self.flags.get(environ, ['-O3'])

    @run_before('run')
    def set_num_threads(self):
        num_threads = self.cores.get(self.current_partition.fullname, 4)
        self.num_cpus_per_task = num_threads
        self.env_vars = {
            'OMP_NUM_THREADS': str(num_threads),
            'OMP_PROC_BIND':   'close',
            'OMP_PLACES':      'cores',
        }

    # --- STREAM kernel extractors ---

    @performance_function('MB/s')
    def extract_bw(self, kind='Copy'):
        if kind not in {'Copy', 'Scale', 'Add', 'Triad'}:
            raise ValueError(f'illegal value in argument kind ({kind!r})')
        return sn.extractsingle(
            rf'{kind}:\s+(\S+)\s+.*', self.stdout, 1, float
        )

    # --- Efficiency metrics as performance functions ---
    # Using @performance_function keeps everything properly deferred —
    # ReFrame resolves these after the job output is available.

    @performance_function('%')
    def triad_efficiency_pct(self):
        '''Triad bandwidth as % of theoretical per-socket peak.'''
        bw_test  = self.getdep('TheoreticalBWTest')
        theo_mbs = _theoretical_bw_gbs(
            bw_test.memory_channels, bw_test.ddr_freq_mhz
        ) * 1000.0
        triad = sn.extractsingle(
            r'Triad:\s+(\S+)\s+.*', self.stdout, 1, float
        )
        return sn.defer(sn.evaluate(triad) / theo_mbs * 100.0)

    @performance_function('%')
    def copy_efficiency_pct(self):
        '''Copy bandwidth as % of theoretical per-socket peak.'''
        bw_test  = self.getdep('TheoreticalBWTest')
        theo_mbs = _theoretical_bw_gbs(
            bw_test.memory_channels, bw_test.ddr_freq_mhz
        ) * 1000.0
        copy = sn.extractsingle(
            r'Copy:\s+(\S+)\s+.*', self.stdout, 1, float
        )
        return sn.defer(sn.evaluate(copy) / theo_mbs * 100.0)

    @performance_function('GB/s')
    def theoretical_peak_per_socket_gbs(self):
        '''Per-socket theoretical peak logged alongside measured results.'''
        bw_test = self.getdep('TheoreticalBWTest')
        return sn.defer(
            _theoretical_bw_gbs(bw_test.memory_channels, bw_test.ddr_freq_mhz)
        )

    @run_before('performance')
    def set_perf_variables(self):
        '''Register all performance variables including auto-computed references.'''
        bw_test = self.getdep('TheoreticalBWTest')

        # Per-socket theoretical peak in MB/s
        theo_mbs = _theoretical_bw_gbs(
            bw_test.memory_channels,
            bw_test.ddr_freq_mhz,
        ) * 1000.0

        # Four STREAM kernels
        self.perf_variables = {
            'Copy':  self.extract_bw('Copy'),
            'Scale': self.extract_bw('Scale'),
            'Add':   self.extract_bw('Add'),
            'Triad': self.extract_bw('Triad'),
            # Derived metrics — informational, not compared against reference
            'triad_efficiency_pct':          self.triad_efficiency_pct(),
            'copy_efficiency_pct':           self.copy_efficiency_pct(),
            'theoretical_peak_per_socket_gbs': self.theoretical_peak_per_socket_gbs(),
        }

        # Build reference dict from efficiency targets x theoretical peak.
        # Only Copy/Scale/Add/Triad are compared — efficiency metrics are
        # informational only (no reference set for them).
        system_key = (
            f'{self.current_system.name}:{self.current_partition.name}'
        )
        self.reference = {
            system_key: {
                kernel: (
                    theo_mbs * target,   # reference value in MB/s
                    -0.10,               # fail if measured < reference x 0.90
                    None,                # no upper bound
                    'MB/s',
                )
                for kernel, target in self.efficiency_targets.items()
            }
        }

    @sanity_function
    def validate_solution(self):
        return sn.all([
            sn.assert_found(r'Solution Validates', self.stdout),
            sn.assert_not_found(r'FAILED', self.stdout),
        ])
