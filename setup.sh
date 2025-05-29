# This files include all the intional requirement of the framwork

#Intinalize spack and load reframe 
source /home/apps/SPACK/spack/share/spack/setup-env.sh
#spack load reframe
spack load reframe@4.7.3
#Enabling auto-completion for refarme 
source /home/apps/SPACK/spack/opt/spack/linux-almalinux8-cascadelake/gcc-13.2.0/reframe-4.0.4-dwsezsgnraoadbyfzrdzygco5ghqeexv/share/completions/reframe.bash 

#Set the paths for Input filse, Test Files, System Setting Files
export RFM_CONFIG_PATH=$(pwd)/config/IUAC_spack #:$(pwd)/config/IUAC_module
