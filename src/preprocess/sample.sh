#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_input=./data/preprocess/all_examples.json
dirpath_output=./data/preprocess/
dirpath_log=./log/

python src/preprocess/sample.py \
    --filepath_input "$filepath_input" \
    --dirpath_output "$dirpath_output" \
    --dirpath_log "$dirpath_log" \
