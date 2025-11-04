# ProMQA: Question Answering Dataset for Multimodal Procedural Activity Understanding

This is the official repository for "[ProMQA: Question Answering Dataset for Multimodal Procedural Activity Understanding](https://aclanthology.org/2025.naacl-long.579/)" (Hasegawa et al., NAACL 2025).

It contains code and data for:
* Data annotation code: preprocess, generation, and verification.
* Benchmarking code: download, prediction, and evaluation.

## News
* 2025/11/04: Additional 476 QA pairs are added. In total, 877 QAs are now available (`data/all_v1.json`).
* 2025/01/22: This work is accepted to NAACL 2025!
* 2024/10/29: 401 QA pairs are now available (`data/all_v0.json`).


## Overview

ProMQA(-Cooking) is an evaluation QA dataset for multimodal procedural activity understanding on cooking.

![Overview](https://github.com/kimihiroh/promqa/blob/main/docs/overview.png)

Given a recipe (text), a recording (video), and a question (text), the task is to predict an answer (text).

![Formulation](https://github.com/kimihiroh/promqa/blob/main/docs/formulation.png)

## Environment Setup

OS: `Ubuntu 24.04.1 LTS x86_64`.

### Virtual environment
```bash
conda create -y -n promqa-cooking python=3.12
conda activate promqa-cooking
pip install openai anthropic google-genai litellm flask gunicorn pre-commit pydot networkx Pillow
pre-commit install
```

You may need to install the following packages, if you have not:
```bash
sudo apt install graphviz ffmpeg parallel
```

## Data

### Download CaptainCook4D

#### Preprocessed Data
You can download the pre-sampled frames (360p) of CaptainCook4D from [our HuggingFace Dataset repo](https://huggingface.co/datasets/kimihiroh/promqa-cooking-frames):
```bash
cd <dirpath_hf>
git clone https://huggingface.co/datasets/kimihiroh/promqa-cooking-frames
cd <...>/promqa-cooking
bash src/unzip_all.sh <dirpath_hf>/promqa-cooking-frames
```
If you want the data as video in original resolution, please check [the following instruction](####full-data).

#### Full Data
* Follow [CaptainCook4D/downloader](https://github.com/CaptainCook4D/downloader) to download recordings. More specifically:
```bash
mkdir repos
cd repos
git clone git@github.com:CaptainCook4D/downloader.git
cd downloder
```
* Update `download_gopro_data.py` [[ref](https://github.com/CaptainCook4D/downloader/issues/1)]
```python
-    if recording_download_link_dict[Constants.GOPRO_RESOLUTION_4K] is not None:
+    if (
+        Constants.GOPRO_RESOLUTION_4K in recording_download_link_dict
+        and recording_download_link_dict[Constants.GOPRO_RESOLUTION_4K] is not None
+    ):
```
* Download
```bash
python download_gopro_data.py --data2d --resolution4K --output_dir <dirpath_original>
```
Now, you can skip to [the benchmark section](##benchmarking) if you do not annotate QAs by yourself.

## Data Annotation

![Interface](https://github.com/kimihiroh/promqa/blob/main/docs/interface.png)

### Download CaptainCook4D Annotation
```bash
cd repos
git clone git@github.com:CaptainCook4D/annotations.git
```

### Preprocess
```bash
bash src/preprocess/update_annotation.sh
bash src/preprocess/create_example.sh
bash src/preprocess/sample.sh
bash src/preprocess/instruction.sh <filename_sample> # e.g., samples_1000.json
```

### QA Generation
```bash
bash src/qa-generation/run.sh <filename_sample> # e.g., samples_1000.json
```

### Human Verification
```bash
ln -s <dirpath_original>/captain_cook_4d/gopro/ ./src/verification/static/
ln -s <dirpath_to_this_folder>/data/preprocess/graphs/ ./src/verification/static
bash src/verification/start.sh <filename_qas> # e.g., gpt-4o-2024-08-06_step-target_samples_1000.json
```


## Benchmarking

### Prepross
Sample frames from videos. You can skip this if you download the pre-sampled frames.
```bash
bash src/benchmark/sample_frame.sh \
    <dirpath_original>/captain_cook_4d \
    <dirpath_frame>
```

### Inference
1. Set an API key for each, e.g., `export OPENAI_API_KEY=<your_key>`
2. Run models from OpenAI, Google, and Anthropic:
```bash
bash src/benchmark/predict.sh \
    <input_file> \ # e.g., all_v1.json
    <dirpath_frame>/frames/<resolution> \ # Or, <dirpath_hf>/promqa-cooking-frames/ if you download the pre-sampled version
    <model_id> \  # e.g., gpt-4o-2024-08-06
```

### Evaluation
1. Set an API key for each, e.g., `export OPENAI_API_KEY=<your_key>`
2. Run LLM-as-a-judge:
```bash
bash src/benchmark/evaluate.sh \
    <filepath_prediction>  # e.g., gpt-4o-2024-08-06_20_all_v1.json
bash src/benchmark/evaluate.sh gpt-4o-2024-08-06_20_all_v1.json
```

## Citation

If you find this work helpful in your research, please consider citing our work.
```bib
@inproceedings{hasegawa-etal-2025-promqa,
      title={ProMQA: Question Answering Dataset for Multimodal Procedural Activity Understanding},
      author={Hasegawa, Kimihiro and Imrattanatrai, Wiradee and Cheng, Zhi-Qi and Asada, Masaki and Holm, Susan and Wang, Yuran and Fukuda, Ken and Mitamura, Teruko},
      booktitle = "Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)",
      year = "2025",
      url = "https://aclanthology.org/2025.naacl-long.579/",
}
```

## Issues/Questions

For any issues, questions, or requests, please create a [GitHub Issue](https://github.com/kimihiroh/promqa/issues).
