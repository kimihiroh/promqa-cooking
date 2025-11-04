"""
Check & Update original (erronous) annotation

"""

import logging
from copy import deepcopy
from collections import defaultdict


def update_step_description(examples):
    """
    correct (probably) annotation errors w.r.t. step description
    how it found: manual inspection
    solution: manual update

    """
    assert examples[26]["recording_id"] == "2_26"
    examples[26]["step_annotations"][13]["description"] = (
        "Microwave-Microwave for 1 more minute"
    )
    assert examples[219]["recording_id"] == "17_49"
    examples[219]["step_annotations"][4]["description"] = (
        "Add-1/2 teaspoon of chaat masala powder to the bowl"
    )

    return examples


def update_error_annotation(examples):
    """
    correct (probably) annotation errors w.r.t. order error annotation
    how it found: semi-automatic inspection
    solution: manual update

    """

    # error annotation mistake, i think
    # the order of microwaving is reverse
    assert examples[11]["recording_id"] == "1_36"
    (
        examples[11]["step_annotations"][4]["description"],
        examples[11]["step_annotations"][6]["description"],
    ) = (
        examples[11]["step_annotations"][6]["description"],
        examples[11]["step_annotations"][4]["description"],
    )
    (
        examples[11]["step_annotations"][4]["step_id"],
        examples[11]["step_annotations"][6]["step_id"],
    ) = (
        examples[11]["step_annotations"][6]["step_id"],
        examples[11]["step_annotations"][4]["step_id"],
    )
    assert examples[11]["step_annotations"][4]["step_id"] == 10
    assert examples[11]["step_annotations"][6]["step_id"] == 8

    # error annotation mistakes i think
    assert examples[12]["recording_id"] == "1_37"
    examples[12]["step_annotations"][1].pop("errors")

    # prob typo
    assert examples[13]["recording_id"] == "1_42"
    assert examples[13]["step_annotations"][4]["errors"][1]["description"] == (
        "Step performed after correct order"
    )
    examples[13]["step_annotations"][4]["errors"][1]["description"] = (
        "Step performed after incorrect order"
    )
    assert examples[13]["step_annotations"][5]["errors"][0]["description"] == (
        "Step performed after correct order"
    )
    examples[13]["step_annotations"][5]["errors"][0]["description"] = (
        "Step performed after incorrect order"
    )

    # update modified description
    assert examples[18]["recording_id"] == "2_3"
    assert examples[18]["step_annotations"][11]["modified_description"] == (
        "Microwave-Microwave the plate, covered, on high for 1.5 minutes"
    )
    examples[18]["step_annotations"][11]["modified_description"] = (
        "Microwave-Microwave the plate, covered, on high for 5 minutes"
    )
    assert examples[18]["step_annotations"][13]["modified_description"] == (
        "Microwave-Microwave the plate, covered, on high for 1.5 minutes"
    )
    examples[18]["step_annotations"][13]["modified_description"] = (
        "Microwave-Microwave the plate, covered, on high for 5 minutes"
    )

    # duplicate steps included
    assert examples[26]["recording_id"] == "2_26"
    assert examples[26]["step_annotations"][15]["step_id"] == 18
    examples[26]["step_annotations"].pop(15)

    # update modified description
    assert examples[44]["recording_id"] == "3_46"
    assert examples[44]["step_annotations"][4]["modified_description"] == (
        "add-Measure 1/8 teaspoon of salt and add it to the mug"
    )
    examples[44]["step_annotations"][4]["modified_description"] = (
        "add-Measure 1 teaspoon of salt and add it to the mug"
    )

    # this is not missing step, rather technique or prep error
    assert examples[61]["recording_id"] == "4_43"
    examples[61]["step_annotations"][8]["errors"].pop(0)

    # try to perform but did not, so remove this step
    assert examples[61]["recording_id"] == "4_43"
    assert examples[61]["step_annotations"][9]["step_id"] == 45
    examples[61]["step_annotations"].pop(9)
    assert examples[61]["step_annotations"][10]["step_id"] == 45

    # the order is not an error based on the task graph
    assert examples[62]["recording_id"] == "4_44"
    examples[62]["step_annotations"][12].pop("errors")
    examples[62]["step_annotations"][13].pop("errors")

    # error annotation mistake, i think
    assert examples[64]["recording_id"] == "5_2"
    (
        examples[64]["step_annotations"][14]["description"],
        examples[64]["step_annotations"][15]["description"],
    ) = (
        examples[64]["step_annotations"][15]["description"],
        examples[64]["step_annotations"][14]["description"],
    )
    (
        examples[64]["step_annotations"][14]["step_id"],
        examples[64]["step_annotations"][15]["step_id"],
    ) = (
        examples[64]["step_annotations"][15]["step_id"],
        examples[64]["step_annotations"][14]["step_id"],
    )

    # update modified description
    assert examples[73]["recording_id"] == "5_27"
    assert examples[73]["step_annotations"][6]["modified_description"] == (
        "spread-spread open filter in dripper to create a cone"
    )
    examples[73]["step_annotations"][6]["modified_description"] = (
        "spread-spread open improperly folded filter in dripper to create a cone"
    )

    # update modified description
    assert examples[104]["recording_id"] == "8_31"
    assert examples[104]["step_annotations"][2]["modified_description"] == (
        "Add-Add 1/5 teaspoon cinnamon to the mug"
    )
    examples[104]["step_annotations"][2]["modified_description"] = (
        "Add-Add 1/5 teaspoon cinnamon to the mug incorrectly"
    )

    # missing step should not have actual timestamp
    assert examples[139]["recording_id"] == "12_6"
    examples[139]["step_annotations"][8]["start_time"] = -1
    examples[139]["step_annotations"][8]["end_time"] = -1

    # I dont't think this is missing step, rather preparation error etc
    assert examples[149]["recording_id"] == "12_38"
    examples[149]["step_annotations"][0]["errors"].pop(0)

    # did not collect spilled corns, but I don't think this is order error
    assert examples[167]["recording_id"] == "13_44"
    examples[167]["step_annotations"][2].pop("errors")

    # update modified description
    assert examples[177]["recording_id"] == "15_29"
    assert examples[177]["step_annotations"][17]["modified_description"] == (
        "Transfer-Transfer it to a serving bowl"
    )
    examples[177]["step_annotations"][17]["modified_description"] = (
        "Transfer-Transfer it to a serving bowl with spilling"
    )

    # update modified description
    assert examples[179]["recording_id"] == "15_33"
    assert examples[179]["step_annotations"][10]["modified_description"] == (
        "Mix-Mix well tomato puree with contents in the pan"
    )
    examples[179]["step_annotations"][10]["modified_description"] = (
        "Mix-Mix tomato puree with contents in the pan insufficiently"
    )

    # did not miss saute step
    assert examples[182]["recording_id"] == "15_41"
    assert examples[182]["step_annotations"][18]["step_id"] == 148
    examples[182]["step_annotations"][18]["start_time"] = 501
    examples[182]["step_annotations"][18]["end_time"] = 690
    examples[182]["step_annotations"][18].pop("errors")
    assert examples[182]["step_annotations"][13]["step_id"] == 142
    examples[182]["step_annotations"][13]["errors"].pop(1)

    # add missing step annotation
    for idx, recording_id, step_idx in [
        (221, "18_3", 12),
        (223, "18_11", 12),
        (225, "18_19", 12),
        (227, "18_27", 12),
        (230, "18_33", 12),
        (234, "18_101", 12),
    ]:
        assert examples[idx]["recording_id"] == recording_id
        examples[idx]["step_annotations"][step_idx]["errors"] = [
            {"tag": "Missing Step", "description": "Skipped this step"}
        ]
        examples[idx]["modified_description"] = "Skipped this step"

    # update modified description
    assert examples[268]["recording_id"] == "22_2"
    assert examples[268]["step_annotations"][12]["modified_description"] == (
        "stir-stir gently with a wooden spoon so the egg that sets on the base of the pan moves to enable the uncooked egg to flow into the space"
    )
    examples[268]["step_annotations"][12]["modified_description"] = (
        "stir-stir gently with a wooden spoon but the egg that sets on the base of the pan was cooked so fast that it cannot be moved to enable the uncooked egg to flow into the space"
    )

    # update modified description
    assert examples[278]["recording_id"] == "22_31"
    assert examples[278]["step_annotations"][12]["modified_description"] == (
        "stir-stir gently with a wooden spoon so the egg that sets on the base of the pan moves to enable the uncooked egg to flow into the space"
    )
    examples[278]["step_annotations"][12]["modified_description"] = (
        "stir-stir gently with a wooden spoon so the egg that sets on the base of the pan moves to enable the uncooked egg to flow into the space, but the stirring is insufficient"
    )

    # update modified description
    assert examples[297]["recording_id"] == "23_32"
    assert examples[297]["step_annotations"][4]["modified_description"] == (
        "Take-Take 1 bell pepper"
    )
    examples[297]["step_annotations"][4]["modified_description"] = (
        "Take-Take 1 soiled bell pepper"
    )

    # cut one more tomato, but i don't think this is order error
    assert examples[282]["recording_id"] == "22_40"
    examples[282]["step_annotations"][2].pop("errors")
    # error annotation mistake
    examples[282]["step_annotations"][4]["errors"].pop(1)

    # did not chopping correctly, but i don't think this is order error
    assert examples[283]["recording_id"] == "22_41"
    examples[283]["step_annotations"][2].pop("errors")

    # the step order does not match with the order based on start time
    assert examples[304]["recording_id"] == "25_4"
    examples[304]["step_annotations"][7], examples[304]["step_annotations"][8] = (
        examples[304]["step_annotations"][8],
        examples[304]["step_annotations"][7],
    )

    # update modified description
    assert examples[312]["recording_id"] == "25_41"
    assert examples[312]["step_annotations"][0]["modified_description"] == (
        "Cut-Cut 1/4 block or 3 ounces of fresh tofu into large cubes (about 1 in x 1 in)"
    )
    examples[312]["step_annotations"][0]["modified_description"] = (
        "Cut-Cut 1/4 block or 3 ounces of fresh tofu into pyramid shapes"
    )

    # the step order does not match with the order based on start time
    assert examples[310]["recording_id"] == "25_22"
    examples[310]["step_annotations"][7], examples[310]["step_annotations"][8] = (
        examples[310]["step_annotations"][8],
        examples[310]["step_annotations"][7],
    )

    # history contains order error, but this step itself is not order error
    assert examples[346]["recording_id"] == "27_45"
    examples[346]["step_annotations"][8].pop("errors")
    examples[346]["step_annotations"][9]["errors"].pop(1)
    examples[346]["step_annotations"][10]["errors"].pop(1)

    # partially missing step: measured but did not put in bowl
    assert examples[356]["recording_id"] == "28_25"
    examples[356]["step_annotations"][0]["start_time"] = -1
    examples[356]["step_annotations"][0]["end_time"] = -1

    # update modified description
    assert examples[366]["recording_id"] == "29_5"
    assert examples[366]["step_annotations"][4]["errors"][0]["description"] == (
        "Used a wooden spoon instead of a brush"
    )
    examples[366]["step_annotations"][4]["errors"][0]["description"] = (
        "Used a wooden spatula instead of a brush"
    )
    assert examples[366]["step_annotations"][4]["modified_description"] == (
        "Brush-Brush 2 slices of baguette with olive oil on both sides using a wooden spoon"
    )
    examples[374]["step_annotations"][4]["modified_description"] = (
        "Brush-Brush 2 slices of baguette with olive oil on both sides using a wooden spatula"
    )

    # update modified description
    assert examples[374]["recording_id"] == "29_28"
    assert examples[374]["step_annotations"][0]["modified_description"] == (
        "add-1/4 tsp salt to a bowl"
    )
    examples[374]["step_annotations"][0]["modified_description"] = (
        "add-1/4 tsp salt to a bowl twice with a wet teaspoon"
    )

    return examples


def update_step_order(examples):
    """
    sort steps based on timestamp
    why: the order of steps in the annotation does not match with the order of timestamp

    """
    new_examples = []
    for example in examples:
        new_example = deepcopy(example)
        new_example["step_annotations"] = sorted(
            new_example["step_annotations"], key=lambda step: step["start_time"]
        )
        new_examples.append(new_example)

    return new_examples


def check_missing_step_annotation(examples):
    """
    check if there are steps with -1 w/o missing step annotation

    """

    for example in examples:
        for step in example["step_annotations"]:
            # -1 => missing step
            if step["start_time"] == -1:
                if (
                    step["end_time"] == -1
                    and "errors" in step
                    and "Missing Step" in [x["tag"] for x in step["errors"]]
                ):
                    pass
                else:
                    logging.warning(
                        f"No missing step annotation for step w/ time == -1: "
                        f"{example['recording_id']}"
                    )

            # missing step => -1
            if "errors" in step and "Missing Step" in [
                x["tag"] for x in step["errors"]
            ]:
                if step["start_time"] == step["end_time"] == -1:
                    pass
                else:
                    logging.warning(
                        f"timestamp != -1 for missing steps: "
                        f"{example['recording_id']}"
                    )

    return None


def check_timestamp_order(examples):
    """
    check if the list of steps is ordered based on timestamp

    note:
       * not checking this: step['end_time'] >= prev_endtime

    """
    exceptions = [  # two steps at once
        13,
        16,
        22,
        "5_3",
        "26_136",
    ]
    for example in examples:
        prev_starttime, prev_endtime = 0, 0
        for idx, step in enumerate(example["step_annotations"]):
            if "errors" in step and "Missing Step" in [
                x["tag"] for x in step["errors"]
            ]:
                continue
            diff = abs(step["start_time"] - prev_starttime) + abs(
                step["end_time"] - prev_endtime
            )
            if diff < 2:
                if (
                    example["activity_id"] in exceptions
                    or example["recording_id"] in exceptions
                ):
                    pass
                else:
                    logging.warning(
                        f"Very close timestamp {example['recording_id']} "
                        f"\nCurrent: {step}\nPrev: {example['step_annotations'][idx-1]}"
                    )
            if (
                step["start_time"] >= prev_starttime
                and step["end_time"] > step["start_time"]
            ):
                prev_starttime = step["start_time"]
                prev_endtime = step["end_time"]
            else:
                logging.warning(
                    f"timestamp is not ordered correctly.  {example['recording_id']} "
                    f"\nCurrent: {step}\nPrev: {example['step_annotations'][idx-1]}"
                )
    return None


def adjust_step_id(examples, activity_id2min_step_id, activity_id2recipe):
    """
    adjust step ids in annotation to align with the ones in task graphs.

    [step]
    1. use step id in task graph if description matches
    2. if there are multiple identical description steps, use manual rules
    """

    for example in examples:
        activity_id = example["activity_id"]
        recipe = activity_id2recipe[activity_id]
        description2step_id = {desc: idx for idx, desc in recipe["steps"].items()}
        steps_in_recipe = [x for x in recipe["steps"].values()]

        check = {
            2: {7: [13, 8], 5: [7, 5, 5]},  # 2_42 has three steps with step_id==5
            10: {1: [14, 1, 3, 3]},  # 10_42 has four steps with step_id==1
            20: {32: [3, 13]},
        }
        for step in example["step_annotations"]:
            if steps_in_recipe.count(step["description"]) == 1:
                new_step_id = description2step_id[step["description"]]
                step["step_id"] = new_step_id
            elif steps_in_recipe.count(step["description"]) > 1:
                adjusted_step_id = (
                    step["step_id"] - activity_id2min_step_id[activity_id]
                )
                if adjusted_step_id in check[activity_id]:
                    step["step_id"] = check[activity_id][adjusted_step_id].pop(0)
            else:
                logging.error("Step not found in graph")

    return examples


def sanity_check_adjustment(examples, activity_id2recipe):
    """
    there are cases where one step in recipe is performed multiple times in recordings.
    <= i think this would not be a problem. so ignore this case.

    """
    # sanity check
    for example in examples:
        activity_id = example["activity_id"]
        recipe = activity_id2recipe[activity_id]

        ids = [x["step_id"] for x in example["step_annotations"]]
        # check no duplicate step ids
        if len(ids) != len(set(ids)):
            if (example["recording_id"] == "2_42" and ids.count(5) == 2) or (
                example["recording_id"] == "10_42" and ids.count(3) == 2
            ):
                pass
            else:
                count = defaultdict(list)
                for step in example["step_annotations"]:
                    count[step["step_id"]].append(step["description"])
                for step_id, descriptions in count.items():
                    # when the same step is still found multiple times in recordings
                    if len(descriptions) > 1:
                        # check if they have the same description
                        assert len(set(descriptions)) == 1
                        description = descriptions[0]

                        # check if recipe contains only one that description
                        if [x for x in recipe["steps"].values()].count(
                            description
                        ) == 1:
                            pass
                        else:
                            logging.error(
                                f"duplicate still exist in {example['recording_id']}"
                            )
                    else:
                        # no problem
                        pass

        # check all step id+description in task graphs
        for step in example["step_annotations"]:
            if step["step_id"] in recipe["steps"]:
                if step["description"] == recipe["steps"][step["step_id"]]:
                    pass
                else:
                    logging.error(
                        f"description of step id {step['step_id']} does not match "
                        f"in recording {example['recording_id']}"
                    )
            else:
                logging.error(
                    f"step id {step['step_id']} in recording {example['recording_id']} "
                    f"not found in task graph"
                )
    return None
