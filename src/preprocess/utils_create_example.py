import logging
from pathlib import Path
import json
import networkx as nx
from copy import deepcopy


# def get_target_error(errors):
#     """
#     return only one target error

#     """
#     candidates = []
#     for error in errors:
#         if error["tag"] in ["Missing Step", "Order Error"]:
#             candidates.append(error)

#     if len(candidates) > 0:
#         return candidates[0]
#     else:
#         return None


def get_activity_name2recipe(dirpath: Path):
    """
    return mapping from activity name (lowercase, no space) to recipe graph

    """

    name2recipe = {}
    for filepath in dirpath.glob("*.json"):
        with open(filepath, "r") as f:
            data = json.load(f)

        G = nx.DiGraph()
        G.add_edges_from(data["edges"])
        name2recipe[filepath.stem] = {
            "graph": G,
            "steps": {int(k): v for k, v in data["steps"].items()},
        }

    return name2recipe


def get_video_metadata(filepath) -> dict:
    """
    get video's metadata, esp. if 4k is available

    """

    with open(filepath, "r") as f:
        examples = json.load(f)

    id2bool = {}
    for idx, example in examples.items():
        id2bool[idx] = "gopro_4k" in example

    return id2bool


def get_next_steps(
    recipe,
    passed_steps,
):
    """
    return possible next steps

    note:
    * passed_steps may or may not be completed

    """
    next_steps = []
    G = recipe["graph"]
    if 0 not in passed_steps:
        passed_steps = deepcopy(passed_steps)
        passed_steps.append(0)
    else:
        logging.warning("start found in passed steps")

    for node in G.nodes:
        if recipe["steps"][node] == "END":
            continue
        if node not in passed_steps:
            # check if all predecessors of this node are in passes_steps
            all_predecessors_passed = all(
                pred in passed_steps for pred in G.predecessors(node)
            )
            # check if no succeeding step is passed
            # otherwise missing steps would be added as next steps
            succeeding_step_found = any(
                pred in passed_steps for pred in nx.descendants(G, node)
            )

            if all_predecessors_passed and not succeeding_step_found:
                next_steps.append(node)

    next_steps_w_description = [
        {"step_id": x, "description": recipe["steps"][x]} for x in next_steps
    ]

    return next_steps_w_description


def get_missing_steps(
    recipe,
    passed_steps,
):
    """
    return missing steps
    missing step is a step where at least
    * one of preceding steps and one of succeeddings are performed

    note:
    * passed_steps may or may not be correctly completed

    """
    G = recipe["graph"]
    if 0 not in passed_steps:
        passed_steps = deepcopy(passed_steps)
        passed_steps.append(0)
    else:
        logging.warning("start found in passed steps")

    missing_steps = []
    for node in G.nodes:
        if recipe["steps"][node] == "END":
            continue
        if node not in passed_steps:
            # check if at least one preceding step and one succeeding step are passed
            preceding_step_found = any(
                pred in passed_steps for pred in nx.ancestors(G, node)
            )
            succeeding_step_found = any(
                pred in passed_steps for pred in nx.descendants(G, node)
            )
            if preceding_step_found and succeeding_step_found:
                missing_steps.append(node)

    missing_steps_w_description = [
        {"step_id": x, "description": recipe["steps"][x]} for x in missing_steps
    ]

    return missing_steps_w_description


def check_if_this_is_missing_step(step) -> bool:
    """
    check if this step is missing step

    note:
    * there are missing steps (start/end time is -1) w/o error annotations
        * e.g. activity_id 18

    """
    flag = False
    if "errors" in step:
        for error in step["errors"]:
            if error["tag"] == "Missing Step":
                flag = True
    if step["end_time"] < 0:
        flag = True

    return flag


def check_end_time(examples) -> None:
    """
    check if end time is valid

    """
    for example in examples:
        splits = example["end_time"].split(":")
        assert len(splits) == 3
        end_time = int(splits[0]) * 3600 + int(splits[1]) * 60 + int(splits[2])
        if end_time < 0:
            logging.error(
                f"Invalid end time: {example['recording_id']} {example['end_time']}"
            )
    return None


# def current_step_overlaps_with_next(
#     idx: int, steps: list, current_step_end_time: float, buffer: float = 2
# ) -> bool:
#     """
#     check if the current step's end time overlaps with the next step's start time
#     note:
#     * 2 seconds is buffer for potential small annotation errors
#     """

#     assert current_step_end_time >= 0

#     next_step = None
#     while len(steps) > idx + 1:
#         # find the earliest step after step[idx] (but missing step)
#         if steps[idx + 1]["start_time"] > 0:
#             next_step = steps[idx + 1]
#             break
#         idx += 1

#     if next_step and current_step_end_time > next_step["start_time"] + buffer:
#         return True

#     return False


def check_overlap(
    idx: int, current_end_time: float, steps: list, margin: float = 2
) -> bool:
    """
    check if the current step overlaps with any of the following steps
    margin: ignore potential small annotation artifact

    """
    current_start_time = 0.0
    for step in steps[idx + 1 :]:
        if check_if_this_is_missing_step(step):
            continue
        if step["end_time"] < 5:
            continue

        # check if a following step overlaps with the current trimmed video
        duration = step["end_time"] - step["start_time"]
        if duration < 2:
            if max(current_start_time, step["start_time"] + duration * 0.9) < min(
                current_end_time, step["end_time"]
            ):
                return True
        else:
            if max(current_start_time, step["start_time"] + margin) < min(
                current_end_time, step["end_time"]
            ):
                return True

    return False


def format2hhmmss(time):
    """format time (second) into hh:mm:ss"""
    h = int(time // 3600)
    m = int((time % 3600) // 60)
    s = int((time % 3600) % 60)

    return f"{h:02}:{m:02}:{s:02}"


def get_end_time(idx: int, steps: list) -> float:
    """
    identify the latest end time in prevs + current

    """
    end_time = steps[idx]["end_time"]
    for step in steps[:idx]:
        if end_time < step["end_time"]:
            # logging.debug(
            #     "one of prev ends later than the current, so we use the later one: "
            #     f"{end_time} -> {step['end_time']}"
            # )
            end_time = step["end_time"]

    return end_time


def sanity_check_order_error(
    recording_id,
    step,
    recipe,
    previous_steps,
):
    order_error = None
    if "errors" in step:
        for error in step["errors"]:
            if error["tag"] == "Order Error":
                order_error = error

    # okay order error annotation even though no missing step exists
    exceptions = [
        # additional wrong step is done during this step
        ("1_32", 2),
        ("1_49", 2),
        ("1_42", 2),
        # all steps are done but in wrong order
        ("1_42", 12),
        ("1_42", 9),
        # same step performed twice, so the second one does not have missing step
        ("2_41", 12),
        # two steps performed once
        ("13_41", 4),
    ]

    missing_steps_before_this_step = get_missing_steps(
        recipe,
        # not adding the current step
        [x["step_id"] for x in previous_steps],
    )
    missing_steps_after_this_step = get_missing_steps(
        recipe,
        [x["step_id"] for x in previous_steps] + [step["step_id"]],
    )

    # sanity check: if missing step is included here
    if (
        len(missing_steps_before_this_step) == 0
        and len(missing_steps_after_this_step) == 0
    ):
        if (recording_id, step["step_id"]) in exceptions:
            pass
        elif not order_error:
            pass
        else:
            print(order_error)
            logging.warning(
                "Order error annotation w/o missing steps "
                f"recording id: {recording_id}, step: {step['step_id']}"
            )


def check_errors(previous_steps, exclude_types=[]):
    """check if error except some exists"""
    error_exists = False
    for step in previous_steps:
        if "errors" in step:
            for error in step["errors"]:
                if error["tag"] not in exclude_types:
                    error_exists = True
    return error_exists


def check_if_target_error_exists(step, error_type):
    """check if target error type exists"""
    flag = False
    if "errors" in step:
        for error in step["errors"]:
            if error["tag"] == error_type:
                flag = True
    return flag


def get_target_description(step, error_type):
    target_error = None
    if "errors" in step:
        for error in step["errors"]:
            if error["tag"] == error_type:
                target_error = error

    error_description = ""
    if target_error:
        error_description = target_error["description"]
    else:
        _type = error_type.replace("Error", "").strip().lower()
        error_description = f"This step does not contain any {_type} errors."

    return error_description


def check_if_target_verb(step, _type, type2verbs) -> bool:
    """check if this step can be a error of this type"""

    verb = step["description"].split("-")[0].lower()
    if verb in type2verbs[_type]:
        return True
    else:
        return False
