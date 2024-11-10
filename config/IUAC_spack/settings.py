# Copyright 2016-2022 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

#
# Generic fallback configuration
#
import os

site_configuration = {
    'systems': [
        {
            'name': 'paramrudra.iuac',
            'descr': 'paramrudra.iuac system',
            'hostnames': ['.*'],
            'modules_system': 'spack',
            'resourcesdir': "/home/apps/hpc_inputs/",
            'stagedir': f'/scratch/{os.environ.get("USER")}/stage',
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
                            'options': ['--mem={size}', '--time=10:00:00']
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
                            'options': ['--mem={size}', '--time=10:00:00']
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
                            'options': ['--mem={size}', '--time=10:00:00']
                        }
                    ]
                },
                {
                     'name': 'gpu',
                     'descr': 'gpu nodes',
                     'modules': ['cuda@11.8.0/lcr74pg'],
                     'scheduler': 'slurm',
                     'launcher': 'srun',
                     'access': ['--partition=gpu','--gres=gpu:2', '--time=10:00:00'],
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
            'modules' : ['intel-oneapi-mpi/izwlzk5'],
            'target_systems': ['paramrudra.iuac'],
        },
        {
            'name': 'gnu',
            'cc': 'gcc',
            'cxx': 'g++',
            'ftn': 'gfortran',
        },
        {
            'name': 'intel',
            'modules': ['intel-oneapi-compilers/72dzcki'],
            'cc': 'icc',
            'cxx': 'icpc',
            'ftn': 'ifort'
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
                    'level': 'debug2',
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
    'general': [
        {
            'check_search_path': ['./application', './basics'],
            'check_search_recursive': True,
            'remote_detect': True,
            'purge_environment': True,
            'report_file': "./reports/run-report-{sessionid}.json"   
        }
    ]    
}
