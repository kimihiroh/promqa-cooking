"""
Create examples from CaptainCook4D

"""

from argparse import ArgumentParser
import logging
from pathlib import Path
import json
from collections import defaultdict
from copy import deepcopy
from utils_create_example import (
    get_activity_name2recipe,
    get_next_steps,
    get_missing_steps,
    check_if_this_is_missing_step,
    check_end_time,
    check_overlap,
    format2hhmmss,
    get_end_time,
    sanity_check_order_error,
    check_errors,
    get_target_description,
    check_if_target_error_exists,
    get_video_metadata,
)


def main(args):
    activity_name2recipe = get_activity_name2recipe(args.dirpath_graph)

    # load annotation
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    # # load mapping
    # with open(args.filepath_verbs, "r") as f:
    #     error_type2verbs = json.load(f)

    w_4k_video = get_video_metadata(args.filepath_metadata_video)

    """
    [target]
    - next step
    - order error
    - missing step
    - preparation error
    - technique error
    - timing error
    - measurement error
    - temperature error
    """
    targets = {}
    for example in examples:
        # skip if 4k video is not available
        if not w_4k_video[example["recording_id"]]:
            continue

        _activity_name = example["activity_name"].lower().replace(" ", "")
        previous_steps = []
        for idx, step in enumerate(example["step_annotations"]):
            # note: better to use this idx for question id? <= i think step_id is enough

            if check_if_this_is_missing_step(step):
                continue

            # skip examples if the input video is too short
            if step["end_time"] < 5:
                if step["step_id"] != -1:
                    logging.warning(f"If exists, this should be added as prev: {step}")
                continue

            current_step = {
                "step_id": step["step_id"],
                "description": (
                    step["modified_description"]
                    if "modified_description" in step
                    else step["description"]
                ),
            }
            if "errors" in step:
                current_step["errors"] = deepcopy(step["errors"])

            end_time = get_end_time(idx, example["step_annotations"])

            # skip if the current step overlaps with any of following steps
            # to avoid any errornous cases after adding it to prev steps
            if check_overlap(
                idx=idx, current_end_time=end_time, steps=example["step_annotations"]
            ):
                is_overlap = True
            else:
                is_overlap = False

            # create example base
            example_id = f"{example['recording_id']}_{current_step['step_id']}"
            target = {
                "recording_id": example["recording_id"],
                "example_id": example_id,
                "end_time": format2hhmmss(end_time),
                "activity_name": example["activity_name"],
                "previous_steps": deepcopy(previous_steps),
                "current_step": current_step,
            }

            # == create examples ==

            """
            create prompt for next step questions
            note:
            * create even if this is the last step, then answer would be none.
            * skip if the current step overlap with the next step duration
            """
            question_id = f"{example_id}_next"
            if (question_id in targets) or is_overlap:
                """
                e.g., one step is performed in multiple timings, like A -> B -> A
                this cannot be said as an annotation error, so just skip these cases.
                """
                pass
                # logging.warning(f"Duplicate example found. Skip: {question_id}")
            else:
                next_steps = get_next_steps(
                    activity_name2recipe[_activity_name],
                    [x["step_id"] for x in previous_steps] + [step["step_id"]],
                )
                targets[question_id] = target | {
                    "type": "next",
                    "next_steps": next_steps,
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            """
            create missing step questions
            note:
            * create even if there is no missing step, then answer would be none
            """
            question_id = f"{example_id}_missing"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
            ):
                pass
            else:
                missing_steps = get_missing_steps(
                    activity_name2recipe[_activity_name],
                    [x["step_id"] for x in previous_steps] + [step["step_id"]],
                )
                targets[question_id] = target | {
                    "type": "missing",
                    "missing_steps": missing_steps,
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps, ["Missing Step"]),
                }

            """
            create prompt for order error questions
            only when order error description is available

            think: what is answer==none questions for order error
            """
            # sanity check
            sanity_check_order_error(
                example["recording_id"],
                step,
                activity_name2recipe[_activity_name],
                previous_steps,
            )

            question_id = f"{example_id}_order"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                or (not check_if_target_error_exists(step, "Order Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "order",
                    "error_description": get_target_description(step, "Order Error"),
                    "question_id": question_id,
                    "is_noisy": check_errors(
                        previous_steps, ["Order Error", "Missing Step"]
                    ),
                }

            """
            create example for preparation error

            """
            question_id = f"{example_id}_preparation"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                # or (not check_if_target_verb(step, "Preparation Error", error_type2verbs))
                # # verb-based rough selection
                or (not check_if_target_error_exists(step, "Preparation Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "preparation",
                    "error_description": get_target_description(
                        step, "Preparation Error"
                    ),
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            """
            create example for measurement error

            """
            question_id = f"{example_id}_measurement"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                # or (not check_if_target_verb(step, "Measurement Error", error_type2verbs))
                # # verb-based rough selection
                or (not check_if_target_error_exists(step, "Measurement Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "measurement",
                    "error_description": get_target_description(
                        step, "Measurement Error"
                    ),
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            """
            create example for timing error

            """
            question_id = f"{example_id}_timing"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                # or (not check_if_target_verb(step, "Timing Error", error_type2verbs))
                # # verb-based rough selection
                or (not check_if_target_error_exists(step, "Timing Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "timing",
                    "error_description": get_target_description(step, "Timing Error"),
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            """
            create example for technique error

            """
            question_id = f"{example_id}_technique"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                # or (not check_if_target_verb(step, "Technique Error", error_type2verbs))
                # # verb-based rough selection
                or (not check_if_target_error_exists(step, "Technique Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "technique",
                    "error_description": get_target_description(
                        step, "Technique Error"
                    ),
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            """
            create example for temperature error

            """
            question_id = f"{example_id}_temperature"
            if (
                (step["step_id"] <= 0)  # skip for start step
                or (question_id in targets)  # avoid duplicates
                or is_overlap  # avoid edge cases
                # or (not check_if_target_verb(step, "Temperature Error", error_type2verbs))
                # # verb-based rough selection
                or (not check_if_target_error_exists(step, "Temperature Error"))
            ):
                pass
            else:
                targets[question_id] = target | {
                    "type": "temperature",
                    "error_description": get_target_description(
                        step, "Temperature Error"
                    ),
                    "question_id": question_id,
                    "is_noisy": check_errors(previous_steps),
                }

            # add this step to history
            if step["step_id"] > 0:  # skip for start step
                previous_steps.append(deepcopy(current_step))

    count = defaultdict(int)
    for target in targets.values():
        count[target["type"]] += 1

    logging.info(f"Total #prompt: {len(targets)} ({dict(count)})")

    check_end_time(targets.values())

    with open(args.dirpath_output / "all_examples.json", "w") as f:
        json.dump(list(targets.values()), f, indent=4)
        f.write("\n")


if __name__ == "__main__":
    parser = ArgumentParser(description="Create exmaples from CaptainCook4D")
    parser.add_argument(
        "--filepath_input",
        type=Path,
        help="filepath to input (annotation updated file)",
    )
    parser.add_argument(
        "--filepath_verbs", type=Path, help="filepath of error type to verbs mapping"
    )
    parser.add_argument(
        "--dirpath_graph", type=Path, help="dirpath to task graph annotation"
    )
    parser.add_argument(
        "--filepath_metadata_video", type=Path, help="filepath to video metadata"
    )
    parser.add_argument("--dirpath_output", type=Path, help="dirpath to output data")
    parser.add_argument("--dirpath_log", type=Path, help="log")

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.dirpath_log / "create_example.log"),
        ],
    )

    if not args.dirpath_log.exists():
        args.dirpath_log.mkdir(parents=True)
    if not args.dirpath_output.exists():
        args.dirpath_output.mkdir(parents=True)

    logging.info(f"Arguments: {vars(args)}")

    main(args)
