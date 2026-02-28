#!/bin/bash

# 用法:
# bash git.sh pull
# bash git.sh push

if [ "$1" = "pull" ]; then
    echo ">>> git pull"
    git pull origin main

elif [ "$1" = "push" ]; then
    echo ">>> git add"
    git add .

    echo ">>> git commit"
    git commit -m "first commit"

    echo ">>> set branch main"
    git branch -M main

    echo ">>> set remote"
    git remote add origin git@github.com:lizi-learn/battery_monitor.git 2>/dev/null

    echo ">>> git push"
    git push -u origin main

else
    echo "用法:"
    echo "bash git.sh pull"
    echo "bash git.sh push"
fi