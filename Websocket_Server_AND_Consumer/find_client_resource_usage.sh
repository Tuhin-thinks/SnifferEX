#!/bin/bash

programCommand=$1

while true; do
    clear
    ps aux | grep "$programCommand" | grep -v grep | awk '{cpu+=$3; mem+=$4; count++} END {print "Matches: " count " | CPU: " cpu "% | MEM: " mem "%"}'
    
    sleep 1
done