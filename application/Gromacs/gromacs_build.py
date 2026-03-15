import reframe as rfm
import reframe.utility.sanity as sn

@rfm.simple_test
class GromacsBuildTest(rfm.RegressionTest):
    descr = 'Build Gromacs using Spack'
    valid_systems = ['paramrudra.snbose:cpu']
    valid_prog_environs = ['gnu']
    
    # Use Spack build system
    build_system = 'Spack'
    
    @run_before('compile')
    def setup_build(self):
        self.build_system.specs = ['gromacs@2024.2']
        # You can add variants here
        # self.build_system.specs = ['gromacs@2024.2 +mpi +cuda']
        
    executable = 'gmx_mpi'
    executable_opts = ['--version']
    
    @sanity_function
    def validate_build(self):
        return sn.assert_found(r'GROMACS', self.stdout)
