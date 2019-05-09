#!/bin/sh
# Update from git origin and move to dir.
base=$1
course=$2
branch=$3
build_number=$4

cd ${base}builds/${course}/${branch}/${build_number}
res=$?
if [ $res -ne 0 ] ; then
    echo "Roman Error. Folder not found"
    exit $res
fi
roman
res=$?
if [ $res -ne 0 ] ; then
    echo "Roman Error."
    exit $res
fi