"""
Update CaptainCook4D annotation
* update labels
* add start step

"""

from argparse import ArgumentParser
import logging
from pathlib import Path
import json
import networkx as nx
import pydot
from copy import deepcopy
from collections import defaultdict
from utils_update_annotation import (
    update_step_description,
    update_error_annotation,
    update_step_order,
    check_missing_step_annotation,
    check_timestamp_order,
    adjust_step_id,
    sanity_check_adjustment,
)


def get_activity_id2name(path: Path) -> dict[int, str]:
    """
    return activity id 2 name mapping
    e.g.,
        * {1: 'Microwave Egg Sandwich', ...}

    """

    with open(path, "r") as f:
        examples = json.load(f)

    id2name = {}
    for _, example in examples.items():
        id2name[example["activity_id"]] = example["activity_name"]

    return id2name


def add_newline(string):
    """for better text visualization in graph"""
    words = string.split()
    new_string = ""
    for idx, word in enumerate(words[:20]):
        if idx % 5 == 0:
            new_string += f"{word}\\n"
        else:
            new_string += f"{word} "

    return new_string.strip()


def get_activity_id2recipe(dirpath: Path, activity_id2name):
    """
    return mapping from activity id to recipe graph
    e.g.,
    * id -> graph and steps

    """
    name2id = {
        name.lower().replace(" ", ""): idx for idx, name in activity_id2name.items()
    }
    id2recipe = {}
    for filepath in dirpath.glob("*.json"):
        idx = name2id[filepath.stem]

        with open(filepath, "r") as f:
            data = json.load(f)

        G = nx.DiGraph()
        G.add_edges_from(data["edges"])

        G_pydot = pydot.Dot(graph_type="digraph")
        id2node = {}
        for step_id, step in data["steps"].items():
            node = pydot.Node(
                f"{step_id}. {add_newline(step)}",
                shape="box",
            )
            G_pydot.add_node(node)
            id2node[step_id] = node

        for edge in data["edges"]:
            edge = pydot.Edge(
                id2node[str(edge[0])],
                id2node[str(edge[1])],
            )
            G_pydot.add_edge(edge)

        id2recipe[idx] = {
            "graph": G,
            "graph_pydot": G_pydot,
            "steps": {int(k): v for k, v in data["steps"].items()},
            "edges": data["edges"],
        }

    return id2recipe


def get_activity_id2min_step_id(filepath):
    """
    return mapping from activity id to minimum step id

    """
    with open(filepath, "r") as f:
        data = json.load(f)
    activity_id2start_index = {}
    for activity_id, ids in data.items():
        activity_id2start_index[int(activity_id)] = min(ids) - 1

    return activity_id2start_index


def get_end_time_for_start(steps) -> float:
    """
    get end time for start step == the start time of the 1st action
    note: the start time of the 1st action might be 0

    """
    for step in steps:
        if step["start_time"] >= 0:
            return step["start_time"]

    return 0


def main(args):
    # this is used to update step id
    activity_id2min_step_id = get_activity_id2min_step_id(args.filepath_step)

    activity_id2name = get_activity_id2name(args.filepath_activity)

    activity_id2recipe = get_activity_id2recipe(args.dirpath_graph, activity_id2name)

    # load annotation
    with open(args.filepath_error, "r") as f:
        examples = json.load(f)

    # udpate annotation
    examples = update_step_description(examples)
    examples = update_error_annotation(examples)

    # warning: this should be done after both manual updates
    examples = update_step_order(examples)

    # to match the step id on recipe
    examples = adjust_step_id(examples, activity_id2min_step_id, activity_id2recipe)

    sanity_check_adjustment(examples, activity_id2recipe)
    check_missing_step_annotation(examples)
    check_timestamp_order(examples)

    new_examples = []
    for example in examples:
        new_example = deepcopy(example)
        new_example["activity_name"] = activity_id2name[example["activity_id"]]

        # add start so that next questions can be created
        start_step = {
            "description": "Start-Start cooking.",
            "step_id": -1,
            "start_time": 0,
            "end_time": get_end_time_for_start(example["step_annotations"]),
        }
        new_example["step_annotations"] = [start_step] + example["step_annotations"]

        new_examples.append(new_example)

    # check no duplicate start step exists
    assert len(examples) == len(new_examples)
    for example, new_example in zip(examples, new_examples):
        assert example["recording_id"] == new_example["recording_id"]
        assert len(example["step_annotations"]) + 1 == len(
            new_example["step_annotations"]
        )

    with open(args.dirpath_output / "original_updated.json", "w") as f:
        json.dump(new_examples, f, indent=4)
        f.write("\n")

    # compile a list of verbs for each error to limit answer==none questions
    error2verbs = defaultdict(list)
    for example in new_examples:
        for step in example["step_annotations"]:
            verb = step["description"].split("-")[0].lower()
            if "errors" in step:
                for error in step["errors"]:
                    error2verbs[error["tag"]].append(verb)
    for error, verbs in error2verbs.items():
        error2verbs[error] = sorted(list(set(verbs)))

    with open(args.dirpath_output / "error_type_to_verbs.json", "w") as f:
        json.dump(error2verbs, f, indent=4)
        f.write("\n")

    # collect graph into one file
    logging.info("Creating recipe images")
    dirpath_graph_images = args.dirpath_output / "graphs" / "raw"
    if not dirpath_graph_images.exists():
        dirpath_graph_images.mkdir(parents=True)
    activity_id2graph = {}
    for activity_id, name in activity_id2name.items():
        recipe = activity_id2recipe[activity_id]
        activity_id2graph[activity_id] = {
            "name": name,
            "steps": recipe["steps"],
            "edges": recipe["edges"],
        }
        recipe["graph_pydot"].write_png(dirpath_graph_images / f"{activity_id}.png")

    with open(args.dirpath_output / "all_graphs.json", "w") as f:
        json.dump(activity_id2graph, f, indent=4)
        f.write("\n")


if __name__ == "__main__":
    parser = ArgumentParser(description="Update CaptainCook4D annotation")
    parser.add_argument(
        "--filepath_error", type=Path, help="filepath to error annotation"
    )
    parser.add_argument(
        "--filepath_activity", type=Path, help="filepath to activity annotation"
    )
    parser.add_argument(
        "--filepath_step", type=Path, help="filepath to step annotation"
    )
    parser.add_argument(
        "--dirpath_graph", type=Path, help="dirpath to task graph annotation"
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
            logging.FileHandler(args.dirpath_log / "update_annotation.log"),
        ],
    )

    if not args.dirpath_log.exists():
        args.dirpath_log.mkdir(parents=True)

    if not args.dirpath_output.exists():
        args.dirpath_output.mkdir(parents=True)

    logging.info(f"Arguments: {vars(args)}")

    main(args)
