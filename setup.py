from setuptools import setup, find_packages

setup(
    name="continusbench",
    version="1.0.0",
    description="Continus Bench — Continuous benchmarking and regression analysis for HPC systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="HPC Tech Team CDAC",
    packages=find_packages(include=["continuousbench", "continuousbench.*", "bin", "bin.*"]),
    python_requires=">=3.7",
    install_requires=[
        "typer>=0.4.0",
        "questionary>=1.10.0",
        "pyyaml>=5.1",
        "reframe-hpc>=4.7.3",
    ],
    extras_require={
        "reporting": ["jinja2>=3.0", "matplotlib>=3.0", "plotly>=5.0"],
    },
    entry_points={
        "console_scripts": [
            "continusbench=continuousbench.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Distributed Computing",
        "Topic :: Scientific/Engineering",
    ],
)
