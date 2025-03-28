#!/bin/bash

# 起動してから600秒以上経過した chromedriver headless_shell python3
# プロセスをKillして、ゾンビプロセスが大量に残ることを防止する

declare -a ProcessNameList=(chrome chromedriver headless_shell python3)
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

echo "Delete Chrome Cache Directory."
rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*
