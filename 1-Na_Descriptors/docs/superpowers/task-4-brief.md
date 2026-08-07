### Task 4: Concurrent dual-track contract, Agent migration, and documentation

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_agent_track.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/automat_utils.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/train.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/test_descriptors.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_status.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/plot_run_results.py`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/program.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/README.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/pyproject.toml`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_info.yaml`
- Modify: `ARIS_Experiments/new_descriptors/.omo/plans/automat-reform-dual-track.md`

**Interfaces:**
- Agent evaluator accepts a descriptor name and CIF-path raw CSV, returns structural metrics, and writes to `results/agent/` only.
- Pipeline writes to `results/pipeline/` only.
- The two tracks share frozen registry/data metadata but no result files before C9.

- [ ] **Step 1: Write failing Agent-contract tests.**

```python
def test_agent_config_exposes_only_new_structural_contract(tmp_path):
    args = parse_agent_args(["--descriptor-name", "a2_max_dist", "--run-info", str(config)])
    assert args.structure_column == "cif_path"

def test_agent_status_uses_agent_results_file_not_legacy_logging_keys(tmp_path):
    assert resolve_results_file(config) == Path("results/agent/results.tsv")
```

- [ ] **Step 2: Run RED tests.**

Run: `pytest -q tests/test_agent_track.py`

Expected: missing legacy config keys and composition-oriented evaluator behavior.

- [ ] **Step 3: Replace the legacy Composition/RF stack.**

Use `Structure`/CIF featurization, Ridge, rank-aware deconfounding, and the shared CV methods. Make descriptor selection explicit rather than relying on removed `descriptor.default_name`. Update `run_status` and plotting to use deconfounded Spearman/audit columns.

- [ ] **Step 4: Encode concurrent isolation in configuration and documentation.**

Add `tracks.pipeline` and `tracks.agent` output locations; document frozen shared input and the prohibition on cross-reading before C9. Update the dual-track OMO plan so A and B launch concurrently and C9 compares only completed frozen outputs.

- [ ] **Step 5: Run focused tests and commit.**

Run: `pytest -q tests/test_agent_track.py`

Expected: Agent CLI/config functions operate without legacy keys.

