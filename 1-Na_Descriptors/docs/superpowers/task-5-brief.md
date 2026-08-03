### Task 5: Integration verification and modification record

**Files:**
- Create: `ARIS_Experiments/new_descriptors/automat-naconductor/修复记录_2026-08-03.md`
- Modify: `ARIS_Experiments/new_descriptors/automat-naconductor/run_pipeline.py`

- [ ] **Step 1: Add a no-CIF pipeline preflight test and an in-memory integration test.**

The preflight test must confirm the pipeline exits with a clear missing-CIF diagnostic before creating analysis results. The integration test may use synthetic numeric features to execute Stages 1–4 without changing the real data artifacts.

- [ ] **Step 2: Run the full suite.**

Run: `pytest -q`

Expected: all tests pass, no collection failure, and no warnings from the repaired regression cases.

- [ ] **Step 3: Run static and CLI verification.**

Run: `python -m compileall -q .`, `python run_pipeline.py --help`, `python train.py --help`, `python run_status.py --help`.

Expected: all commands exit zero; no computation is attempted without valid CIF input.

- [ ] **Step 4: Write the modification record and commit.**

The record must list each original defect, root cause, changed files, behavioral change, tests, remaining limitation (CIF absent), and the research interpretation boundary.
