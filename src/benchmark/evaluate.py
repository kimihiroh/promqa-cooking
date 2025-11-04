"""
Evaluate (LLM-as-a-judge)

"""

from argparse import ArgumentParser
from collections import defaultdict
from copy import deepcopy
import logging
from pathlib import Path
import json
import time
from tqdm import tqdm
import yaml
from utils import (
    get_date,
    load_recipe,
    get_text_content_evaluation,
    call_api,
    estimate_cost,
)


def parse_feedback(feedback: str) -> tuple[str, str]:
    """
    parse feedback

    e.g.,
    TBU
    """

    splits = feedback.split("[Judge]")
    rationale, judge = splits

    return judge.strip(), rationale.strip()


def main(args):
    # load input
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    # load instruction
    name2recipe = load_recipe(args.filepath_recipe)

    # load prompt template
    with open(args.filepath_template, "r") as f:
        template_components = yaml.safe_load(f)

    logging.info(f"#target examples: {len(examples)} ({args.template_type=})")

    logging.info("Call API")
    if "human_answer" in examples[0]:
        filepath_output = (
            args.dirpath_output / f"{Path(args.model_id).name}_{args.template_type}"
            f"_{args.filepath_input.parent.name}_{args.filepath_input.name}"
        )
    else:
        filepath_output = (
            args.dirpath_output
            / f"{Path(args.model_id).name}_{args.template_type}_{args.filepath_input.name}"
        )
    new_examples = []
    count_tokens = defaultdict(int)
    for idx, example in tqdm(enumerate(examples), total=len(examples)):
        content, text_prompt = get_text_content_evaluation(
            model_id=args.model_id,
            template_type=args.template_type,
            components=template_components,
            name2recipe=name2recipe,
            example=example,
        )

        if idx == 0:  # sanity check
            logging.info("text_prompt")
            logging.info(text_prompt)
        # sys.exit('stop')

        response, _tokens = call_api(
            model_id=args.model_id,
            content=content,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

        new_example = deepcopy(example)
        new_example["evaluation"] = {
            "prompt": text_prompt,
            "model_id": args.model_id,
            "template_type": args.template_type,
            "response": response,
        }
        try:
            judge, rationale = parse_feedback(response)
            new_example["evaluation"]["judge"] = judge
            new_example["evaluation"]["rationale"] = rationale
        except Exception as e:
            logging.warning(f"Error happened during postprocess: {e}")
        new_examples.append(new_example)

        count_tokens["input"] += _tokens["input"]
        count_tokens["output"] += _tokens["output"]

        with open(filepath_output, "w") as f:
            json.dump(new_examples, f, indent=4)
            f.write("\n")
        time.sleep(args.wait_time)

    assert len(examples) == len(new_examples)

    cost = estimate_cost(args.model_id, count_tokens)
    logging.info(f"Estimated cost: ${cost:.4f}.")


if __name__ == "__main__":
    parser = ArgumentParser(description="Evaluate")
    parser.add_argument("--filepath_input", type=Path, help="filepath to input data")
    parser.add_argument("--filepath_recipe", type=Path, help="filepath for recipe")
    parser.add_argument("--filepath_template", type=Path, help="filepath to template")
    parser.add_argument("--dirpath_output", type=Path, help="dirpath to output")
    parser.add_argument("--template_type", type=str, help="template_type")
    parser.add_argument("--model_id", type=str, help="model id")
    parser.add_argument("--temperature", type=float, help="temperature", default=0.0)
    parser.add_argument(
        "--max_tokens", type=int, help="max tokens to generate", default=256
    )
    parser.add_argument("--wait_time", type=int, help="API call wait time", default=0.5)
    parser.add_argument("--dirpath_log", type=Path, help="dirpath to log")

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
            logging.FileHandler(args.dirpath_log / f"evaluate_{get_date()}.log"),
        ],
    )

    logging.info(f"Arguments: {vars(args)}")

    main(args)
