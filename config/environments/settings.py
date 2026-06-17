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
            'modules': ['openmpi/h34jdpb'],
            'target_systems': ['paramrudra.cdacb'],
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
            'modules': ['intel-oneapi-compilers/t7vsoln'],
        },
        {
            'name': 'nvhpc',
            'cc': 'nvc',
            'cxx': 'nvcc',
            'ftn': 'nvfortran',
            'modules': ['nvhpc/n62w34u'],
            
        }
    ],
}