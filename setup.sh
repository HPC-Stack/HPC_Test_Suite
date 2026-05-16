# This files include all the intional requirement of the framwork

#Intinalize spack and load reframe 
source /home/apps/spack/share/spack/setup-env.sh
#spack load reframe
spack load reframe@4.7.3
#Enabling auto-completion for refarme 
source /home/apps/spack/opt/spack/linux-almalinux8-cascadelake/gcc-13.2.0/reframe-4.7.3-cr5giu3pqks37s6dazqrnfq2q7s55rga/share/completions/reframe.bash 

#Set the paths for Input filse, Test Files, System Setting Files
export RFM_CONFIG_FILES=/home/cdacapp01/HPC_Test_Suite/config/common/settings.py:/home/cdacapp01/HPC_Test_Suite/config/environments/settings.py:/home/cdacapp01/HPC_Test_Suite/config/pseudo-cluster/settings.py
export RFM_CHECK_SEARCH_PATH=$(pwd)
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true
#/scratch/$USER/reframe/perflogs

##################################################
# #LLM SETUP
# source /home/apps/spack/share/spack/setup-env.sh
# spack load gcc@12/67zlogn
# spack load nvhpc/tdc6iex
# export CUDA_HOME=/home/apps/spack/opt/spack/linux-almalinux8-cascadelake/gcc-13.2.0/nvhpc-24.5-tdc6iexttubxc42znfv3hxpeoq2wiab7/Linux_x86_64/24.5/cuda/12.4/
# source /home/apps/MLDL/DL-CondaPy3/bin/activate
# #conda create -n vllm_py311 python=3.11 -y
# conda activate vllm_py311
# #pip install vllm==0.19.0
# pip install transformers>=4.51.0