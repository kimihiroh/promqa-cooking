"""
helper functions

"""

import anthropic
import base64
from collections import defaultdict
from datetime import datetime
import google as genai
import json

# from litellm import completion
import logging
import os
from openai import OpenAI
from pathlib import Path
import pydot
import re
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
    "gemini/gemini-1.5-flash-001": {
        "input": 0.075 / 1e6,
        "output": 0.30 / 1e6,
    },
    "gemini/gemini-1.5-pro-002": {
        # the price doubles for >128k tokens
        "input": 3.5 / 1e6,
        "output": 10.5 / 1e6,
    },
    "gemini/gemini-1.5-flash-002": {
        "input": 0.075 / 1e6,
        "output": 0.30 / 1e6,
    },
}


TEMPLATE = """[Instruction]
This is a multimodal question answering task.

A user is cooking {activity_name}.
The images are the sampled frames from the user recording.
Here is the recipe in the DOT format:
[Recipe]
{recipe}

Answer the following question by the user in one sentence, based on the given information.
[Question]
{question}
[Answer]
"""  # noqa: E501

# idea: feed recipe as an image instead of text


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


def load_recipe(filepath_graph: Path):
    """
    load recipe

    """

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
            "dot": G.to_string().strip(),
        }
    return activity_name2recipe


def extract_index(filepath):
    return int(re.search(r"\d+", filepath.stem).group())


def encode_image(filepath: Path) -> Any:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def convert_time(time: str) -> int:
    hh, mm, ss = time.split(":")
    return int(mm) * 60 + int(ss)


def load_frame(
    example: Any, dirpath: Path, max_frames: int
) -> tuple[list[str], list[str], float]:
    """
    load & sample frames

    """

    logging.info("load & sample frames")

    dirpath_frame = dirpath / example["recording_id"]
    end_time_second = convert_time(example["end_time"])

    filepaths_frame = []
    for filepath in dirpath_frame.glob("*.png"):
        if int(filepath.stem) <= end_time_second:
            filepaths_frame.append(filepath)

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

    sampled_frame_paths, sampled_frame_ids = [], []
    # note: "reversed" to make sure the last frame is included in the input
    for idx, filepath_frame in enumerate(reversed(filepaths_frame_sorted)):
        # change sample rate
        if idx % rate_inverse == 0:
            sampled_frame_paths.insert(0, filepath_frame)
            sampled_frame_ids.insert(0, filepath_frame.stem)

    assert len(sampled_frame_paths) <= max_frames

    return sampled_frame_paths, sampled_frame_ids, rate_inverse


def get_text_content(
    model_id: str,
    recipe: str,
    name: str,
    question: str,
) -> tuple[list, str]:
    """
    format text as input
    todo

    """

    prompt = (
        TEMPLATE.replace("{recipe}", recipe)
        .replace("{activity_name}", name)
        .replace("{question}", question)
    )

    if "gpt" in model_id or "claude" in model_id:
        content = [
            {
                "type": "text",
                "text": prompt.strip(),
            }
        ]
    elif "gemini" in model_id:
        content = [prompt]
    else:
        logging.error(f"Undefined {model_id=}")
        content = []

    return content, prompt.strip()


def get_image_content(
    model_id: str,
    image_paths: list,
) -> list:
    """
    format images as input
    * encode: gpt4o
    * uplode: gemini

    """

    if "gpt" in model_id:
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encode_image(image_path)}"
                },
            }
            for image_path in image_paths
        ]
    elif "claude" in model_id:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": encode_image(image_path),
                },
            }
            for image_path in image_paths
        ]
    elif "gemini" in model_id:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        content = [genai.upload_file(image_path) for image_path in image_paths]
    else:
        logging.error(f"Undefined {model_id=}")
        content = []

    return content


def format_steps(steps: list, w_error: bool = False) -> str:
    output = ""
    for step in steps:
        output += f"- {step['description']}\n"
        if w_error and "errors" in step:
            for error in step["errors"]:
                output += f"    - [{error['tag']}] {error['description']}\n"

    return output.strip()


def get_text_content_evaluation(
    model_id: str,
    template_type: str,
    components: dict,
    name2recipe: dict,
    example: dict,
) -> tuple[list, str]:
    """

    todo: merge with get_text_content above
    """
    prompt = None
    template = components["prefix"]
    if "binary" in template_type:
        template += f"\n{components['option']['binary']}"
    elif "ternary" in template_type:
        template += f"\n{components['option']['ternary']}"
    template += f"\n{components['note']['default']}"
    if "recipe" in template_type:
        template += f"\n{components['note']['recipe']}"
    if "step" in template_type:
        template += f"\n{components['note']['step']}"
    template += f"\n{components['task']}"

    steps = example["previous_steps"] + [example["current_step"]]

    question = f"- {example['question']}"
    gold_answers = "\n".join([f"- {answer}" for answer in example["answers"]]).strip()
    if "human_answer" in example:
        predicted_answer = f"- {example['human_answer']}"
    else:
        predicted_answer = f"- {example['prediction']['response']}"

    prompt = (
        template.replace("{activity_name}", example["activity_name"])
        .replace("{step_information}", format_steps(steps=steps, w_error=True))
        .replace("{recipe}", name2recipe[example["activity_name"]]["dot"])
        .replace("{question}", question)
        .replace("{gold_answer}", gold_answers)
        .replace("{predicted_answer}", predicted_answer)
    )

    if "gpt" in model_id:
        content = [
            {
                "type": "text",
                "text": prompt.strip(),
            }
        ]
    elif "claude" in model_id:
        content = [
            {
                "type": "text",
                "text": prompt.strip(),
            }
        ]
    elif "gemini" in model_id:
        content = [prompt]
    else:
        logging.error(f"Undefined {model_id=}")
        content = []

    return content, prompt


def estimate_cost(model_id: str, count: dict[str, int]) -> None:
    """estimate cost"""
    cost = (
        PRICE[model_id]["input"] * count["input"]
        + PRICE[model_id]["output"] * count["output"]
    )
    return cost


def call_api(
    model_id: str,
    content: list,
    temperature: float,
    max_tokens: int,
) -> tuple[str, tuple[int, int]]:
    """
    call API via LiteLLM
    except Gemini

    """

    output = None
    tokens = defaultdict(int)
    try:
        if "gpt" in model_id:
            client = OpenAI()
            response = client.chat.completions.create(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            output = response.choices[0].message.content
            tokens["input"] = response.usage.prompt_tokens
            tokens["output"] = response.usage.completion_tokens
        elif "claude" in model_id:
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": content}],
            )
            output = response.content[0].text
            tokens["input"] = response.usage.input_tokens
            tokens["output"] = response.usage.output_tokens
        elif "gemini" in model_id:
            model = genai.GenerativeModel(model_name=str(Path(model_id).name))
            response = model.generate_content(
                content,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            output = response.text
            tokens["input"] = response.usage_metadata.prompt_token_count
            tokens["output"] = response.usage_metadata.candidates_token_count
        else:
            logging.error(f"Undefined {model_id=}")
    except Exception as e:
        output = "Error"
        logging.info(f"Exception: {e}")

    return output, tokens
