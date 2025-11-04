# PR Review Agent: Keep `runs.args` in sync with `inputs` (Docker GitHub Action)

**Purpose:** Ensure Docker-based GitHub Actions keep the `runs.args` list exactly synchronized with the `inputs` schema. When `inputs` change, `runs.args` must be updated in the same PR to match. Treat `inputs` as authoritative.

---

## When to Run
Trigger this check whenever a PR modifies any `action.yml` / `action.yaml` file, especially changes under:
- `inputs` (added/removed/renamed keys, or reordering), or
- `runs.args`

> Skip if `runs.using` is not `docker` (this policy addresses Docker actions).

---

## Canonical Mapping Rules
Given an input named `<key>` under `inputs`, the container must receive a `--<key> <value>` pair in `runs.args` in the following form (two array elements):

```yaml
- --<key>
- ${{ inputs.<key> }}
```

**Authoritative ordering:** The order of `runs.args` pairs must match the order of keys as they appear in `inputs`.

**Exact key spelling:** Use the input key verbatim after `--`. Do not transform hyphens/underscores or case.

**Completeness:** Include **every** key in `inputs` in `runs.args`. Do **not** include any arg that is not defined in `inputs`.

**Booleans and optional inputs:** Always include all inputs, even if optional or boolean. Let the container entrypoint decide how to handle empty/false values.

**Preserve other run fields:** Do not alter `runs.image`, `runs.entrypoint`, or other `runs.*` fields unless obviously required by the PR. Only synchronize the `args` list.

---

## What to Check
1. **Presence:** `runs.args` exists (array) when `runs.using: docker`.
2. **Pairing:** `runs.args` contains *exactly* two elements per input key, in the repeating pattern:
   - `--<key>`
   - `${{ inputs.<key> }}`
3. **Coverage:** The set of keys appearing after `--` equals the set of keys under `inputs` (no missing, no extras).
4. **Order:** The order of `--<key>` pairs matches the order of keys declared under `inputs`.
5. **Exactness:** Keys match exactly (including hyphens). GitHub expression uses `${{ inputs.<key> }}` with identical key spelling.
6. **No mixing styles:** Do not accept single-element flags (e.g., just `--key`) or combined `--key=${{ inputs.key }}`. Use the 2-element style above to avoid quoting pitfalls.
7. **No unrelated churn:** Reject updates that reformat unrelated YAML regions or reorder unrelated keys (minimize diff).

---

## Auto-Fix Strategy (Patch Template)
When the `inputs` section changes (added/removed/renamed or reordered), produce a patch that rewrites the `runs.args` array to match. Keep other fields as-is.

**Generated args list (example):**
```yaml
runs:
  using: docker
  image: Dockerfile
  args:
    - --aws-region
    - ${{ inputs.aws-region }}
    - --role-to-assume
    - ${{ inputs.role-to-assume }}
    # ...repeat for each input, in input order
```

**Unified diff suggestion (example):**
```diff
--- a/action.yml
+++ b/action.yml
@@ -10,6 +10,22 @@ runs:
   using: docker
   image: Dockerfile
-  args: []
+  args:
+    - --aws-region
+    - ${{ inputs.aws-region }}
+    - --role-to-assume
+    - ${{ inputs.role-to-assume }}
+    - --aws-access-key-id
+    - ${{ inputs.aws-access-key-id }}
+    - --aws-secret-access-key
+    - ${{ inputs.aws-secret-access-key }}
+    # (include all inputs in order)
```

> **Indentation:** Preserve the project’s existing indentation (usually 2 spaces).

---

## Review Comment Template
Use this comment when the PR changes `inputs` but not `runs.args`, or when they’re out of sync:

> **Sync `runs.args` with `inputs`**
>
> This action uses `runs.using: docker`, so the container’s CLI args must mirror the `inputs` schema exactly.
> - Treat `inputs` as authoritative.
> - For each input key `k`, add two entries to `runs.args` in the same order as `inputs`:
>   ```yaml
>   - --k
>   - ${{ inputs.k }}
>   ```
> - Remove any args for keys not present in `inputs`.
> - Ensure exact key spelling (including hyphens).
>
> I’ve suggested a patch to update `runs.args` accordingly.

---

## Pseudocode for the Check
```python
# inputs_keys: list of keys in order of appearance under `inputs`
# args: the array at runs.args


def parse_args_pairs(args):
    # returns list of (flag_key, expr_key) in order
    pairs = []
    if len(args) % 2 != 0:
        return None  # invalid shape
    for i in range(0, len(args), 2):
        flag, val = args[i], args[i+1]
        if not isinstance(flag, str) or not flag.startswith("--"):
            return None
        flag_key = flag[2:]
        # expect value like "${{ inputs.<key> }}"
        expected_prefix = "${{ inputs."
        expected_suffix = " }}"
        if not (isinstance(val, str) and val.startswith(expected_prefix) and val.endswith(expected_suffix)):
            return None
        expr_key = val[len(expected_prefix):-len(expected_suffix)]
        pairs.append((flag_key, expr_key))
    return pairs


pairs = parse_args_pairs(runs_args)
if pairs is None:
    fail("runs.args must be two-element pairs of --<key> and ${{ inputs.<key> }}")

flag_keys = [k for (k, _) in pairs]
expr_keys = [k for (_, k) in pairs]

if flag_keys != inputs_keys or expr_keys != inputs_keys:
    fail("runs.args must include every inputs key exactly once, in the same order, with exact spelling")
```

---

## Edge Cases & Guidance
- **Reordering inputs:** If authors reorder `inputs`, reorder `runs.args` to match (no functional change, but maintain alignment).
- **Renaming inputs:** Remove old key pair from `runs.args` and add pair for the new key.
- **Removing inputs:** Remove the corresponding `--<key>` pair from `runs.args`.
- **Adding inputs:** Append new pairs to `runs.args` in the new input order.
- **YAML quoting:** The `${{ ... }}` expression must remain unquoted or double-quoted only if necessary for the repository’s style; do not alter expression content.
- **Comments:** If the file uses inline comments, avoid dropping or moving them.
- **Non-Docker actions:** If `runs.using` != `docker`, do not enforce these rules (Node actions can use `main`/`post`).

---

## Acceptance Criteria
- `runs.args` exists and exactly mirrors `inputs` (shape, order, spelling).
- No extra or missing keys.
- Minimal, targeted diff in PR suggestions.
- Other `runs.*` values unchanged.

---

*This agent guide ensures contributors never forget to propagate input schema updates to the Docker container’s command-line contract.*
