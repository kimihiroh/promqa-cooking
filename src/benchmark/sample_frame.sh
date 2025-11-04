#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

# preprocess videos
dirpath_input=$1/gopro/resolution_4k/
dirpath_output=$2
dirpath_log=./log/

mkdir -p $dirpath_log

max_parallel_jobs=1

# note: sample frames from all recordings

echo "Start video resizing: $(date)"
python src/benchmark/sample_frame.py \
    --dirpath_input "$dirpath_input" \
    --dirpath_output "$dirpath_output" \
    --max_parallel_jobs $max_parallel_jobs \
    --dirpath_log $dirpath_log
echo "Finish video resizing: $(date)"
