#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_error=./repos/annotations/annotation_json/error_annotations.json
filepath_activity=./repos/annotations/annotation_json/complete_step_annotations.json
filepath_step=./repos/annotations/annotation_json/activity_idx_step_idx.json
dirpath_graph=./repos/annotations/task_graphs/
dirpath_output=./data/preprocess/
dirpath_log=./log/

# preprocess error annotation of captaincook4d
python src/preprocess/update_annotation.py \
    --filepath_error "$filepath_error" \
    --filepath_activity "$filepath_activity" \
    --filepath_step "$filepath_step" \
    --dirpath_graph "$dirpath_graph" \
    --dirpath_output "$dirpath_output" \
    --dirpath_log "$dirpath_log"
