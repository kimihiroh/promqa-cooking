#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_recipe=./data/graphs.json
filepath_template=./src/benchmark/templates.yaml
dirpath_output=./output/evaluation/
dirpath_log=./log

model_id=gpt-4o-2024-08-06
template_type=ternary-step

filepath_input=./output/prediction/$1

python src/benchmark/evaluate.py \
    --filepath_input "$filepath_input" \
    --filepath_recipe "$filepath_recipe" \
    --filepath_template "$filepath_template" \
    --dirpath_output "$dirpath_output" \
    --template_type "$template_type" \
    --model_id "$model_id" \
    --dirpath_log "$dirpath_log"
