#!/bin/bash
# Update from git origin and move to dir.
base=$1
course=$2
branch=$3
build_number=$4
file_name=$5

cd ${base}builds/${course}/${branch}/${build_number}
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error"
fi
if [ -z $file_name ] || [ $file_name -e "course.yml" ]; then
    roman
else
    echo "Roman with file name"
    roman -f $file_name
fi
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error"
fi
exit $retVal