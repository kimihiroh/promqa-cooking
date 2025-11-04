"""
flask app for verification

session:
- current_id: the index that the page is showing

"""

from flask import Flask, render_template, request, redirect, url_for, session
import json
import logging
from pathlib import Path
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

config = {  # hard-coded
    "num_a": 5
}


# load data
def load_data() -> list:
    """
    load data from file
    * if in progress file exists, load from it.
    * if not, load from input
    """

    # check if annotation is in progress
    filepath_output = Path(os.getenv("FILEPATH_OUTPUT"))
    if filepath_output.exists():
        with open(filepath_output, "r") as f:
            examples = json.load(f)
    else:
        filepath_input = Path(os.getenv("FILEPATH_INPUT"))
        with open(filepath_input, "r") as f:
            examples = json.load(f)
    return examples


def get_latest_id(examples: list) -> int:
    """

    note:
    * check if this is not reset when opened in diff tab/browser. <- seems not

    """

    latest_id = 0
    for idx, example in enumerate(examples):
        if "judge" in example and example["judge"]:
            latest_id = idx + 1
    if latest_id >= len(examples):
        latest_id -= 1
    return latest_id


def format_html(steps: list) -> str:
    output = ""
    for step in steps:
        output += f"- {step['step_id']}: {step['description']}\n"
        if "errors" in step:
            for error in step["errors"]:
                output += f"    - [{error['tag']}] {error['description']}\n"

    return output.strip() if output else None


def save_data(examples: list) -> None:
    filepath = Path(os.getenv("FILEPATH_OUTPUT"))
    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True)
    with open(filepath, "w") as f:
        json.dump(examples, f, indent=4)
        f.write("\n")


@app.route("/", methods=["GET"])
def annotate():
    """main page"""

    global config

    examples = load_data()

    if "current_id" not in session or not session["current_id"]:
        session["current_id"] = 0

    if session["current_id"] >= len(examples):
        session["current_id"] = len(examples) - 1

    example = examples[session["current_id"]]
    filepath_video_high = f"gopro/resolution_4k/{example['recording_id']}_4K.mp4"
    filepath_video_low = f"gopro/resolution_360p/{example['recording_id']}_360p.mp4"

    current_step_html = "None"
    if example["current_step"]["step_id"] >= 0:
        current_step_html = format_html([example["current_step"]])

    data = {
        "question_template": "question.html",
        "answer_template": "answer.html",
        "js_filename": "base.js",
        "question_type": example["type"],
        "prev_step_status": "noisy" if example["is_noisy"] else "clean",
        "activity_name": example["activity_name"],
        "graph": f"graphs/status/{example['example_id']}.png",
        "video_low": filepath_video_low,
        "video_high": filepath_video_high,
        "example_id": example["example_id"],
        "previous_steps_html": format_html(example["previous_steps"]),
        "current_step_html": current_step_html,
        "total_num": len(examples),
        "current_id": session["current_id"] + 1,
        "end_time": example["end_time"][3:],
        "num_a": config["num_a"],
        "candidate_q": example["question"],
        "judge": example["judge"] if "judge" in example else {},
    }

    answers = {}
    for aid, answer in enumerate(example["answers"]):
        answers[f"candidate_a{aid+1}"] = answer

    page = render_template("base.html", answers=answers, **data)
    return page


@app.route("/", methods=["POST"])
def submit():
    """

    todo:
    * terminate the app automatically?
    """

    global config

    examples = load_data()

    judge = {"question": None, "answers": [], "comment": []}

    judge_question = request.form.get("judge_q", None)
    if judge_question == "false":
        judge_question = False
    elif judge_question == "true":
        judge_question = True
    else:
        logging.error(f"Question judgement is missing, {session['current_id']=}")
    judge["question"] = judge_question

    # better to limit the num to actual answers?
    # <- maybe okay to leave as is cz of access in js code
    if judge_question:
        for _aid in range(len(examples[session["current_id"]]["answers"])):
            judge_answer = request.form.get(f"judge_a{_aid+1}", None)
            if judge_answer == "false":
                judge_answer = False
            elif judge_answer == "true":
                judge_answer = True
            else:
                logging.error(
                    f"Answer judgement is missing, {session['current_id']=}, {_aid=}"
                )
            judge["answers"].append(judge_answer)

        comment = request.form.get("comment", None)
        if comment:
            judge["comment"] = [x.strip() for x in comment.split(";")]

    examples[session["current_id"]]["judge"] = judge

    save_data(examples)

    if session["current_id"] + 1 < len(examples):
        session["current_id"] = session["current_id"] + 1
    else:
        logging.info("Annotation completed.")

    return redirect(url_for("annotate"))


@app.route("/go_back", methods=["GET"])
def go_back():
    """Navigate to the previous question"""
    if session["current_id"] > 0:
        session["current_id"] = session["current_id"] - 1
    else:
        pass  # nothing happens when this is the first example
    return redirect(url_for("annotate"))


@app.route("/go_next", methods=["GET"])
def go_next():
    """Navigate to the next question up to the latest example"""
    examples = load_data()
    latest_id = get_latest_id(examples)
    if session["current_id"] + 1 <= latest_id:
        session["current_id"] = session["current_id"] + 1
    else:
        pass  # nothing happens when this is the first example
    return redirect(url_for("annotate"))


@app.route("/return_latest", methods=["GET"])
def return_latest():
    """# Navigate to the latest question"""
    examples = load_data()
    session["current_id"] = get_latest_id(examples)
    return redirect(url_for("annotate"))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[logging.StreamHandler()],
    )

    # todo: add password
    app.run(debug=True)
