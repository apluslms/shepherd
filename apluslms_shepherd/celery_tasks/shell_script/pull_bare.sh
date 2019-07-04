#!/bin/sh
# Update from git origin and move to dir.
base=$1
dir=$2
git_origin=$3
branch=$4
course=$5
instance=$6
build_number=$7
private_key=$8

cd $base
if [ -d $dir ]; then
  echo "Local repo found, fetching updates"
  cd $dir
  if [ -z "$8" ]
  then
          git fetch origin $branch:$branch
  else
    echo"Found local private key"
    ssh-agent sh -c "ssh-add $private_key; git fetch origin $branch:$branch"

  fi
  res=$?
  if [ $res -ne 0 ] ; then
    exit $res
    fi
else
  echo "No local repo found, cloning the repo from remote."
  if [ -z "$8" ]
  then
    git clone --bare $git_origin
  else
    echo"Found local private key"
    ssh-agent sh -c "ssh-add $private_key; git clone --bare $git_origin"
  fi
  res=$?
   if [ $res -ne 0 ] ; then
     echo "Clone failed, error."
    exit $res
  fi
  cd $dir
   res=$?
   if [ $res -ne 0 ] ; then
     echo "No local repo after git clone operation, error."
    exit $res
  fi
fi
echo 'Generating worktree'
#git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
git worktree add -f ../builds/$course/$instance/$build_number $branch
cd ../builds/$course/$instance/$build_number
git submodule init && git submodule update --depth 1
