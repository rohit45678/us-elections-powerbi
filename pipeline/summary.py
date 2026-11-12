"""Summary analytics computed from the raw extracts (mirrors the DAX logic)."""

from __future__ import annotations

from collections import defaultdict


def party_shares(rows: list[dict]) -> dict[tuple, dict[str, float]]:
    """Vote share (%) per (state, cycle) -> party, over all candidates."""
    totals: dict[tuple, int] = defaultdict(int)
    party_votes: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        key = (row["state"], row["cycle"])
        totals[key] += row["votes"]
        party_votes[key][row["party"]] += row["votes"]
    return {
        key: {party: votes / totals[key] * 100 for party, votes in parties.items()}
        for key, parties in party_votes.items()
    }


def swing_table(rows: list[dict]) -> list[dict]:
    """Per state: DEM/REP share for each cycle and the DEM swing between cycles."""
    shares = party_shares(rows)
    states = sorted({row["state"] for row in rows})
    state_names = {row["state"]: row["state_name"] for row in rows}
    cycles = sorted({row["cycle"] for row in rows})
    table = []
    for state in states:
        entry = {"state": state, "state_name": state_names[state]}
        for cycle in cycles:
            entry[f"dem_{cycle}"] = shares[(state, cycle)].get("DEM", 0.0)
            entry[f"rep_{cycle}"] = shares[(state, cycle)].get("REP", 0.0)
        if len(cycles) >= 2:
            first, last = cycles[0], cycles[-1]
            entry["dem_swing"] = entry[f"dem_{last}"] - entry[f"dem_{first}"]
            entry["cycles"] = (first, last)
        table.append(entry)
    return table


def format_swing_table(table: list[dict]) -> str:
    if not table:
        return "(no data)"
    first, last = table[0]["cycles"]
    header = (
        f"{'State':<15} {'DEM ' + str(first):>9} {'REP ' + str(first):>9} "
        f"{'DEM ' + str(last):>9} {'REP ' + str(last):>9} {'DEM swing':>10}"
    )
    lines = [header, "-" * len(header)]
    for entry in table:
        lines.append(
            f"{entry['state_name']:<15} {entry[f'dem_{first}']:>8.1f}% {entry[f'rep_{first}']:>8.1f}% "
            f"{entry[f'dem_{last}']:>8.1f}% {entry[f'rep_{last}']:>8.1f}% "
            f"{entry['dem_swing']:>+9.1f}p"
        )
    return "\n".join(lines)
