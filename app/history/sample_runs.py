# Fake run results, in the SAME shape as Person 4's run_workflow() output.
# tasks is a dictionary keyed by node id.
# attempts is a list with one record per try.

runs = [
    # Run 1: everything works on the first try
    {
        "id": 1,
        "status": "Success",
        "outputs": {
            "a": {"value": 3},
            "b": {"value": 4},
            "c": {"inputs": {"a": {"value": 3}, "b": {"value": 4}}},
        },
        "tasks": {
            "a": {"status": "Success", "output": {"value": 3}, "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"value": 3}, "error": None}]},
            "b": {"status": "Success", "output": {"value": 4}, "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"value": 4}, "error": None}]},
            "c": {"status": "Success",
                  "output": {"inputs": {"a": {"value": 3}, "b": {"value": 4}}},
                  "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"inputs": {"a": {"value": 3},
                                                      "b": {"value": 4}}},
                                "error": None}]},
        },
    },
    # Run 2: task b fails once, then works on the retry
    {
        "id": 2,
        "status": "Success",
        "outputs": {
            "a": {"value": 3},
            "b": {"message": "Demo task succeeded"},
            "c": {"inputs": {"a": {"value": 3},
                             "b": {"message": "Demo task succeeded"}}},
        },
        "tasks": {
            "a": {"status": "Success", "output": {"value": 3}, "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"value": 3}, "error": None}]},
            "b": {"status": "Success",
                  "output": {"message": "Demo task succeeded"}, "error": None,
                  "attempts": [
                      {"attempt": 1, "status": "Failed", "output": None,
                       "error": "RuntimeError: Demo task failed on purpose."},
                      {"attempt": 2, "status": "Success",
                       "output": {"message": "Demo task succeeded"},
                       "error": None},
                  ]},
            "c": {"status": "Success",
                  "output": {"inputs": {"a": {"value": 3},
                                        "b": {"message": "Demo task succeeded"}}},
                  "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"inputs": {"a": {"value": 3},
                                                      "b": {"message": "Demo task succeeded"}}},
                                "error": None}]},
        },
    },
    # Run 3: task b fails every time, so task c is skipped
    {
        "id": 3,
        "status": "Failed",
        "outputs": {"a": {"value": 3}},
        "tasks": {
            "a": {"status": "Success", "output": {"value": 3}, "error": None,
                  "attempts": [{"attempt": 1, "status": "Success",
                                "output": {"value": 3}, "error": None}]},
            "b": {"status": "Failed", "output": None,
                  "error": "RuntimeError: Demo task failed on purpose.",
                  "attempts": [
                      {"attempt": 1, "status": "Failed", "output": None,
                       "error": "RuntimeError: Demo task failed on purpose."},
                      {"attempt": 2, "status": "Failed", "output": None,
                       "error": "RuntimeError: Demo task failed on purpose."},
                  ]},
            "c": {"status": "Skipped", "output": None,
                  "error": "Skipped because task 'b' failed.",
                  "attempts": []},
        },
    },
]


if __name__ == "__main__":
    for run in runs:
        parts = []
        for node_id, task in run["tasks"].items():
            parts.append(f"{node_id}: {task['status']} ({len(task['attempts'])} tries)")
        print(f"Run {run['id']} | {run['status']} | " + " | ".join(parts))