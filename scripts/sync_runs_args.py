#!/usr/bin/env python3
import sys, os, pathlib, yaml, subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]


def find_action_files():
    # Scan repo for action.yml or action.yaml (common locations: root, subactions)
    for p in REPO.rglob("action.y*ml"):
        # ignore things in .git
        if ".git" in p.parts:
            continue
        yield p


def build_args_from_inputs(inputs_ordered):
    args = []
    for key in inputs_ordered:
        args.extend([f"--{key}", f"${{{{ inputs.{key} }}}}"])
    return args


def normalize_pairs(args):
    """Return list of (flag_key, expr_key). Return None if shape is not valid."""
    if not isinstance(args, list) or len(args) % 2 != 0:
        return None
    pairs = []
    for i in range(0, len(args), 2):
        flag, val = args[i], args[i + 1]
        if not (isinstance(flag, str) and flag.startswith("--")):
            return None
        k = flag[2:]
        prefix, suffix = "${{ inputs.", " }}"
        if not (
            isinstance(val, str) and val.startswith(prefix) and val.endswith(suffix)
        ):
            return None
        expr_key = val[len(prefix) : -len(suffix)]
        pairs.append((k, expr_key))
    return pairs


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f), f.read()


def dump_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def sync_file(path):
    data, original_text = load_yaml(path)
    runs = (data or {}).get("runs") or {}
    if str(runs.get("using", "")).lower() != "docker":
        return False, "skip (not docker)"

    inputs = data.get("inputs") or {}
    # Preserve declaration order: PyYAML preserves insertion order in 3.7+
    input_keys = list(inputs.keys())

    # Ensure args exist as list
    current_args = runs.get("args", [])
    desired_args = build_args_from_inputs(input_keys)

    ok_pairs = normalize_pairs(current_args)
    current_keys = [k for (k, _) in ok_pairs] if ok_pairs is not None else None
    current_exprs = [k for (_, k) in ok_pairs] if ok_pairs is not None else None

    if current_args == desired_args:
        return False, "already in sync"

    # If mismatched (shape/order/missing/extra), rewrite args
    runs["args"] = desired_args
    data["runs"] = runs
    dump_yaml(path, data)
    return True, "updated"


def main():
    any_changes = False
    updated_files = []
    skipped = []
    for path in find_action_files():
        changed, note = sync_file(path)
        if note.startswith("skip"):
            skipped.append((str(path), note))
        elif changed:
            any_changes = True
            updated_files.append(str(path))

    # Print a small summary for the workflow logs
    if updated_files:
        print("Updated:", ", ".join(updated_files))
    if skipped:
        print("Skipped:", ", ".join(f"{p} ({n})" for p, n in skipped))

    # Surface result to GitHub Actions
    # HAS_CHANGES=1 means we rewrote at least one file
    print(f"HAS_CHANGES={'1' if any_changes else '0'}")

    # Also write to GITHUB_OUTPUT if present for downstream steps
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"HAS_CHANGES={'1' if any_changes else '0'}\n")


if __name__ == "__main__":
    sys.exit(main())
