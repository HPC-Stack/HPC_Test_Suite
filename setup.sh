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
