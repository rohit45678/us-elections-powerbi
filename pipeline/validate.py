"""Data validation: reconciliation checks that fail loudly.

Two layers are checked:

* raw extracts  -- candidate votes must sum to the recorded county total for
  every county and cycle, vote shares per race must sum to 100%, ballots
  cast must cover the office vote total, and no duplicate or non-positive
  rows may exist.
* modeled tables -- the star schema must reconcile back to the raw data:
  same row count, same total votes, and every foreign key resolvable.

Any failure raises ValidationError with every problem found, and main.py
turns that into a non-zero exit.
"""

from __future__ import annotations

from collections import defaultdict

SHARE_TOLERANCE = 0.01  # percentage points


class ValidationError(Exception):
    """Raised when one or more reconciliation checks fail."""


def _race_key(row: dict) -> tuple:
    return (row["cycle"], row["state"], row["county"])


def validate_raw(rows: list[dict]) -> list[str]:
    """Validate raw result rows. Returns a list of check descriptions passed."""
    errors: list[str] = []

    seen: set[tuple] = set()
    for row in rows:
        key = (row["cycle"], row["state"], row["county"], row["candidate"])
        if key in seen:
            errors.append(f"duplicate row for {key}")
        seen.add(key)
        if row["votes"] <= 0:
            errors.append(f"non-positive votes in {key}: {row['votes']}")

    races: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        races[_race_key(row)].append(row)

    for race, members in sorted(races.items()):
        total_votes = sum(member["votes"] for member in members)
        recorded_totals = {member["county_total_votes"] for member in members}
        if len(recorded_totals) != 1:
            errors.append(f"{race}: inconsistent county_total_votes values {sorted(recorded_totals)}")
        else:
            recorded_total = next(iter(recorded_totals))
            if total_votes != recorded_total:
                errors.append(
                    f"{race}: candidate votes sum to {total_votes}, "
                    f"county_total_votes says {recorded_total}"
                )
        share_sum = sum(member["votes"] / total_votes * 100 for member in members) if total_votes else 0
        if abs(share_sum - 100.0) > SHARE_TOLERANCE:
            errors.append(f"{race}: vote shares sum to {share_sum:.4f}%, expected 100%")
        ballots = {member["ballots_cast"] for member in members}
        registered = {member["registered_voters"] for member in members}
        if len(ballots) != 1 or len(registered) != 1:
            errors.append(f"{race}: inconsistent ballots_cast / registered_voters values")
        else:
            if ballots.pop() < total_votes:
                errors.append(f"{race}: ballots_cast is below the office vote total")
            if registered.pop() < total_votes:
                errors.append(f"{race}: registered_voters is below the office vote total")

    if errors:
        raise ValidationError("raw data validation failed:\n  - " + "\n  - ".join(errors))
    return [
        f"candidate votes reconcile to county totals for {len(races)} county races",
        "vote shares sum to 100% in every race (tolerance 0.01 pp)",
        "ballots cast and registered voters cover office totals everywhere",
        "no duplicate or non-positive rows",
    ]


def validate_model(rows: list[dict], dim_state, dim_candidate, fact) -> list[str]:
    """Validate the star schema against the raw rows it was built from."""
    errors: list[str] = []

    if len(fact) != len(rows):
        errors.append(f"fact has {len(fact)} rows, raw data has {len(rows)}")
    raw_total = sum(row["votes"] for row in rows)
    fact_total = sum(entry["Votes"] for entry in fact)
    if raw_total != fact_total:
        errors.append(f"fact votes total {fact_total} != raw votes total {raw_total}")

    state_keys = {entry["StateKey"] for entry in dim_state}
    candidate_keys = {entry["CandidateKey"] for entry in dim_candidate}
    for entry in fact:
        if entry["StateKey"] not in state_keys:
            errors.append(f"fact row references unknown StateKey {entry['StateKey']}")
            break
        if entry["CandidateKey"] not in candidate_keys:
            errors.append(f"fact row references unknown CandidateKey {entry['CandidateKey']}")
            break

    state_names = [entry["State"] for entry in dim_state]
    if len(state_names) != len(set(state_names)):
        errors.append("dim_state contains duplicate states")
    candidate_combos = [(e["Cycle"], e["Candidate"]) for e in dim_candidate]
    if len(candidate_combos) != len(set(candidate_combos)):
        errors.append("dim_candidate contains duplicate (cycle, candidate) rows")

    if errors:
        raise ValidationError("model validation failed:\n  - " + "\n  - ".join(errors))
    return [
        f"fact row count matches raw extracts ({len(fact)} rows)",
        f"total votes reconcile raw -> fact ({fact_total:,})",
        "all fact foreign keys resolve to dimension rows",
        "dimensions are unique on their natural keys",
    ]
