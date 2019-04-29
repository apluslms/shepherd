#!/usr/bin/env bash
# Update from git origin and move to dir.
dir=$1
git_origin=$2
branch=$3

if [ -d $dir ]; then
  cd $dir
  git fetch
  # Following trick might not be needed. It's supposed to ensure there is local branch per remote
  branch_now=`git branch`
  if [ "${branch_now#* }" != "$branch" ]; then
    echo "The "
    git reset -q --hard
    git checkout -q $branch
  fi
  git reset -q --hard origin/$branch
  git submodule update --init --recursive
  #git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
else
  git clone -b $branch --recursive $git_origin $dir
  cd $dir
fi