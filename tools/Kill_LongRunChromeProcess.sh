#!/bin/bash

declare -a ProcessNameList=(chromedriver headless_shell python3)
PID=$$
CurrentTime=$(date +%s)

for process in "${ProcessNameList[@]}"
do
  echo "ProcessName: ${process}"
  for i in $(pgrep ${process})
  do
    TIME=$(ps -o lstart --noheader -p ${i})
    if [ -n "${TIME}" ]; then
      StartupTime=$(date +%s -d "${TIME}")
      ElapsedTime=$(expr ${CurrentTime} - ${StartupTime})
    else
      ElapsedTime=1
    fi
    if [ ${ElapsedTime} -gt 600 ]; then
      kill ${i}
    else
      echo "Not kill ${i}"
    fi
  done
done
