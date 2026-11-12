"""Reconciliation tests: fixtures, star schema and summary must all agree."""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.prep import build_model, load_raw
from pipeline.summary import swing_table
from pipeline.validate import validate_model, validate_raw

DATA_DIR = Path(__file__).resolve().parents[1] / "sample_data"


def test_fixture_data_reconciles():
    rows = load_raw(DATA_DIR)
    checks = validate_raw(rows)  # raises ValidationError on any problem
    assert len(checks) == 4


def test_candidate_votes_sum_to_county_totals():
    rows = load_raw(DATA_DIR)
    races = defaultdict(list)
    for row in rows:
        races[(row["cycle"], row["state"], row["county"])].append(row)
    assert len(races) == 34  # 17 counties x 2 cycles
    for members in races.values():
        assert sum(m["votes"] for m in members) == members[0]["county_total_votes"]


def test_vote_shares_sum_to_100_per_race():
    rows = load_raw(DATA_DIR)
    races = defaultdict(list)
    for row in rows:
        races[(row["cycle"], row["state"], row["county"])].append(row)
    for members in races.values():
        total = sum(m["votes"] for m in members)
        share_sum = sum(m["votes"] / total * 100 for m in members)
        assert abs(share_sum - 100.0) < 0.01, share_sum


def test_star_schema_reconciles_with_raw():
    rows = load_raw(DATA_DIR)
    dim_state, dim_candidate, fact = build_model(rows)
    validate_model(rows, dim_state, dim_candidate, fact)
    assert len(fact) == len(rows) == 136
    assert len(dim_state) == 5
    assert len(dim_candidate) == 8  # 4 candidates per cycle x 2 cycles
    assert sum(entry["Votes"] for entry in fact) == sum(row["votes"] for row in rows)


def test_fact_keys_resolve():
    rows = load_raw(DATA_DIR)
    dim_state, dim_candidate, fact = build_model(rows)
    state_keys = {entry["StateKey"] for entry in dim_state}
    candidate_keys = {entry["CandidateKey"] for entry in dim_candidate}
    assert all(entry["StateKey"] in state_keys for entry in fact)
    assert all(entry["CandidateKey"] in candidate_keys for entry in fact)


def test_swing_directions_match_fixture_design():
    table = {entry["state"]: entry for entry in swing_table(load_raw(DATA_DIR))}
    # Pennsylvania and Arizona moved Republican 2020 -> 2024 in the fixtures;
    # Wisconsin moved (slightly) Democratic.
    assert table["PA"]["dem_swing"] < 0
    assert table["AZ"]["dem_swing"] < 0
    assert table["WI"]["dem_swing"] > 0
    for entry in table.values():
        assert 0 < entry["dem_2020"] < 100
        assert 0 < entry["dem_2024"] < 100
