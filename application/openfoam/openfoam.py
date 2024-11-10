import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import sys

def parse_time_cmd(s):	
    """ Convert timing info from `time` into float seconds.	
       E.g. parse_time('0m0.000s') -> 0.0	
    """	
    
    s = s.strip()
    mins, _, secs = s.partition('m')	
    mins = float(mins)	
    secs = float(secs.rstrip('s'))	

    return mins * 60.0 + secs

@rfm.simple_test
class openfoamTest(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs openfoam'
    valid_systems = ['paramrudra.iuac:cpu']
    valid_prog_environs = ['gnu']
    num_tasks = 96
    num_tasks_per_node = 48
    modules = ['openfoam/ggn7wsm','intel-oneapi-mpi/3alw73q']
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'OMP_NUM_THREADS': '1'
    }
    prerun_cmds = [
            'tar --strip-components 2 -xf Motorbike_bench_template.tar.gz bench_template/basecase',
            './Allclean', # removes logs, old timehistories etc just in case 
            
            # set domain decomposition:
            # using 'scotch' method means simpleCoeffs is ignored so it doesn't need to match num_tasks:
            'sed -i -- "s/method .*/method          scotch;/g" system/decomposeParDict',
            'sed -i -- "s/numberOfSubdomains .*/numberOfSubdomains %i;/g" system/decomposeParDict' % num_tasks,

            # remove streamlines:
            'sed -i -- \'s/    #include "streamLines"//g\' system/controlDict',
            'sed -i -- \'s/    #include "wallBoundedStreamLines"//g\' system/controlDict',

            # fix location of mesh quality defaults (needed for v6+?)
            "sed -i -- 's|caseDicts|caseDicts/mesh/generation|' system/meshQualityDict",

            './Allmesh', # do meshing

            'time \\', # want to run mpi task under time
        ]

    executable = 'simpleFoam'
    executable_opts = ["-parallel"]
    keep_files = ['log.snappyHexMesh', 'log.blockMesh', 'log.decomposePar']
    
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='ExecutionTime')
    def extract_ExecutionTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 1, float)[-1]

    @performance_function('s', perf_key='ClockTime')
    def extract_ClockTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 2, float)[-1]

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)


@rfm.simple_test
class openfoamTestNew(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs openfoam'
    np = parameter([48,96,192,384,768,1536,3072])
    valid_systems = ['paramrudra.iuac:cpu']
    valid_prog_environs = ['gnu']
    num_tasks_per_node = 48
    modules = ['openfoam/ggn7wsm','intel-oneapi-mpi/3alw73q']
    sourcesdir = 'src'
    exclusive_access = True
   

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.np
        if self.num_tasks == 1:
            self.executable_opts = [""]
        else:
            self.executable_opts = ["-parallel"]
        self.prerun_cmds = [
            'tar -xzvf  openfoam_data.tar.gz',
            'cd OpenFOAM_data',
            
            # set domain decomposition:
            # using 'scotch' method means simpleCoeffs is ignored so it doesn't need to match num_tasks:
            'sed -i -- "s/method .*/method          scotch;/g" system/decomposeParDict',
            'sed -i -- "s/numberOfSubdomains .*/numberOfSubdomains %i;/g" system/decomposeParDict' % self.num_tasks,

            'rm -rf processor*', # removes logs, old timehistories etc just in case 
            'decomposePar',
            
            # remove streamlines:
            #'sed -i -- \'s/    #include "streamLines"//g\' system/controlDict',
            #'sed -i -- \'s/    #include "wallBoundedStreamLines"//g\' system/controlDict',

            # fix location of mesh quality defaults (needed for v6+?)
            #"sed -i -- 's|caseDicts|caseDicts/mesh/generation|' system/meshQualityDict -overwrite",

            #'./Allmesh', # do meshing

            'time \\', # want to run mpi task under time
        ]
    
    reference = {
        '*': {
            'ExecutionTime': (0, None, None, 's'),
            'ClockTime': (0, None, None, 's'),
            'runtime_real': (0, None, None, 's'),
        }
    }

    executable = 'sonicFoam'
    keep_files = ['log.snappyHexMesh', 'log.blockMesh', 'log.decomposePar']

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()
       

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='ExecutionTime')
    def extract_ExecutionTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 1, float)[-1]

    @performance_function('s', perf_key='ClockTime')
    def extract_ClockTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 2, float)[-1]

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)

@rfm.simple_test
class openfoamTest_para(rfm.RunOnlyRegressionTest):
    descr = 'A test that runs openfoam'
    np = parameter([48,96,192,384])
    valid_systems = ['kamrupa:cpu']
    valid_prog_environs = ['openfoam']
    num_tasks_per_node = 48
    sourcesdir = 'src'
    exclusive_access = True
    env_vars = {
        'OMP_NUM_THREADS': '20'
    }

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.np
        if self.num_tasks == 1:
            self.executable_opts = [""]
        else:
            self.executable_opts = ["-parallel"]
        self.prerun_cmds = [
            'tar --strip-components 2 -xf Motorbike_bench_template.tar.gz bench_template/basecase',
            './Allclean', # removes logs, old timehistories etc just in case 
            
            # set domain decomposition:
            # using 'scotch' method means simpleCoeffs is ignored so it doesn't need to match num_tasks:
            'sed -i -- "s/method .*/method          scotch;/g" system/decomposeParDict',
            'sed -i -- "s/numberOfSubdomains .*/numberOfSubdomains %i;/g" system/decomposeParDict' % self.num_tasks,

            # remove streamlines:
            'sed -i -- \'s/    #include "streamLines"//g\' system/controlDict',
            'sed -i -- \'s/    #include "wallBoundedStreamLines"//g\' system/controlDict',

            # fix location of mesh quality defaults (needed for v6+?)
            "sed -i -- 's|caseDicts|caseDicts/mesh/generation|' system/meshQualityDict -overwrite",

            './Allmesh', # do meshing

            'time \\', # want to run mpi task under time
        ]
    
    reference = {
        '*': {
            'ExecutionTime': (0, None, None, 's'),
            'ClockTime': (0, None, None, 's'),
            'runtime_real': (0, None, None, 's'),
        }
    }

    executable = 'simpleFoam'
    # executable_opts = ["-parallel"]
    keep_files = ['log.snappyHexMesh', 'log.blockMesh', 'log.decomposePar']

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()
       

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='ExecutionTime')
    def extract_ExecutionTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 1, float)[-1]

    @performance_function('s', perf_key='ClockTime')
    def extract_ClockTime(self):
        return sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 2, float)[-1]

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)