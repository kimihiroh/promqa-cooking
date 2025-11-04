"""
Explore templates for calling LLM API to generate question-answer pairs

"""

from argparse import ArgumentParser
from copy import deepcopy
import json
import logging
from pathlib import Path
import yaml
from utils import (
    get_date,
    load_recipe,
    load_frame,
    get_text_content,
    get_image_content,
    # call_openai_api,
    call_api,
    save_data,
)


def main(args):
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    # load template
    with open(args.filepath_template, "r") as f:
        template_components = yaml.safe_load(f)

    name2recipe = load_recipe(args.filepath_graph, args.dirpath_recipe_image)

    # load user recording as frames
    if "video" in args.template_type:
        id2sample = load_frame(args.dirpath_frames, args.max_frames)

    logging.info(f"{args.template_type=}")
    messages_list, indices = [], []
    new_examples = []
    for idx, example in enumerate(examples):
        # text part
        content, text_prompt = get_text_content(
            components=template_components,
            template_type=args.template_type,
            example=example,
            name2recipe=name2recipe,
        )
        # add image part if applicable
        if "video" in args.template_type:
            content += get_image_content(
                id2sample=id2sample,
                example=example,
                name2recipe=name2recipe,
                template_type=args.template_type,
            )
        messages_list.append({"role": "user", "content": content})
        indices.append(idx)

        new_example = deepcopy(example)
        new_example["generation"] = {"prompt": text_prompt}
        new_examples.append(new_example)

    # check
    logging.info("[sanity check] messages_list[1]['content'][0]['text']=")
    logging.info(messages_list[1]["content"][0]["text"])
    logging.info(f"#requests: {len(messages_list)}/{len(examples)}")

    logging.info("API call starts")
    responses, cost = call_api(
        model_id=args.model_id,
        messages_list=messages_list,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        wait_time=1 if "video" in args.template_type else 0.5,
    )

    save_data(
        model_id=args.model_id,
        template_type=args.template_type,
        examples=new_examples,
        responses=responses,
        indices=indices,
        filepath_output=(
            args.dirpath_output
            / f"{Path(args.model_id).name}_{args.template_type}_{args.filepath_input.name}"
            # args.dirpath_output / f"{args.filepath_input.name}"
        ),
    )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Explore templates for calling LLM API to generate question-answer pairs"
    )
    parser.add_argument(
        "--filepath_input",
        type=Path,
        help="filepath to input data",
    )
    parser.add_argument(
        "--filepath_template",
        type=Path,
        help="filepath to template",
    )
    parser.add_argument(
        "--dirpath_frames", type=Path, help="dirpath to resized frames", default=None
    )
    parser.add_argument(
        "--filepath_graph",
        type=Path,
        help="filepath to graphs",
    )
    parser.add_argument(
        "--dirpath_recipe_image",
        type=Path,
        help="dirpath to recipe images",
        default=None,
    )
    parser.add_argument(
        "--dirpath_output",
        type=Path,
        help="dirpath to output data",
    )
    parser.add_argument(
        "--model_id",
        type=str,
        help="model_id",
    )
    parser.add_argument(
        "--template_type",
        type=str,
        help="template_type",
    )
    parser.add_argument("--temperature", type=float, help="temperature", default=0.7)
    parser.add_argument(
        "--max_tokens", type=int, help="max tokens to generate", default=512
    )
    parser.add_argument("--max_frames", type=int, help="max frames to feed", default=50)
    parser.add_argument("--seed", type=int, help="random seed", default=42)
    parser.add_argument("--dirpath_log", type=Path, help="dirpath for log")

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.dirpath_log / f"generation_{get_date()}.log"),
        ],
    )

    if not args.dirpath_output.exists():
        args.dirpath_output.mkdir(parents=True)

    logging.info(f"Arguments: {vars(args)}")

    main(args)
