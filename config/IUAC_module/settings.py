# Copyright 2016-2022 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

#
# Generic fallback configuration
#

site_configuration = {
    'systems': [
        {
            'name': 'paramrudra.iuac',
            'descr': 'paramrudra.iuac system',
            'hostnames': ['.*'],
            'modules_system': 'lmod',
            'partitions': [
                {
                    'name': 'login',
                    'scheduler': 'local',
                    'launcher': 'local',
                    'environs': ['gnu','intel']
                },
                {
                    'name': 'standard',
                    'descr': 'standard nodes',
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=standard'],
                    'environs': ['gnu', 'intel'],
                    'max_jobs': 100,
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}']
                        }
                    ]
                },
                {
                    'name': 'cpu',
                    'descr': 'cpu nodes',
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=cpu'],
                    'environs': ['gnu', 'intel','foss'],
                    'max_jobs': 100,
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}']
                        }
                    ]
                },
                {
                    'name': 'hm',
                    'descr': 'hm nodes',
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=hm'],
                    'environs': ['gnu', 'intel'],
                    'max_jobs': 100,
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}']
                        }
                    ]
                },
                {
                     'name': 'gpu',
                     'descr': 'gpu nodes',
                     'modules': ['cuda@11.8.0/6tjefbp'],
                     'scheduler': 'slurm',
                     'launcher': 'srun',
                     'access': ['--partition=gpu','--gres=gpu:2'],
                     'environs': ['gnu', 'intel'],
                     'max_jobs': 100,
                     'resources': [
                         {
                             'name': 'memory',
                             'options': ['--mem={size}']
                         }
                     ]
                 },
            ]
        },
    ],
    'environments': [
        {
            'name': 'foss',
            'cc': 'mpicc',
            'cxx': 'mpicxx',
            'ftn': 'mpif90',
            'modules' : ['openmpi/5.0.2'],
            'target_systems': ['paramrudra.iuac'],
        },
        {
            'name': 'gnu',
            'cc': 'gcc',
            'cxx': 'g++',
            'ftn': 'gfortran',
            'target_systems': ['paramrudra.iuac'],
        },
        {
            'name': 'intel',
            'modules': ['compiler/oneapi-2024/compiler/latest'],
            'cc': 'icc',
            'cxx': 'icpc',
            'ftn': 'ifort',
            'target_systems': ['paramrudra.iuac'],
        },
    ],
    'logging': [
        {
            'handlers': [
                {
                    'type': 'stream',
                    'name': 'stdout',
                    'level': 'info',
                    'format': '%(message)s'
                },
                {
                    'type': 'file',
                    'level': 'debug',
                    'format': '[%(asctime)s] %(levelname)s: %(check_info)s: %(message)s',   # noqa: E501
                    'append': False
                }
            ],
            'handlers_perflog': [
                {
                    'type': 'filelog',
                    'prefix': '%(check_system)s/%(check_partition)s',
                    'level': 'info',
                    'format': (
                        '%(check_job_completion_time)s,reframe %(version)s,'
                        '%(check_info)s,jobid=%(check_jobid)s,'
                        '%(check_perf_var)s=%(check_perf_value)s,'
                        'num_tasks=%(check_num_tasks)s,'
                        'num_tasks_per_node=%(check_num_tasks_per_node)s,'
                        'ref=%(check_perf_ref)s '
                        '(l=%(check_perf_lower_thres)s,'
                        'u=%(check_perf_upper_thres)s),'
                        '%(check_perf_unit)s'
                    ),
                    'append': True
                }
            ]
        }
    ],
}
