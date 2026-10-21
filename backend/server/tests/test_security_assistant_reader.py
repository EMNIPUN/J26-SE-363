"""The reader of the Security Assistant result folders: names, paths, redaction, contributor ids."""

import json

import pytest

from app.modules.security.reader import NotFound, ResultsReader, clean_text, counts, sanitize

TEAM, RUN = "J26-SE-363", "2026-10-21T0930-manual-a1b2c3d"


def finding(gid="G1", category="V2", status="confirmed", **extra):
    return {"group_id": gid, "category": category, "status": status, "introducing_commit": {"sha": "abc1234", "contributor": "C-0a1b2c3d"}, **extra}


def write_run(root, team=TEAM, run=RUN, findings=None, manifest=True, mapping=None, audit=None):
    folder = root / team / run
    folder.mkdir(parents=True)
    report = {"meta": {"source": "demo"}, "run": {"complete": True, "incomplete_reasons": [], "stages": []}, "findings": findings or [finding()]}
    (folder / "report.json").write_text(json.dumps(report), encoding="utf-8")
    if manifest:
        (folder / "run.json").write_text(json.dumps({"started_at": "2026-10-21T09:30:00Z", "trigger": "manual", "scan_type": "full",
                                                     "repo": "https://github.com/o/r", "commit_sha": "a" * 40}), encoding="utf-8")
    if mapping is not None:
        (folder / "trace_mapping.local.json").write_text(json.dumps({"salt": "s", "contributors": mapping}), encoding="utf-8")
    if audit is not None:
        (folder / "audit.jsonl").write_text("\n".join(json.dumps(a) for a in audit) + "\nnot json\n", encoding="utf-8")
    return folder


@pytest.fixture
def reader(tmp_path):
    return ResultsReader(tmp_path)


# ---- names and paths -----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("team,run", [("..", RUN), (TEAM, ".."), (TEAM, "../" + TEAM), ("a/b", RUN), (TEAM, "x\\y"), ("", RUN), (TEAM, ""),
                                      (".hidden", RUN), (TEAM, "r" * 200), (TEAM, "C:"), (TEAM, "run.json")])
def test_a_name_that_is_not_a_plain_name_is_refused(tmp_path, reader, team, run):
    write_run(tmp_path)
    with pytest.raises(NotFound):
        reader.run(team, run)
    with pytest.raises(NotFound):
        reader.audit(team, run)


def test_an_unknown_team_or_run_is_not_found_and_lists_nothing(tmp_path, reader):
    write_run(tmp_path)
    assert reader.run_ids("other-team") == [] and reader.summaries("other-team") == [] and reader.run_ids("../x") == []
    with pytest.raises(NotFound):
        reader.run(TEAM, "no-such-run")


def test_a_symlink_that_leaves_the_results_folder_is_refused(tmp_path, reader):
    outside = tmp_path.parent / (tmp_path.name + "_outside")
    (outside / "r1").mkdir(parents=True)
    (outside / "r1" / "report.json").write_text("{}", encoding="utf-8")
    try:
        (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    with pytest.raises(NotFound):
        reader.run("linked", "r1")


def test_only_the_whitelisted_shared_files_can_be_read(tmp_path, reader):
    (tmp_path / "_shared").mkdir()
    (tmp_path / "_shared" / "workflow.mmd").write_text("graph TD;", encoding="utf-8")
    (tmp_path / "_shared" / "secrets.txt").write_text("x", encoding="utf-8")
    assert reader.shared("workflow.mmd") == "graph TD;"
    for bad in ("secrets.txt", "../workflow.mmd", "a/b.md", "..", "missing.csv", ""):
        with pytest.raises(NotFound):
            reader.shared(bad)


def test_a_missing_or_broken_report_is_not_found(tmp_path, reader):
    folder = write_run(tmp_path)
    (folder / "report.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(NotFound):
        reader.run(TEAM, RUN)
    (folder / "report.json").unlink()
    assert reader.run_ids(TEAM) == []  # a folder without a report is not a run


# ---- listing -------------------------------------------------------------------------------------------------------------------------
def test_runs_are_listed_newest_first_with_counts_and_provenance(tmp_path, reader):
    write_run(tmp_path, run="older", findings=[finding("A", status="confirmed"), finding("B", "V4", "dismissed")])
    newer = write_run(tmp_path, run="newer", findings=[finding("A", status="uncertain")])
    manifest = json.loads((newer / "run.json").read_text(encoding="utf-8"))
    (newer / "run.json").write_text(json.dumps({**manifest, "started_at": "2026-11-01T10:00:00Z"}), encoding="utf-8")
    rows = reader.summaries(TEAM)
    assert [r["run_id"] for r in rows] == ["newer", "older"]
    assert rows[1]["counts"]["V2"]["confirmed"] == 1 and rows[1]["counts"]["V4"]["dismissed"] == 1 and rows[0]["counts"]["V2"]["uncertain"] == 1
    assert rows[0]["trigger"] == "manual" and rows[0]["repo"] == "https://github.com/o/r" and rows[0]["complete"] is True


def test_a_run_without_a_manifest_still_loads(tmp_path, reader):
    write_run(tmp_path, manifest=False)
    run = reader.run(TEAM, RUN)
    assert run["manifest"] == {} and reader.summaries(TEAM)[0]["repo"] == "demo"


def test_counts_treat_an_unknown_status_as_uncertain():
    c = counts([finding(status="not interpreted"), finding(status="weird")])
    assert c["V2"]["not interpreted"] == 1 and c["V2"]["uncertain"] == 1


# ---- redaction -----------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("secret", ["AKIAIOSFODNN7EXAMPLE", "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2", "sk_live_" + "abcd1234efgh5678",
                                    "xoxb-1234567890-abcdefghij", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl"])
def test_a_secret_in_any_string_is_redacted_on_the_way_out(tmp_path, reader, secret):
    write_run(tmp_path, findings=[finding(snippet=f"x = '{secret}'", rationale=f"the key {secret} is hard-coded", deep={"list": [secret]})])
    text = json.dumps(reader.run(TEAM, RUN))
    assert secret not in text and "[REDACTED by API]" in text


def test_a_private_key_block_and_a_password_assignment_are_redacted():
    block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"
    assert "MIIEow" not in clean_text(f"k = '''{block}'''")
    assert "hunter2hunter2" not in clean_text('password = "hunter2hunter2"') and clean_text('password = "hunter2hunter2"').startswith("password = ")
    assert clean_text('password = "[REDACTED password placeholder_like=false]"') == 'password = "[REDACTED password placeholder_like=false]"'


def test_an_email_address_is_removed_but_code_that_only_looks_like_one_is_kept():
    assert "jane.doe@example.org" not in clean_text("mail jane.doe@example.org now")
    code = "limiter = Limiter(app)\n@app.route('/x')\n- uses: actions/checkout@latest"
    assert clean_text(code) == code


def test_address_like_keys_are_dropped_and_a_bad_contributor_id_becomes_none():
    out = sanitize({"email": "a@b.co", "author": "Jane", "ok": 1, "introducing_commit": {"contributor": "Jane Doe"},
                    "x": [{"contributor": "C-0a1b2c3d"}, {"contributor": "C-XYZ"}, {"contributor": None}]})
    assert out == {"ok": 1, "introducing_commit": {"contributor": None},
                   "x": [{"contributor": "C-0a1b2c3d"}, {"contributor": None}, {"contributor": None}]}


def test_sanitize_leaves_numbers_bools_and_null():
    assert sanitize({"a": 1, "b": 1.5, "c": True, "d": None}) == {"a": 1, "b": 1.5, "c": True, "d": None}


# ---- "mine" --------------------------------------------------------------------------------------------------------------------------
def test_the_contributor_id_of_an_email_comes_from_the_local_mapping_and_the_mapping_is_never_returned(tmp_path, reader):
    mapping = {"C-0a1b2c3d": {"name": "Jane Doe", "email": "Jane.Doe@Example.org"}, "C-11111111": {"name": "Sam", "email": "sam@example.org"},
               "not-an-id": {"name": "X", "email": "jane.doe@example.org"}}
    write_run(tmp_path, mapping=mapping)
    assert reader.contributor_ids(TEAM, RUN, " jane.doe@example.org ") == ["C-0a1b2c3d"]
    assert reader.contributor_ids(TEAM, RUN, "nobody@example.org") == [] and reader.contributor_ids(TEAM, RUN, None) == []
    everything = json.dumps(reader.run(TEAM, RUN)) + json.dumps(reader.summaries(TEAM)) + json.dumps(reader.audit(TEAM, RUN))
    assert "Jane" not in everything and "example.org" not in everything and "salt" not in everything


def test_without_a_mapping_nobody_has_a_contributor_id(tmp_path, reader):
    write_run(tmp_path)
    assert reader.contributor_ids(TEAM, RUN, "jane@example.org") == []


# ---- audit ---------------------------------------------------------------------------------------------------------------------------
def test_audit_lines_are_returned_cleaned_and_broken_lines_are_skipped(tmp_path, reader):
    write_run(tmp_path, audit=[{"event": "llm_call", "prompt_sha256": "ab" * 32, "note": "to jane@example.org"}, {"event": "run_end"}])
    lines = reader.audit(TEAM, RUN)
    assert [x["event"] for x in lines] == ["llm_call", "run_end"] and "jane@example.org" not in json.dumps(lines)
    assert reader.audit(TEAM, RUN)[0]["prompt_sha256"] == "ab" * 32


def test_a_run_without_an_audit_file_has_no_audit_lines(tmp_path, reader):
    write_run(tmp_path)
    assert reader.audit(TEAM, RUN) == []
