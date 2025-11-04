#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_input=./data/preprocess/$1
filepath_template=src/qa-generation/templates.yaml
dirpath_recipe_image=./data/preprocess/graphs/raw/
dirpath_output=./data/generation/
filepath_graph=./data/preprocess/all_graphs.json
dirpath_log=./log/

model_id=gpt-4o-2024-08-06
template_type=step-target

python src/qa-generation/run.py \
    --filepath_input "$filepath_input" \
    --filepath_template "$filepath_template" \
    --filepath_graph "$filepath_graph" \
    --dirpath_recipe_image "$dirpath_recipe_image" \
    --dirpath_output "$dirpath_output" \
    --model_id "$model_id" \
    --template_type "$template_type" \
    --dirpath_log "$dirpath_log"
