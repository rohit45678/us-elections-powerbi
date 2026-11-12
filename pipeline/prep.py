"""Data preparation: raw county-level results -> star-schema model tables.

Reads the raw extracts in sample_data/ (one CSV per cycle), and produces:

    out/dim_state.csv       one row per state
    out/dim_candidate.csv   one row per candidate per cycle
    out/fact_results.csv    one row per county x candidate x cycle

The fact table is at county grain. County-level measures that repeat on every
candidate row (county_total_votes, ballots_cast, registered_voters) are
de-duplicated by the DAX measures in measures.dax, as documented in model.md.
"""

from __future__ import annotations

import csv
from pathlib import Path

INT_FIELDS = ("cycle", "votes", "county_total_votes", "ballots_cast", "registered_voters")


def load_raw(data_dir: str | Path) -> list[dict]:
    """Load and type-normalize every results_*.csv extract in data_dir."""
    data_path = Path(data_dir)
    files = sorted(data_path.glob("results_*.csv"))
    if not files:
        raise FileNotFoundError(f"no results_*.csv files found in {data_path}")
    rows: list[dict] = []
    for file_path in files:
        with open(file_path, newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                row = dict(raw)
                for field_name in INT_FIELDS:
                    row[field_name] = int(row[field_name])
                rows.append(row)
    rows.sort(key=lambda r: (r["cycle"], r["state"], r["county"], -r["votes"]))
    return rows


def build_dim_state(rows: list[dict]) -> list[dict]:
    states = {}
    for row in rows:
        states[row["state"]] = row["state_name"]
    return [
        {"StateKey": index, "State": state, "State Name": states[state]}
        for index, state in enumerate(sorted(states), start=1)
    ]


def build_dim_candidate(rows: list[dict]) -> list[dict]:
    combos = sorted({(row["cycle"], row["candidate"], row["party"]) for row in rows})
    return [
        {"CandidateKey": index, "Candidate": candidate, "Party": party, "Cycle": cycle}
        for index, (cycle, candidate, party) in enumerate(combos, start=1)
    ]


def build_fact(rows: list[dict], dim_state: list[dict], dim_candidate: list[dict]) -> list[dict]:
    state_keys = {entry["State"]: entry["StateKey"] for entry in dim_state}
    candidate_keys = {
        (entry["Cycle"], entry["Candidate"]): entry["CandidateKey"] for entry in dim_candidate
    }
    fact = []
    for row in rows:
        fact.append(
            {
                "Cycle": row["cycle"],
                "StateKey": state_keys[row["state"]],
                "County": row["county"],
                "CandidateKey": candidate_keys[(row["cycle"], row["candidate"])],
                "Votes": row["votes"],
                "County Total Votes": row["county_total_votes"],
                "Ballots Cast": row["ballots_cast"],
                "Registered Voters": row["registered_voters"],
            }
        )
    return fact


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_model(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    dim_state = build_dim_state(rows)
    dim_candidate = build_dim_candidate(rows)
    fact = build_fact(rows, dim_state, dim_candidate)
    return dim_state, dim_candidate, fact


def write_model(out_dir: str | Path, dim_state, dim_candidate, fact) -> dict[str, Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, table in (
        ("dim_state.csv", dim_state),
        ("dim_candidate.csv", dim_candidate),
        ("fact_results.csv", fact),
    ):
        target = out_path / name
        _write_csv(target, table)
        written[name] = target
    return written
