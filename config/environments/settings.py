# config/multifile/environments/settings.py
# Programming environments available across all systems.
# Add new compilers/toolchains here; target_systems scopes them.

site_configuration = {
    'environments': [
        {
            'name': 'foss',
            'cc':  'mpicc',
            'cxx': 'mpicxx',
            'ftn': 'mpif90',
            'modules': ['openmpi/daxqcla'],
            'target_systems': ['paramrudra.snbose'],
        },
        {
            'name': 'gnu',
            'cc':  'gcc',
            'cxx': 'g++',
            'ftn': 'gfortran',
            'modules': ['openmpi@4.1.6/daxqcla'],
            # No target_systems = available on all systems
        },
        {
            'name': 'intel',
            'cc':  'icc',
            'cxx': 'icpc',
            'ftn': 'ifort',
            'modules': ['intel-oneapi-compilers/72dzcki'],
        },
        {
            'name': 'spack-only',
            'cc':  'gcc',
            'cxx': 'g++',
            'ftn': 'gfortran',
            'modules': [],
            # Used when Spack environment is activated externally
        },
    ],
}