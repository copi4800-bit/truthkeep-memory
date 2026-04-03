import json

from aegis_py import cli
from scripts import prove_it


def test_truthkeep_cli_remember_and_status_work(tmp_path, capsys):
    db_path = tmp_path / "phase125_cli.db"
    assert cli.main(["--db-path", str(db_path), "remember", "The release owner is Bao."]) == 0
    remember_out = capsys.readouterr().out
    assert remember_out.strip()

    assert cli.main(["--db-path", str(db_path), "status"]) == 0
    status_out = capsys.readouterr().out
    assert "State:" in status_out


def test_truthkeep_cli_field_snapshot_emits_json(tmp_path, capsys):
    db_path = tmp_path / "phase125_snapshot.db"
    assert cli.main(["--db-path", str(db_path), "remember", "Bao prefers black coffee."]) == 0
    capsys.readouterr()
    assert cli.main(["--db-path", str(db_path), "field-snapshot"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "state_coverage" in payload
    assert "energy" in payload


def test_prove_it_summary_passes_and_confirms_correctness_behavior(tmp_path):
    summary = prove_it.build_proof_summary(db_path=str(tmp_path / "phase125_proof.db"))
    assert summary["passed"] is True
    assert summary["metrics"]["correction_top1_preserved"] is True
    assert summary["metrics"]["why_not_available"] is True
