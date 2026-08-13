from __future__ import annotations

from pathlib import Path

import descriptors
import pandas as pd
import pytest

import train as train_module
from automat_utils import (
    AGENT_RESULT_COLUMNS,
    evaluate_structural_descriptor,
    resolve_frozen_input_identity,
)
from plot_run_results import read_agent_results
from run_config import load_run_info
from run_pipeline import parseArgs
from run_status import read_results, resolve_results_file
from train import parse_agent_args


def _write_agent_config(
    tmp_path: Path,
    *,
    raw_file: str = "data/raw.csv",
    shared_raw_file: str | None = None,
    descriptor_registry: str | None = None,
    frozen: bool = True,
) -> Path:
    config_path = tmp_path / "run_info.yaml"
    config_path.write_text(
        "\n".join(
            [
                "data:",
                f"  raw_file: {raw_file}",
                "  featurized_file: data/featurized.csv",
                "  target_column: log_sigma",
                "  structure_column: cif_path",
                "  system_column: system",
                "  anion_type_column: anion_type",
                "evaluation:",
                "  model:",
                "    alpha: 1.0",
                "combination:",
                "  max_descriptors: 3",
                "tracks:",
                "  agent:",
                "    results_file: results/agent/results.tsv",
                "    feature_cache_file: results/agent/descriptor_features.csv",
                "    ideas_file: results/agent/ideas.tsv",
                "    status:",
                "      max_iterations: 12",
                "      patience: 4",
                "      primary_metric: rank_corr_of_linear_residuals",
                "  pipeline:",
                "    output_dir: results/pipeline",
                "shared_input:",
                f"  frozen: {str(frozen).lower()}",
                f"  raw_file: {shared_raw_file or raw_file}",
                "  descriptor_registry: "
                + (descriptor_registry or str(Path(descriptors.__file__).resolve())),
                "  registry_revision: frozen-structural-registry",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_agent_config_exposes_only_new_structural_contract(tmp_path: Path) -> None:
    config = _write_agent_config(tmp_path)

    args = parse_agent_args(
        ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
    )

    assert args.descriptor_name == "a2_max_dist"
    assert args.structure_column == "cif_path"
    assert args.target_column == "log_sigma"
    assert args.registry_revision == "frozen-structural-registry"
    assert args.descriptor_registry == Path(descriptors.__file__).resolve()
    assert not hasattr(args, "composition_column")
    assert not hasattr(args, "train_file")
    assert not hasattr(args, "validation_file")


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--raw-file", "different.csv"),
        ("--structure-column", "other_cif"),
        ("--target-column", "other_target"),
    ],
)
def test_agent_rejects_overrides_of_frozen_shared_input(
    tmp_path: Path, option: str, value: str
) -> None:
    config = _write_agent_config(tmp_path)

    with pytest.raises(SystemExit):
        parse_agent_args(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config), option, value]
        )


def test_agent_status_uses_agent_results_file_not_legacy_logging_keys(
    tmp_path: Path,
) -> None:
    config = load_run_info(_write_agent_config(tmp_path))

    assert resolve_results_file(config) == Path("results/agent/results.tsv")


def test_agent_status_rejects_unversioned_legacy_result_rows(tmp_path: Path) -> None:
    config_path = _write_agent_config(tmp_path)
    identity = resolve_frozen_input_identity(
        load_run_info(config_path), config_path
    )
    legacy_results = tmp_path / "legacy-results.tsv"
    legacy_results.write_text(
        "descriptor_name\trank_corr_of_linear_residuals\tstatus\n"
        "a2_max_dist\t0.4\tevaluated\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required columns"):
        read_results(legacy_results, identity)


def test_status_and_plot_reject_results_from_a_different_frozen_batch(
    tmp_path: Path,
) -> None:
    config_path = _write_agent_config(tmp_path)
    identity = resolve_frozen_input_identity(
        load_run_info(config_path), config_path
    )
    foreign = {
        column: "" for column in AGENT_RESULT_COLUMNS
    }
    foreign.update(
        {
            "descriptor_name": "a2_max_dist",
            "raw_spearman": "0.2",
            "rank_corr_of_linear_residuals": "0.3",
            "status": "evaluated",
            "shared_raw_file": str(tmp_path / "other-raw.csv"),
            "descriptor_registry": str(identity.descriptor_registry),
            "registry_revision": identity.registry_revision,
        }
    )
    results = tmp_path / "foreign-results.tsv"
    pd.DataFrame([foreign], columns=AGENT_RESULT_COLUMNS).to_csv(
        results, sep="\t", index=False
    )

    with pytest.raises(ValueError, match="frozen batch identity"):
        read_results(results, identity)
    with pytest.raises(ValueError, match="frozen batch identity"):
        read_agent_results(results, identity)


def test_agent_rejects_pipeline_results_override(tmp_path: Path) -> None:
    config = _write_agent_config(tmp_path)

    with pytest.raises(SystemExit):
        parse_agent_args(
            [
                "--descriptor-name",
                "a2_max_dist",
                "--run-info",
                str(config),
                "--results-file",
                "results/pipeline/not-allowed.tsv",
            ]
        )


def test_pipeline_default_output_follows_pipeline_track_config(tmp_path: Path) -> None:
    config = _write_agent_config(tmp_path)

    args = parseArgs(["--run-info", str(config)])

    assert args.output_dir == "results/pipeline"


def test_pipeline_rejects_agent_output_override(tmp_path: Path) -> None:
    config = _write_agent_config(tmp_path)

    with pytest.raises(SystemExit):
        parseArgs(
            [
                "--run-info",
                str(config),
                "--output-dir",
                "results/agent/not-allowed",
            ]
        )


def test_pipeline_rejects_run_info_with_nonfrozen_raw_input(tmp_path: Path) -> None:
    config = _write_agent_config(
        tmp_path,
        raw_file="data/raw.csv",
        shared_raw_file="data/other.csv",
    )

    with pytest.raises(SystemExit):
        parseArgs(["--run-info", str(config)])


def test_agent_rejects_run_info_with_nonfrozen_raw_input(tmp_path: Path) -> None:
    config = _write_agent_config(
        tmp_path,
        raw_file="data/raw.csv",
        shared_raw_file="data/other.csv",
    )

    with pytest.raises(SystemExit):
        parse_agent_args(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
        )


def test_agent_and_pipeline_require_real_current_frozen_registry(tmp_path: Path) -> None:
    wrong_registry = tmp_path / "other_registry.py"
    wrong_registry.write_text("# not the loaded descriptor registry\n", encoding="utf-8")
    config = _write_agent_config(tmp_path, descriptor_registry=str(wrong_registry))

    with pytest.raises(SystemExit, match="2"):
        parse_agent_args(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
        )
    with pytest.raises(SystemExit, match="2"):
        parseArgs(["--run-info", str(config)])


def test_agent_and_pipeline_reject_nonexistent_frozen_registry(tmp_path: Path) -> None:
    config = _write_agent_config(
        tmp_path, descriptor_registry=str(tmp_path / "missing_registry.py")
    )

    with pytest.raises(SystemExit, match="2"):
        parse_agent_args(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
        )
    with pytest.raises(SystemExit, match="2"):
        parseArgs(["--run-info", str(config)])


def test_agent_and_pipeline_require_shared_input_frozen_true(tmp_path: Path) -> None:
    config = _write_agent_config(tmp_path, frozen=False)

    with pytest.raises(SystemExit, match="2"):
        parse_agent_args(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
        )
    with pytest.raises(SystemExit, match="2"):
        parseArgs(["--run-info", str(config)])


def test_status_and_plot_reject_mixed_frozen_batch_rows(tmp_path: Path) -> None:
    config_path = _write_agent_config(tmp_path)
    identity = resolve_frozen_input_identity(
        load_run_info(config_path), config_path
    )
    current = {column: "" for column in AGENT_RESULT_COLUMNS}
    current.update(
        {
            "descriptor_name": "a2_max_dist",
            "raw_spearman": "0.2",
            "rank_corr_of_linear_residuals": "0.3",
            "status": "evaluated",
            "shared_raw_file": str(identity.raw_file),
            "descriptor_registry": str(identity.descriptor_registry),
            "registry_revision": identity.registry_revision,
        }
    )
    mixed = current.copy()
    mixed["shared_raw_file"] = str(tmp_path / "different-raw.csv")
    results = tmp_path / "mixed-results.tsv"
    pd.DataFrame([current, mixed], columns=AGENT_RESULT_COLUMNS).to_csv(
        results, sep="\t", index=False
    )

    with pytest.raises(ValueError, match="frozen batch identity mismatch"):
        read_results(results, identity)
    with pytest.raises(ValueError, match="frozen batch identity mismatch"):
        read_agent_results(results, identity)


def test_agent_cif_preflight_fails_before_creating_agent_outputs(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    raw_path.write_text(
        "material_id,cif_path,system,anion_type,log_sigma\n"
        "sample-1,missing.cif,NASICON,oxide,-3.0\n",
        encoding="utf-8",
    )
    config = _write_agent_config(tmp_path, raw_file=str(raw_path))
    args = parse_agent_args(
        ["--descriptor-name", "a2_max_dist", "--run-info", str(config)]
    )

    with pytest.raises(FileNotFoundError, match="CIF preflight failed"):
        evaluate_structural_descriptor(args)

    assert not (tmp_path / "results" / "agent").exists()


def test_train_rejects_foreign_batch_before_overwriting_agent_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = _write_agent_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    results_dir = tmp_path / "results" / "agent"
    results_dir.mkdir(parents=True)
    audit_file = results_dir / "descriptor_features.csv"
    audit_file.write_text("sentinel audit\n", encoding="utf-8")

    foreign = {column: "" for column in AGENT_RESULT_COLUMNS}
    foreign.update(
        {
            "descriptor_name": "a2_max_dist",
            "raw_spearman": "0.2",
            "rank_corr_of_linear_residuals": "0.3",
            "status": "evaluated",
            "shared_raw_file": str(tmp_path / "foreign-raw.csv"),
            "descriptor_registry": str(Path(descriptors.__file__).resolve()),
            "registry_revision": "frozen-structural-registry",
        }
    )
    pd.DataFrame([foreign], columns=AGENT_RESULT_COLUMNS).to_csv(
        results_dir / "results.tsv", sep="\t", index=False
    )

    args = parse_agent_args(
        ["--descriptor-name", "a2_max_dist", "--run-info", str(config_path)]
    )
    frame = pd.DataFrame(
        {
            "material_id": ["m1"],
            "cif_path": ["sample.cif"],
            "system": ["NASICON"],
            "anion_type": ["oxide"],
            "log_sigma": [-3.0],
            "a2_max_dist": [2.5],
        }
    )
    metrics = {column: "" for column in AGENT_RESULT_COLUMNS}
    metrics.update(
        {
            "descriptor_name": "a2_max_dist",
            "shared_raw_file": str(args.raw_file),
            "descriptor_registry": str(args.descriptor_registry),
            "registry_revision": args.registry_revision,
            "raw_spearman": 0.1,
            "rank_corr_of_linear_residuals": 0.1,
            "status": "evaluated",
        }
    )
    monkeypatch.setattr(
        train_module,
        "prepare_structural_evaluation",
        lambda _args: (frame, metrics),
    )

    with pytest.raises(SystemExit) as exc_info:
        train_module.main(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config_path)]
        )

    assert exc_info.value.code == 2
    assert audit_file.read_text(encoding="utf-8") == "sentinel audit\n"
    assert "frozen batch identity mismatch" in capsys.readouterr().err


def test_train_rejects_foreign_audit_before_creating_agent_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = _write_agent_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    results_dir = tmp_path / "results" / "agent"
    results_dir.mkdir(parents=True)
    audit_file = results_dir / "descriptor_features.csv"
    foreign_audit = pd.DataFrame(
        {
            "material_id": ["m1"],
            "shared_raw_file": [str(tmp_path / "foreign-raw.csv")],
            "descriptor_registry": [str(Path(descriptors.__file__).resolve())],
            "registry_revision": ["frozen-structural-registry"],
            "a2_max_dist": [2.5],
        }
    )
    foreign_audit.to_csv(audit_file, index=False)

    args = parse_agent_args(
        ["--descriptor-name", "a2_max_dist", "--run-info", str(config_path)]
    )
    frame = pd.DataFrame(
        {
            "material_id": ["m1"],
            "cif_path": ["sample.cif"],
            "system": ["NASICON"],
            "anion_type": ["oxide"],
            "log_sigma": [-3.0],
            "a2_max_dist": [2.5],
        }
    )
    metrics = {column: "" for column in AGENT_RESULT_COLUMNS}
    metrics.update(
        {
            "descriptor_name": "a2_max_dist",
            "shared_raw_file": str(args.raw_file),
            "descriptor_registry": str(args.descriptor_registry),
            "registry_revision": args.registry_revision,
            "raw_spearman": 0.1,
            "rank_corr_of_linear_residuals": 0.1,
            "status": "evaluated",
        }
    )
    monkeypatch.setattr(
        train_module,
        "prepare_structural_evaluation",
        lambda _args: (frame, metrics),
    )

    with pytest.raises(SystemExit) as exc_info:
        train_module.main(
            ["--descriptor-name", "a2_max_dist", "--run-info", str(config_path)]
        )

    assert exc_info.value.code == 2
    assert not (results_dir / "results.tsv").exists()
    pd.testing.assert_frame_equal(pd.read_csv(audit_file), foreign_audit)
    assert "frozen batch identity mismatch" in capsys.readouterr().err
