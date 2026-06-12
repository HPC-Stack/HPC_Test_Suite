import os
import subprocess
import sys

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture


@rfm.simple_test
class GromacsBuildTest(rfm.CompileOnlyRegressionTest):
    descr = 'Build GROMACS with Spack'
    
    build_system = 'Spack'
    local = True

    spack_spec = variable(
        str,
        value='gromacs +cuda cuda_arch=80 ^openmpi+cuda schedulers=slurm'
    )

    @run_before('compile')
    def setup_build(self):
        self.build_system.specs = [self.spack_spec]

    @sanity_function
    def validate_build(self):
        return sn.assert_true(True)


_BENCHMARKS = [
    ('HECBioSim/Crambin', -204107.0, 0.001),
    ('HECBioSim/Glutamine-Binding-Protein', -724598.0, 0.001),
    ('HECBioSim/hEGFRDimer', -3.32892e+06, 0.001),
    ('HECBioSim/hEGFRDimerSmallerPL', -3.27080e+06, 0.001),
    ('HECBioSim/hEGFRDimerPair', -1.20733e+07, 0.001),
    ('HECBioSim/hEGFRtetramerPair', -2.09831e+07, 0.001),
]


@rfm.simple_test
class GromacsBenchmark(rfm.RunOnlyRegressionTest):
    
    tags = {'sciapp', 'gromacs'}

    benchmark_info = parameter(_BENCHMARKS, fmt=lambda x: x[0], loggable=True)
    nb_impl = parameter(['cpu', 'gpu'], loggable=True)

    executable = 'gmx_mpi'
    keep_files = ['md.log']
    time_limit = '60m'
    exclusive_access = True

    build = fixture(GromacsBuildTest, scope='environment')

    @run_after('init')
    def prepare_test(self):
        name, nrg_ref, nrg_tol = self.benchmark_info
        self.descr = f'GROMACS {name} (NB: {self.nb_impl})'
        self._nrg_ref = nrg_ref
        self._nrg_tol = nrg_tol
        self.executable_opts = ['mdrun', '-nb', self.nb_impl, '-s', 'benchmark.tpr']
        if self.nb_impl == 'gpu':
            self.num_gpus_per_node = 1

    @run_before('run')
    def set_mpirun_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def download_input(self):
        name = self.benchmark_info[0]
        url = f'https://github.com/victorusu/GROMACS_Benchmark_Suite/raw/1.0.0/{name}/benchmark.tpr'
        tpr_path = os.path.join(self.stagedir, 'benchmark.tpr')
        if not os.path.exists(tpr_path):
            subprocess.run(['curl', '-fL', url, '-o', tpr_path], check=True, timeout=900)

    @run_before('run')
    def load_spack_env(self):
        spack_env = os.path.join(self.build.stagedir, 'rfm_spack_env')
        spec = self.build.spack_spec
        self.prerun_cmds = [
            f'eval `spack -e {spack_env} load --sh {spec}`',
            'which gmx_mpi',
        ]

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @performance_function('ns/day')
    def perf(self):
        return sn.extractsingle(
            r'Performance:\s+(?P<perf>\S+)',
            'md.log', 'perf', float
        )

    @sanity_function
    def assert_energy_readout(self):
        energy = sn.extractsingle(
            r'\s+Potential\s+Kinetic En\.\s+Total Energy'
            r'\s+Conserved En\.\s+Temperature\n'
            r'(\s+\S+){2}\s+(?P<energy>\S+)(\s+\S+){2}\n'
            r'\s+Pressure \(bar\)\s+Constr\. rmsd',
            'md.log', 'energy', float, item=-1
        )
        return sn.all([
            sn.assert_found('Finished mdrun', 'md.log'),
            sn.assert_reference(
                energy, self._nrg_ref,
                -self._nrg_tol, self._nrg_tol
            ),
        ])


@rfm.simple_test
class GromacsStrongScalingBenchmark(rfm.RunOnlyRegressionTest):
    
    tags = {'sciapp', 'gromacs', 'strongscaling'}

    benchmark_info = parameter(_BENCHMARKS, fmt=lambda x: x[0], loggable=True)
    nb_impl = parameter(['cpu', 'gpu'], loggable=True)
    num_nodes = parameter([1, 2, 4, 8])

    executable = 'gmx_mpi'
    keep_files = ['md.log']
    time_limit = '120m'
    exclusive_access = True

    build = fixture(GromacsBuildTest, scope='environment')

    @run_after('init')
    def prepare_test(self):
        name, nrg_ref, nrg_tol = self.benchmark_info
        self.descr = f'GROMACS {name} strong-scaling {self.num_nodes} (NB: {self.nb_impl})'
        self._nrg_ref = nrg_ref
        self._nrg_tol = nrg_tol
        self.executable_opts = ['mdrun', '-nb', self.nb_impl, '-s', 'benchmark.tpr']
        if self.nb_impl == 'gpu':
            self.num_gpus_per_node = 2

    @run_after('init')
    def set_tasks(self):
        self.num_tasks = self.num_nodes * self.num_tasks_per_node

    @run_before('run')
    def set_mpirun_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def download_input(self):
        name = self.benchmark_info[0]
        url = f'https://github.com/victorusu/GROMACS_Benchmark_Suite/raw/1.0.0/{name}/benchmark.tpr'
        tpr_path = os.path.join(self.stagedir, 'benchmark.tpr')
        if not os.path.exists(tpr_path):
            subprocess.run(['curl', '-fL', url, '-o', tpr_path], check=True, timeout=900)

    @run_before('run')
    def load_spack_env(self):
        spack_env = os.path.join(self.build.stagedir, 'rfm_spack_env')
        spec = self.build.spack_spec
        self.prerun_cmds = [
            f'eval `spack -e {spack_env} load --sh {spec}`',
            'which gmx_mpi',
        ]

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @performance_function('ns/day')
    def perf(self):
        return sn.extractsingle(
            r'Performance:\s+(?P<perf>\S+)',
            'md.log', 'perf', float
        )

    @sanity_function
    def assert_energy_readout(self):
        energy = sn.extractsingle(
            r'\s+Potential\s+Kinetic En\.\s+Total Energy'
            r'\s+Conserved En\.\s+Temperature\n'
            r'(\s+\S+){2}\s+(?P<energy>\S+)(\s+\S+){2}\n'
            r'\s+Pressure \(bar\)\s+Constr\. rmsd',
            'md.log', 'energy', float, item=-1
        )
        return sn.all([
            sn.assert_found('Finished mdrun', 'md.log'),
            sn.assert_reference(
                energy, self._nrg_ref,
                -self._nrg_tol, self._nrg_tol
            ),
        ])
