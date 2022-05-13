#!/bin/bash

# Bash wrapper to set environment and launch script for the smartscope worker
echo 'Setting smartscope environment'
set -a
. "${SMARTSCOPE_DIR}/conf.env"
set +a
# source activate "$CONDA_ENV"
smartscope.py "$@"
