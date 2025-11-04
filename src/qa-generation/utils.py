"""
utils functions

"""

import base64
from collections import defaultdict
from datetime import datetime
import json
from litellm import completion
import logging
from openai import OpenAI
import os
from pathlib import Path
import pydot
import re
import time
from tqdm import tqdm
import random
from typing import Any, Optional


PRICE = {
    "gpt-4o": {
        "input": 5 / 1e6,
        "output": 15 / 1e6,
    },
    "gpt-4o-2024-08-06": {
        "input": 2.5 / 1e6,
        "output": 10 / 1e6,
    },
    "gpt-4o-mini-2024-07-18": {
        "input": 0.15 / 1e6,
        "output": 0.6 / 1e6,
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3 / 1e6,
        "output": 15 / 1e6,
    },
    "gemini/gemini-1.5-pro-001": {
        # the price doubles for >128k tokens
        "input": 3.5 / 1e6,
        "output": 10.5 / 1e6,
    },
}


def get_date(granularity: Optional[str] = "min") -> str:
    """
    get date

    """
    date_time = datetime.now()
    if granularity == "min":
        str_data_time = date_time.strftime("%Y%m%d-%H%M")
    elif granularity == "day":
        str_data_time = date_time.strftime("%Y%m%d")
    else:
        logging.error(f"Undefined timestamp granularity: {granularity}")

    return str_data_time


def load_recipe(filepath_graph, dirpath_recipe_image):
    id2image_path = {}
    for filepath in dirpath_recipe_image.glob("*.png"):
        id2image_path[filepath.stem] = filepath

    with open(filepath_graph, "r") as f:
        raw_graphs = json.load(f)
    activity_name2recipe = {}
    for activity_id, graph in raw_graphs.items():
        G = pydot.Dot(graph_type="digraph")
        action_id2description = {}
        for action_id, action in graph["steps"].items():
            node = pydot.Node(f"{action}")
            action_id2description[action_id] = action
            G.add_node(node)

        for edge in graph["edges"]:
            edge = pydot.Edge(
                action_id2description[str(edge[0])],
                action_id2description[str(edge[1])],
            )
            G.add_edge(edge)

        activity_name2recipe[graph["name"]] = {
            "encoded_image": encode_image(id2image_path[activity_id]),
            "dot": G.to_string().strip(),
            "steps": graph["steps"],
        }
    return activity_name2recipe


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_index(filepath):
    return int(re.search(r"\d+", filepath.stem).group())


def load_frame(dirpath: Path, max_frames: int) -> dict:
    """
    load & sample frames

    """

    logging.info("load & sample frames")
    id2sample = {}
    for dirpath_frames in tqdm(dirpath.iterdir(), total=len(list(dirpath.iterdir()))):
        if not dirpath_frames.is_dir():
            continue

        filepaths_frame = list(dirpath_frames.glob("*.png"))
        num_frames = len(filepaths_frame)
        # e.g., 700 frames, max 250 => rate: 1 frame per every 3 frames
        if num_frames > max_frames:
            if num_frames % max_frames == 0:
                rate_inverse = num_frames // max_frames
            else:
                rate_inverse = (num_frames // max_frames) + 1
        else:
            rate_inverse = 1
        filepaths_frame_sorted = sorted(filepaths_frame, key=extract_index)

        sampled_frames = []
        sampled_frames_idx = []
        # note: "reversed" to make sure the last frame is included in the input
        for idx, filepath_frame in enumerate(reversed(filepaths_frame_sorted)):
            # change sample rate
            if idx % rate_inverse == 0:
                sampled_frames.insert(0, encode_image(filepath_frame))
                sampled_frames_idx.insert(0, filepath_frame.stem)

        assert len(sampled_frames) <= max_frames

        id2sample[dirpath_frames.stem] = {
            "encode": sampled_frames,
            "idx": sampled_frames_idx,
            "rate_inverse": rate_inverse,
        }

    return id2sample


def format_steps(steps: list, w_error: bool = False) -> str:
    output = ""
    for step in steps:
        output += f"- {step['description']}\n"
        if w_error and "errors" in step:
            for error in step["errors"]:
                output += f"    - [{error['tag']}] {error['description']}\n"

    return output.strip()


def get_step_information(example: dict, w_error: bool = False) -> str:
    step = ""
    # previous
    if len(example["previous_steps"]) == 0:
        pass
    elif len(example["previous_steps"]) == 1:
        step += f"The person completed this step:\n{format_steps(example['previous_steps'], w_error)}\n"
    else:
        step += f"The person completed these steps:\n{format_steps(example['previous_steps'], w_error)}\n"

    # current
    if len(example["previous_steps"]) == 0:
        step += (
            "The person has just performed this step:"
            f"\n{format_steps([example['current_step']], w_error)}"
        )
    else:
        step += (
            "And, the person has just performed this step:\n"
            f"{format_steps([example['current_step']], w_error)}"
        )
    return step


def get_current_step_information(example: dict) -> str:
    step = (
        "The person has just performed this step:"
        f"\n{format_steps([example['current_step']], False)}"
    )
    return step


def get_target_information(example: dict, id2step: dict) -> str:
    target = ""
    match example["type"]:
        case "next":
            if len(example["next_steps"]) == 0:
                target = "The friend know this is the last step."
            else:
                target = (
                    "The friend knows the following step(s) can be done next:\n"
                    f"{format_steps(example['next_steps'])}"
                )
        case "missing":
            if len(example["missing_steps"]) == 0:
                target = "The friend know there is no missing step."
            elif len(example["missing_steps"]) == 1:
                target = (
                    "The friend knows the following step is missed:\n"
                    f"{format_steps(example['missing_steps'])}"
                )
            else:
                target = (
                    "The friend knows the following steps are missed:\n"
                    f"{format_steps(example['missing_steps'])}"
                )
        case "order":
            if example["error_description"].startswith(
                "This step does not contain any"
            ):
                target = f"The friend knows {example['error_description'].lower()}"
            else:
                target = (
                    f"The friend knows that there is an error in the latest action about {example['type']}: "
                    f"{example['error_description']}"
                )
        case "preparation" | "measurement" | "timing" | "technique" | "temperature":
            if example["error_description"].startswith(
                "This step does not contain any"
            ):
                target = f"The friend knows {example['error_description'].lower()}"
            else:
                target = (
                    f"The friend knows that there is an error in the latest action about {example['type']}: "
                    f"{example['error_description']}\n"
                    "According to the recipe, the correct action is:\n"
                    f"- {id2step[str(example['current_step']['step_id'])]}"
                )

        case _:
            logging.warning(f"Undefined {example['question_type']=}")
    return target


def get_text_content(
    components: dict,
    template_type: str,
    example: dict,
    name2recipe: dict,
) -> tuple[list, str]:
    prompt = None
    match template_type:
        case "video-dot":
            template = f"""{components['prefix']}
{components['recipe']['dot']}
{components['video']['wo_recipe_image']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = template.replace(
                "{recipe_name}", example["activity_name"]
            ).replace("{recipe}", name2recipe[example["activity_name"]]["dot"])
        case "video-image":
            template = f"""{components['prefix']}
{components['recipe']['image']['w_video']}
{components['video']['w_recipe_image']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = template.replace("{recipe_name}", example["activity_name"])
        case "video-target":
            template = f"""{components['prefix']}
{components['video']['wo_recipe_image']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = template.replace(
                "{recipe_name}", example["activity_name"]
            ).replace(
                "{target_information}",
                get_target_information(
                    example, name2recipe[example["activity_name"]]["steps"]
                ),
            )
        case "video-step-target":
            template = f"""{components['prefix']}
{components['step']}
{components['video']['wo_recipe_image']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{step_information}", get_step_information(example))
                .replace(
                    "{target_information}",
                    get_target_information(
                        example, name2recipe[example["activity_name"]]["steps"]
                    ),
                )
            )
        case "step-dot":
            template = f"""{components['prefix']}
{components['recipe']['dot']}
{components['step']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{recipe}", name2recipe[example["activity_name"]]["dot"])
                .replace("{step_information}", get_step_information(example))
            )
        case "step-image":
            template = f"""{components['prefix']}
{components['recipe']['image']['wo_video']}
{components['step']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = template.replace(
                "{recipe_name}", example["activity_name"]
            ).replace("{step_information}", get_step_information(example))
        case "step-target":  # default
            template = f"""{components['prefix']}
{components['step']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{step_information}", get_step_information(example))
                .replace(
                    "{target_information}",
                    get_target_information(
                        example, name2recipe[example["activity_name"]]["steps"]
                    ),
                )
            )
        case "step-dot-target":  # default+alpha: better answers?
            template = f"""{components['prefix']}
{components['recipe']['dot']}
{components['step']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{recipe}", name2recipe[example["activity_name"]]["dot"])
                .replace("{step_information}", get_step_information(example))
                .replace(
                    "{target_information}",
                    get_target_information(
                        example, name2recipe[example["activity_name"]]["steps"]
                    ),
                )
            )
        case "step-errors-target":  # default+alpha: hypothesis: better answers?
            template = f"""{components['prefix']}
{components['step']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{step_information}", get_step_information(example, True))
                .replace("{target_information}", get_target_information(example))
            )
        case "one-step-target":
            template = f"""{components['prefix']}
{components['step']}
{components['target']}
{components['question'][example['type']]}
{components['constraint']}
{components['example'][example['type']]}
{components['suffix']}"""
            prompt = (
                template.replace("{recipe_name}", example["activity_name"])
                .replace("{step_information}", get_current_step_information(example))
                .replace("{target_information}", get_target_information(example))
            )
        case _:
            logging.warning(f"Undefined {template_type=}")

    content = [
        {
            "type": "text",
            "text": prompt.strip(),
        }
    ]

    return content, prompt.strip()


def get_image_content(
    id2sample: dict,
    example: dict,
    name2recipe: dict,
    template_type: str,
) -> list:
    content = []
    if "image" in template_type:
        content += [
            {
                "type": "image_url",
                "image_url": {
                    "url": (
                        f"data:image/png;base64,"
                        f"{name2recipe[example['activity_name']]['encoded_image']}"
                    )
                },
            }
        ]
    if "video" in template_type:
        content += [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_image}"},
            }
            for encoded_image in id2sample[example["example_id"]]["encode"]
        ]
    return content


def postprocess(generation: str) -> dict[str, Any]:
    # specifically for gemini
    qas = []
    if generation:
        generation = generation.replace("**", "")
        matches = re.findall(r"\* (.*?)\n((?: {2,4}\* .*?\n)*)", generation + "\n")

        for question, answers in matches:
            qa = {"question": question, "answers": []}
            for raw_answer in answers.splitlines():
                _matches = re.findall(r" {2,4}\* (.*)", raw_answer)
                if len(_matches) != 1:
                    logging.warning(f"No/Multiple answer(s) extracted: {raw_answer}")
                else:
                    qa["answers"].append(_matches[0])
            qas.append(qa)

        random.shuffle(qas)

    if len(qas) != 3:
        logging.warning(
            f"{len(qas)} (!=3) QAs were extracted from:\n"
            f"generation={generation} qas={qas}\n"
        )
        if len(qas) == 0:
            qas.append({"question": None, "answers": [None]})

    return qas


def estimate_cost(model_id: str, count: dict[str, int]) -> float:
    """estimate cost"""
    cost = (
        PRICE[model_id]["input"] * count["input"]
        + PRICE[model_id]["output"] * count["output"]
    )
    logging.info(f"Estimated cost: ${cost:.4f}.")
    return cost


def call_openai_api(
    model_id: str,
    messages_list: list[str],
    temperature: float,
    max_tokens: int,
    wait_time: int = 30,
) -> list[str]:
    """call OpenAI API"""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    responses = []
    count_tokens = defaultdict(int)
    for messages in messages_list:
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            responses.append((model_id, response.choices[0].message.content))
            count_tokens["input"] += response.usage.prompt_tokens
            count_tokens["output"] += response.usage.completion_tokens
        except Exception as e:
            responses.append((model_id, "Error"))
            logging.info(f"Exception: {e}")
        # todo: change here, more dynamically adjust wait time
        time.sleep(wait_time)

    estimate_cost(model_id, count_tokens)

    return responses


def call_api(
    model_id: str,
    messages_list: list[str],
    temperature: float,
    max_tokens: int,
    wait_time: int,
) -> list[str]:
    """call API via LiteLLM"""

    responses = []
    count_tokens = defaultdict(int)
    for messages in messages_list:
        try:
            response = completion(
                model=model_id,
                messages=[messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            responses.append(response.choices[0].message.content)
            count_tokens["input"] += response.usage.prompt_tokens
            count_tokens["output"] += response.usage.completion_tokens
        except Exception as e:
            responses.append("Error")
            logging.info(f"Exception: {e}")
        time.sleep(wait_time)

    cost = estimate_cost(model_id, count_tokens)

    return responses, cost


def save_data(
    model_id: str,
    template_type: str,
    examples: list[dict[str, str | float]],
    responses: list[str],
    indices: list[int],
    filepath_output: Path,
) -> None:
    try:
        # combine input&output
        if len(examples) != len(responses):
            logging.error(f"{len(examples)=} != {len(responses)=}")
        for idx, response in zip(indices, responses):
            if "generation" not in examples[idx]:
                examples[idx]["generation"] = {"prompt": None}
            examples[idx]["generation"]["response"] = response
            examples[idx]["generation"]["model_id"] = model_id
            examples[idx]["generation"]["template_type"] = template_type
            qas = postprocess(response)
            random.shuffle(qas)
            examples[idx]["generation"]["qas"] = qas
            examples[idx]["question"] = qas[0]["question"]
            examples[idx]["answers"] = qas[0]["answers"]
        # save combined version
        with open(filepath_output, "w") as f:
            json.dump(examples, f, indent=4)
            f.write("\n")
    except Exception as e:
        logging.error(f"Error while saving: {e}")
        # save generation as is
        with open(filepath_output, "w") as f:
            json.dump(responses, f, indent=4)
            f.write("\n")

    return None
