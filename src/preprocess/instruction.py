"""
Preprocess videos and instructions

Create
* status image
* trimmed video
* sampled frames
* sampled frames after resizing

"""

from argparse import ArgumentParser
import logging
from pathlib import Path
import json
import pydot
from tqdm import tqdm
from datetime import datetime


def get_date(granularity="min") -> str:
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


def load_data(filepath: Path) -> list[dict[str, str | float]]:
    with open(filepath, "r") as f:
        return json.load(f)


def get_activity_name2recipe(filepath: Path):
    """
    return mapping from activity name to recipe graph

    """

    with open(filepath, "r") as f:
        data = json.load(f)

    name2recipe = {}
    for example in data.values():
        name2recipe[example["name"]] = example

    return name2recipe


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


def create_recipe_image(
    previous_steps: list,
    current_step: dict,
    recipe: dict,
    filepath_output: Path,
) -> None:
    """
    create recipe image

    Note:
    * step description is from recipe
    * caption is modefied description, w/ error information
    * previous steps are green box
    * current step is orange octagon
    * others are dashed box

    """

    G = pydot.Dot(graph_type="digraph")
    id2prev = {x["step_id"]: x for x in previous_steps} | {0: "START"}
    id2node = {}
    for step_id, step in recipe["steps"].items():
        if int(step_id) in id2prev:
            _step = id2prev[int(step_id)]
            node = pydot.Node(
                f"{step_id}. {add_newline(step)}",
                shape="box",
                color="forestgreen",
                style="solid" if "errors" in _step else "bold",
                xlabel="⚠︎" if "errors" in _step else "",
            )
        elif int(step_id) == current_step["step_id"]:
            node = pydot.Node(
                f"{step_id}. {add_newline(step)}",
                shape="box",
                color="darkorange",
                style="diagonals, solid"
                if "errors" in current_step
                else "diagonals, bold",
                xlabel="⚠︎" if "errors" in current_step else "",
            )
        else:
            node = pydot.Node(
                f"{step_id}. {add_newline(step)}", shape="box", style="dotted"
            )
        id2node[step_id] = node
        G.add_node(node)

    for edge in recipe["edges"]:
        edge = pydot.Edge(
            id2node[str(edge[0])],
            id2node[str(edge[1])],
        )
        G.add_edge(edge)

    G.write_png(filepath_output)

    return None


def create_folders(dirpaths: list[Path]) -> None:
    """create folders if not exists"""
    for dirpath in dirpaths:
        if not dirpath.exists():
            logging.info(f"Creating dir: {str(dirpath)}")
            dirpath.mkdir(parents=True)


def main(args):
    with open(args.filepath_input, "r") as f:
        examples = json.load(f)

    recipes = get_activity_name2recipe(args.filepath_graph)

    dirpath_image = args.dirpath_output / "graphs" / "status"
    if not dirpath_image.exists():
        dirpath_image.mkdir(parents=True)

    """
    create corresponding partial graph
    """
    for example in tqdm(examples):
        # 1. create corresponding partial graph
        filepath_image = (
            args.dirpath_output / "graphs" / "status" / f"{example['example_id']}.png"
        )
        if not filepath_image.exists():
            create_recipe_image(
                previous_steps=example["previous_steps"],
                current_step=example["current_step"],
                recipe=recipes[example["activity_name"]],
                filepath_output=filepath_image,
            )


if __name__ == "__main__":
    parser = ArgumentParser(description="Preprocess videos and instructions")
    parser.add_argument("--filepath_input", type=Path, help="filepath to input data")
    parser.add_argument("--filepath_graph", type=Path, help="filepath to graph")
    parser.add_argument("--dirpath_output", type=Path, help="dirpath_output")
    parser.add_argument("--dirpath_log", type=Path, help="dirpath for log")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                args.dirpath_log / f"preprocess_instruction_{get_date()}.log"
            ),
        ],
    )

    if not args.dirpath_log.exists():
        args.dirpath_log.mkdir(parents=True)
    if not args.dirpath_output.exists():
        args.dirpath_output.mkdir(parents=True)

    logging.info(f"Arguments: {vars(args)}")

    main(args)
