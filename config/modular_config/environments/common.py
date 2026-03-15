environments = [
    {
        'name': 'foss',
        'cc': 'mpicc',
        'cxx': 'mpicxx',
        'ftn': 'mpif90',
        'modules': ['intel-oneapi-mpi/izwlzk5'],
        'target_systems': ['paramrudra.snbose'],
    },
    {
        'name': 'gnu',
        'cc': 'gcc',
        'cxx': 'g++',
        'ftn': 'gfortran',
        'modules': ['openmpi@4.1.6/daxqcla'],
    },
    {
        'name': 'intel',
        'modules': ['intel-oneapi-compilers/72dzcki'],
        'cc': 'icc',
        'cxx': 'icpc',
        'ftn': 'ifort'
    },
    {
        'name': 'spack-only',
        'cc': 'gcc',
        'cxx': 'g++',
        'ftn': 'gfortran',
        'modules': [],
    },
]
