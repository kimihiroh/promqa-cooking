#!/usr/bin/bash

eval "$(conda shell.bash hook)"
conda activate promqa-cooking

filepath_input=./data/preprocess/original_updated.json
filepath_verbs=./data/preprocess/error_type_to_verbs.json
dirpath_graph=./repos/annotations/task_graphs/
filepath_metadata_video=./repos/downloader/metadata/download_links.json
dirpath_output=./data/preprocess/
dirpath_log=./log/

#
python src/preprocess/create_example.py \
    --filepath_input "$filepath_input" \
    --filepath_verbs "$filepath_verbs" \
    --dirpath_graph "$dirpath_graph" \
    --filepath_metadata_video "$filepath_metadata_video" \
    --dirpath_output "$dirpath_output" \
    --dirpath_log "$dirpath_log"
