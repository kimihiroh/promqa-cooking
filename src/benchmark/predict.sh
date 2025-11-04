#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_input=./data/$1
filepath_recipe=./data/graphs.json
dirpath_image=$2
dirpath_output=./output/prediction/
dirpath_log=./log

model_id=$3
max_frames=20

python src/benchmark/predict.py \
    --filepath_input "$filepath_input" \
    --filepath_recipe "$filepath_recipe" \
    --dirpath_image "$dirpath_image" \
    --dirpath_output "$dirpath_output" \
    --model_id "$model_id" \
    --max_frames "$max_frames" \
    --dirpath_log "$dirpath_log"
