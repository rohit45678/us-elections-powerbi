# Data Model — US Elections Vote-Share Analysis

This document describes the star schema behind the Power BI report, the
relationships and measures, what each report page shows, and how to rebuild
the `.pbix` from the pipeline outputs in this repository.

The pipeline (`main.py`) turns the raw extracts in `sample_data/` into the
three modeled tables in `out/`. The sample data covers five swing states
(PA, GA, AZ, WI, MI), 17 counties and the 2020 and 2024 presidential cycles;
the same model works unchanged for a full 50-state extract.

## Tables

### Dim State — `out/dim_state.csv` → table name `Dim State`

| Column     | Type | Description                    |
|------------|------|--------------------------------|
| StateKey   | int  | Surrogate key (primary key)    |
| State      | text | USPS state abbreviation        |
| State Name | text | Full state name (map display)  |

### Dim Candidate — `out/dim_candidate.csv` → table name `Dim Candidate`

One row per candidate **per cycle** (candidates differ between cycles).

| Column       | Type | Description                                   |
|--------------|------|-----------------------------------------------|
| CandidateKey | int  | Surrogate key (primary key)                   |
| Candidate    | text | Candidate name                                |
| Party        | text | Party code: DEM, REP, LIB, GRN, OTH           |
| Cycle        | int  | Election cycle the candidacy belongs to       |

### Fact Results — `out/fact_results.csv` → table name `Fact Results`

One row per county × candidate × cycle (136 rows for the sample data).

| Column            | Type | Description                                                        |
|-------------------|------|--------------------------------------------------------------------|
| Cycle             | int  | Election year (2020, 2024)                                         |
| StateKey          | int  | FK → Dim State                                                     |
| County            | text | County name (degenerate dimension; races are unique per state+county+cycle) |
| CandidateKey      | int  | FK → Dim Candidate                                                 |
| Votes             | int  | Votes cast for this candidate in this county                       |
| County Total Votes| int  | Total votes for the office in this county — **repeats on every candidate row** |
| Ballots Cast      | int  | Total ballots cast in this county — **repeats on every candidate row** |
| Registered Voters | int  | Registered voters in this county — **repeats on every candidate row** |

> ⚠️ Never SUM `County Total Votes`, `Ballots Cast` or `Registered Voters`
> directly from the fact table — they repeat per candidate and would be
> counted once per candidate. The `County Total Votes`, `Ballots Cast` and
> `Registered Voters` measures in `measures.dax` de-duplicate them with
> `SUMX ( SUMMARIZE ( ..., MAX ( ... ) ) )` per county.

## Relationships

```
Dim State     [StateKey]      1 ───< * Fact Results [StateKey]
Dim Candidate [CandidateKey]  1 ───< * Fact Results [CandidateKey]
```

Both relationships are single-direction (dimension filters fact). `Cycle`
lives on the fact table (and as an attribute on Dim Candidate), so cycle
slicers come from `Fact Results[Cycle]`; cycle-over-cycle measures use
`CALCULATE` with `Cycle - 4` for presidential cycles.

## Measures

All measures live in `measures.dax`. Summary:

| Measure | What it answers |
|---------|-----------------|
| Total Votes | Votes for the candidates in context |
| Vote Share % | Candidate/party share of the whole race in context |
| Two-Party Vote Share % | Share normalized over DEM + REP votes only |
| County Total Votes / Ballots Cast / Registered Voters | De-duplicated county-level totals |
| Turnout % | Office votes ÷ ballots cast |
| Winner | Name of the winning candidate in context |
| Margin (Votes) / Margin % | Winner's lead over the runner-up |
| Votes (Previous Cycle), Vote Share % (Previous Cycle) | Same context, previous presidential cycle |
| Vote Share Swing (pp) | Cycle-over-cycle change in vote share, in percentage points |
| Vote Growth % | Cycle-over-cycle change in raw votes |

## Report pages

### Page 1 — Overview (map)

- Filled map on `Dim State[State Name]`, colored by DEM `Vote Share %` with a
  diverging scale; tooltip shows REP share, `Margin %` and `Turnout %`.
- KPI cards: `Total Votes`, `Turnout %`, closest state by `Margin %`.
- Bar chart: states ranked by `Margin (Votes)`.
- Slicer: `Cycle`.

### Page 2 — Vote-share breakdown

- 100% stacked bar: vote share by candidate within each state
  (`Vote Share %` on axis, `Dim Candidate[Candidate]` as legend).
- County matrix: rows = state + county, columns = candidates, values =
  `Votes` and `Vote Share %`, with data bars; drill-down from state to
  county.
- Slicers: `Cycle`, `Party`.

### Page 3 — Swing analysis

- Bar chart of `Vote Share Swing (pp)` by state for DEM and REP, zero line
  emphasized; counties available on drill-down.
- Scatter: `Margin %` (x) vs. `Turnout %` (y), one point per county, colored
  by `Winner`.
- Table of the ten closest counties by `Margin (Votes)` with both cycles'
  shares side by side.

## Rebuilding the .pbix in Power BI Desktop

1. Run `python main.py` in this repository — it validates the raw data,
   builds the model and writes `out/dim_state.csv`, `out/dim_candidate.csv`
   and `out/fact_results.csv`.
2. In Power BI Desktop: **Get Data → Text/CSV** for each of the three files.
3. Rename the tables to `Dim State`, `Dim Candidate` and `Fact Results`
   (the measure definitions depend on these exact names).
4. In **Model view**, create the two relationships listed above and set the
   marked key columns as keys. Hide the key columns from report view.
5. Create an empty **Measures** table (Enter Data with one dummy column,
   then delete the column) and paste each measure from `measures.dax` via
   **New measure**; apply the format strings noted in the file.
6. Build the three pages as specified above; set the map to use
   `State Name` as the location field.
7. Save as `us-elections-vote-share.pbix`.

To refresh with a new cycle or a full extract, drop the new `results_YYYY.csv`
into `sample_data/`, re-run `python main.py`, and refresh the dataset — no
model changes are needed.
