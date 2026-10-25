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
        },
        {
            'name': 'gnu',
            'cc':  'gcc',
            'cxx': 'g++',
            'ftn': 'gfortran',
            # No target_systems = available on all systems
        },
        {
            'name': 'intel',
            'cc':  'icc',
            'cxx': 'icpc',
            'ftn': 'ifort',
        },
        {
            'name': 'nvhpc',
            'cc': 'nvc',
            'cxx': 'nvcc',
            'ftn': 'nvfortran',           
        }
    ],
}