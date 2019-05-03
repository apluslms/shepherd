#!/usr/bin/env bash
# Update from git origin and move to dir.
base=$1
dir=$2
git_origin=$3
branch=$4
course=$5


cd ${base}
if [ -d $dir ]; then
  echo "Local repo found, fetching updates"
  cd ${dir}
  git fetch origin ${branch}:${branch}
else
  echo "No local repo"
  git clone --bare ${git_origin}
  cd ${dir}
fi
#git --no-pager log --pretty=format:"------------;Commit metadata;;Hash:;%H;Subject:;%s;Body:;%b;Committer:;%ai;%ae;Author:;%ci;%cn;%ce;------------;" -1 | tr ';' '\n'
git worktree add -f ../builds/${course}/${branch} ${branch}
cd ../builds/${course}/${branch}
git pull
git reset --hard HEAD
git submodule init && git submodule update
