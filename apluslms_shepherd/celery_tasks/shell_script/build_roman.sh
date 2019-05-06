#!/usr/bin/env bash
# Update from git origin and move to dir.
base=$1
course=$2
branch=$3

cd ${base}/builds/${course}/${branch}
roman
