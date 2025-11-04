""" """

from argparse import ArgumentParser
import logging
from pathlib import Path
import json
from collections import defaultdict
import random


def get_stat(examples) -> None:
    """
    get statistics of data

    """

    logging.info(f"#total: {len(examples)}")

    count_type_pre = defaultdict(lambda: defaultdict(int))
    count_type_ans = defaultdict(lambda: defaultdict(int))
    count_type_err = defaultdict(lambda: defaultdict(int))
    count_type_nsy_ans = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    count_rec = defaultdict(int)

    for example in examples:
        count_type_pre[example["type"]][len(example["previous_steps"])] += 1
        count_rec[example["recording_id"]] += 1

        num_potential_ans = 0
        match example["type"]:
            case "next":
                num_potential_ans = len(example["next_steps"])
            case "missing":
                num_potential_ans = len(example["missing_steps"])
            case (
                "order"
                | "preparation"
                | "measurement"
                | "timing"
                | "technique"
                | "temperature"
            ):
                if example["error_description"].startswith(
                    "This step does not contain any"
                ):
                    num_potential_ans = 0
                else:
                    num_potential_ans = 1
            case _:
                pass
        count_type_ans[example["type"]][num_potential_ans] += 1

        num_err_step = (
            sum(["errors" in step for step in example["previous_steps"]])
            if example["is_noisy"]
            else 0
        )
        count_type_err[example["type"]][num_err_step] += 1

        count_type_nsy_ans[example["type"]][example["is_noisy"]][
            num_potential_ans > 0
        ] += 1

    logging.info("#previous steps")
    for _type, _count in count_type_pre.items():
        _count_sorted = {k: _count[k] for k in sorted(_count.keys())}
        logging.info(f"{_type:11}: {_count_sorted}")

    logging.info("")

    logging.info("#potential answers")
    for _type, _count in count_type_ans.items():
        _count_sorted = {k: _count[k] for k in sorted(_count.keys())}
        logging.info(f"{_type:11}: {_count_sorted}")

    logging.info("")

    logging.info("#errors in previous steps")
    for _type, _count in count_type_err.items():
        _count_sorted = {k: _count[k] for k in sorted(_count.keys())}
        logging.info(f"{_type:11}: {_count_sorted}")

    logging.info("")

    num_total_recording = len(set([x["recording_id"] for x in examples]))
    logging.info(f"#examples for one recording (total: {num_total_recording})")
    count_count_rec = defaultdict(int)
    for rec, count in count_rec.items():
        count_count_rec[count] += 1
    logging.info({k: count_count_rec[k] for k in sorted(count_count_rec.keys())})

    logging.info("")

    logging.info("Type-noisy-w/answer")
    for _type, _count_nsy_ans in count_type_nsy_ans.items():
        logging.info(_type)
        for _nsy in [True, False]:
            label = "Noisy" if _nsy else "Clean"
            logging.info(
                f"  [{label}] " f"{sum([x for x in _count_nsy_ans[_nsy].values()])}"
            )
            for _ans in [True, False]:
                label_ans = "w/ " if _ans else "w/o"
                logging.info(f"    [{label_ans} Ans] {_count_nsy_ans[_nsy][_ans]}")

    return None


def sample(
    _type: str,
    recording_examples: dict,
    num_target: int,
    max_potential_answer: int = 5,  # hard-coded
    max_errors: int = 5,  # hard-coded
) -> tuple[list, list]:
    """
    sample num_target examples evenly for each category as much as possibly
    * at most one example for each type from each recording
    * #candidate_answer <= 5

    """

    samples, remainings = [], []

    category_samples = defaultdict(lambda: defaultdict(list))
    for recording_id, examples in recording_examples.items():
        # categorize each example based on w_answer and is_noisy
        category_examples = defaultdict(lambda: defaultdict(list))
        for example in examples:
            match _type:
                case "next":
                    w_answer = len(example["next_steps"]) > 0
                case "missing":
                    w_answer = len(example["missing_steps"]) > 0
                case (
                    "order"
                    | "preparation"
                    | "measurement"
                    | "timing"
                    | "technique"
                    | "temperature"
                ):
                    if example["error_description"].startswith(
                        "This step does not contain any"
                    ):
                        w_answer = False
                    else:
                        w_answer = True
                case _:
                    logging.error(f"Undefined {_type=}")

            """
            skip examples
            * w/ more than max_error errors in previous steps
            * w/ more than max_potential_answer potential answers

            """
            num_err_step = (
                sum(["errors" in step for step in example["previous_steps"]])
                if example["is_noisy"]
                else 0
            )
            if (
                (num_err_step > max_errors)
                or (
                    _type == "next"
                    and len(example["next_steps"]) > max_potential_answer
                )
                or (
                    _type == "missing"
                    and len(example["missing_steps"]) > max_potential_answer
                )
            ):
                remainings.append(example)
            else:
                category_examples[example["is_noisy"]][w_answer].append(example)

        # sample at most one example for each category per recording
        for is_noisy, answer_examples in category_examples.items():
            for w_answer, _examples in answer_examples.items():
                if len(_examples) > 0:
                    random.shuffle(_examples)
                    category_samples[is_noisy][w_answer].append(_examples[0])
                    remainings += _examples[1:]

    match _type:
        case "next" | "missing":
            # sample target num of examples for each category
            for is_noisy, answer_samples in category_samples.items():
                num_w_answer = num_wo_answer = num_target // 4
                if (len(answer_samples[True]) < num_w_answer) and (
                    len(answer_samples[False]) < num_wo_answer
                ):
                    logging.warning(
                        f"#both w/ and w/o answer examples are under {num_w_answer}"
                    )
                elif len(answer_samples[True]) < num_w_answer:
                    num_wo_answer += num_w_answer - len(answer_samples[True])
                    num_w_answer = len(answer_samples[True])
                elif len(answer_samples[False]) < num_wo_answer:
                    num_w_answer += num_wo_answer - len(answer_samples[False])
                    num_wo_answer = len(answer_samples[False])
                else:
                    pass

                # sample w_answer == True
                _samples_w_answer = answer_samples[True]
                random.shuffle(_samples_w_answer)
                samples += _samples_w_answer[:num_w_answer]
                remainings += _samples_w_answer[num_w_answer:]

                # sample w_answer == False
                _samples_wo_answer = answer_samples[False]
                random.shuffle(_samples_wo_answer)
                samples += _samples_wo_answer[:num_wo_answer]
                remainings += _samples_wo_answer[num_wo_answer:]

        case (
            "order"
            | "preparation"
            | "measurement"
            | "timing"
            | "technique"
            | "temperature"
        ):
            """only w_answer == True"""
            # adjust #sample
            num_noisy = num_clean = num_target // 2
            if (len(category_samples[True][True]) < num_noisy) and (
                len(category_samples[False][True]) < num_clean
            ):
                logging.warning(f"#both noisy and clean examples are under {num_noisy}")
            elif len(category_samples[True][True]) < num_noisy:
                num_clean += num_noisy - len(category_samples[True][True])
                num_noisy = len(category_samples[True][True])
            elif len(category_samples[False][True]) < num_clean:
                num_noisy += num_clean - len(category_samples[False][True])
                num_clean = len(category_samples[False][True])
            else:
                pass

            # sample noisy
            _samples_noisy_w_answer = category_samples[True][True]
            random.shuffle(_samples_noisy_w_answer)
            samples += _samples_noisy_w_answer[:num_noisy]
            remainings += _samples_noisy_w_answer[num_noisy:]

            # sample clean
            _samples_clean_w_answer = category_samples[False][True]
            random.shuffle(_samples_clean_w_answer)
            samples += _samples_clean_w_answer[:num_clean]
            remainings += _samples_clean_w_answer[num_clean:]

        case _:
            logging.error(f"Undefined {_type=}")

    # check total num
    assert len(samples) + len(remainings) == sum(
        [len(x) for x in recording_examples.values()]
    )
    # check if any duplication exists
    ids = [x["question_id"] for x in samples]
    assert len(ids) == len(set(ids))
    ids = [x["question_id"] for x in remainings]
    assert len(ids) == len(set(ids))

    return samples, remainings


def main(args):
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    logging.info("Stats of all examples")
    get_stat(examples)

    type_recording_examples = defaultdict(lambda: defaultdict(list))
    for example in examples:
        type_recording_examples[example["type"]][example["recording_id"]].append(
            example
        )

    samples, remainings = [], []

    random.seed(args.seed)
    for _type, recording_examples in type_recording_examples.items():
        if args.target_num == 1000:
            num_target = 400 if _type in ["next", "missing"] else 50
        elif args.target_num == 10:
            num_target = 4 if _type in ["next", "missing"] else 1
        else:
            logging.error(f"Undefined {args.target_num}")
        logging.info(f"Sample {num_target:3} examples from {_type}")
        _samples, _remainings = sample(_type, recording_examples, num_target)
        samples += _samples
        remainings += _remainings
    logging.info("Stats of samples")
    get_stat(samples)

    assert len(samples) + len(remainings) == len(examples)

    with open(args.dirpath_output / f"samples_{args.target_num}.json", "w") as f:
        json.dump(samples, f, indent=4)
        f.write("\n")

    with open(args.dirpath_output / f"remainings_{args.target_num}.json", "w") as f:
        json.dump(remainings, f, indent=4)
        f.write("\n")


if __name__ == "__main__":
    parser = ArgumentParser(description="")
    parser.add_argument("--filepath_input", type=Path, help="filepath to input data")
    parser.add_argument("--dirpath_output", type=Path, help="dirpath to output")
    parser.add_argument("--target_num", type=int, default=1000)  # 10
    parser.add_argument("--seed", type=int, help="random seed", default=42)
    parser.add_argument("--dirpath_log", type=Path, help="log")

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.dirpath_log / "sample.log"),
        ],
    )

    if not args.dirpath_log.exists():
        args.dirpath_log.mkdir(parents=True)

    logging.info(f"Arguments: {vars(args)}")

    main(args)
