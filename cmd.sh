#!/bin/bash
while [ "1" = "1" ]
do
    for args in $@
    do
      echo "Printed by cmd.sh" $args 
    done
sleep 5
done
