# The example workflow from the guide: Source A and Source B feed into Combine.

nodes = [
    {
        "id": "a",
        "name": "Source A",
        "type": "emit_json",
        "config": {"value": {"value": 3}},
    },
    {
        "id": "b",
        "name": "Source B",
        "type": "emit_json",
        "config": {"value": {"value": 4}},
    },
    {
        "id": "c",
        "name": "Combine",
        "type": "combine_inputs",
        "config": {},
    },
]

# ("a", "c") means: A must finish before C
edges = [("a", "c"), ("b", "c")]

workflow = {
    "name": "Example workflow",
    "nodes": nodes,
    "edges": edges,
}

if __name__ == "__main__":
    print("Workflow:", workflow["name"])
    for node in workflow["nodes"]:
        print(" - task:", node["name"])
    for source, target in workflow["edges"]:
        print(" - arrow:", source, "->", target)