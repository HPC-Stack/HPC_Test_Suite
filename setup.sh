# This files include all the intional requirement of the framwork

#Intinalize spack and load reframe 
source /home/apps/spack/share/spack/setup-env.sh
#spack load reframe
spack load reframe@4.7.3
#Enabling auto-completion for refarme 
source /home/apps/spack/opt/spack/linux-almalinux8-cascadelake/gcc-13.2.0/reframe-4.7.3-cr5giu3pqks37s6dazqrnfq2q7s55rga/share/completions/reframe.bash 

#Set the paths for Input filse, Test Files, System Setting Files
export RFM_CONFIG_PATH=$(pwd)/config/modular_config
export RFM_OUTPUT_DIR=/scratch/$USER/output
export RFM_STAGE_DIR=/scratch/$USER/stage
export RFM_PERFLOG_DIR=/scratch/$USER/perflogs
export RFM_CHECK_SEARCH_PATH=$(pwd)
export RFM_CHECK_SEARCH_RECURSIVE=yes

