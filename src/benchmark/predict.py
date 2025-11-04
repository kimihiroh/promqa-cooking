"""
Predict answers from each set of a video (images), a recipe, and a question.

"""

from argparse import ArgumentParser
from copy import deepcopy
from collections import defaultdict
import json
import logging
from pathlib import Path
import time
from tqdm import tqdm
from utils import (
    get_date,
    load_recipe,
    load_frame,
    get_text_content,
    get_image_content,
    call_api,
    estimate_cost,
    # save_data,
)


def main(args):
    # load input
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    # load instruction
    name2recipe = load_recipe(args.filepath_recipe)

    filepath_output = (
        args.dirpath_output
        / f"{Path(args.model_id).name}_{args.max_frames}_{args.filepath_input.name}"
    )

    # create input & call api
    logging.info("Start inference")
    new_examples = []
    count_tokens = defaultdict(int)
    for idx, example in tqdm(enumerate(examples), total=len(examples)):
        content, text_prompt = get_text_content(
            model_id=args.model_id,
            recipe=name2recipe[example["activity_name"]]["dot"],
            name=example["activity_name"],
            question=example["question"],
        )

        if idx == 0:  # sanity check
            logging.info("content[0]")
            if "gpt" in args.model_id or "claude" in args.model_id:
                logging.info(content[0]["text"])
            elif "gemini" in args.model_id:
                logging.info(content[0])
            else:
                logging.error(f"Undefined {args.model_id=}")

        logging.info("Prepare image content")
        # load user recording as frames
        filepaths_image, ids_image, rate_inverse = load_frame(
            example, args.dirpath_image, args.max_frames
        )
        content += get_image_content(
            model_id=args.model_id,
            image_paths=filepaths_image,
        )
        # call api
        response, _tokens = call_api(
            model_id=args.model_id,
            content=content,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

        new_example = deepcopy(example)
        new_example["prediction"] = {
            "prompt": text_prompt,
            "frame_ids": ids_image,
            "rate_inverse": rate_inverse,
            "dirpath_images": str(args.dirpath_image),
            "model_id": args.model_id,
            "response": response,
        }
        new_examples.append(new_example)

        count_tokens["input"] += _tokens["input"]
        count_tokens["output"] += _tokens["output"]

        if "gemini" in args.model_id:
            logging.info("Delete uploaded images")
            for _content in content[1:]:
                _content.delete()

        with open(filepath_output, "w") as f:
            json.dump(new_examples, f, indent=4)
            f.write("\n")
        time.sleep(args.wait_time)

    logging.info(f"#target examples: {len(new_examples)}/{len(examples)}")
    cost = estimate_cost(args.model_id, count_tokens)
    logging.info(f"Estimated cost: ${cost:.4f}.")


if __name__ == "__main__":
    parser = ArgumentParser(description="Predict")
    parser.add_argument("--filepath_input", type=Path, help="filepath for input")
    parser.add_argument("--filepath_recipe", type=Path, help="filepath for recipe")
    parser.add_argument("--dirpath_image", type=Path, help="dirpath for frames")
    parser.add_argument("--dirpath_output", type=Path, help="filepath for output")
    parser.add_argument("--model_id", type=str, help="model id")
    parser.add_argument("--temperature", type=float, help="temperature", default=0.0)
    parser.add_argument(
        "--max_tokens", type=int, help="max tokens to generate", default=1024
    )
    parser.add_argument("--max_frames", type=int, help="max frames to feed", default=20)
    parser.add_argument("--wait_time", type=int, help="API call wait time", default=10)
    parser.add_argument("--dirpath_log", type=Path, help="dirpath for log")

    args = parser.parse_args()

    if not args.dirpath_log.exists():
        args.dirpath_log.mkdir(parents=True)

    if not args.dirpath_output.exists():
        args.dirpath_output.mkdir(parents=True)

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.dirpath_log / f"predict_{get_date()}.log"),
        ],
    )

    logging.info(f"Arguments: {vars(args)}")

    main(args)
