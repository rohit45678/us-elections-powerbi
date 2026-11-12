# US Elections Vote-Share Analysis
Advanced Power BI project analyzing US election results and vote share: data modeling, DAX measures, and interactive reporting on voting patterns across geographies and election cycles.
**Tech stack:** Power BI, DAX, Data Modeling
**Highlights:** star-schema model; vote-share DAX measures; interactive drill-down reporting. (Freelance project.)

## What this repository contains

A `.pbix` is a binary file, so this repository holds everything needed to
reproduce the project end-to-end: the raw data extracts, a Python pipeline
that cleans and models them into a star schema with strict reconciliation
checks, the project's complete DAX measure library, and a model document
that specifies every table, relationship and report page — plus the steps
to rebuild the `.pbix` in Power BI Desktop from the generated tables.

Sample data: county-level presidential results for five swing states
(PA, GA, AZ, WI, MI — 17 counties) across the 2020 and 2024 cycles, with
candidates, votes, office totals, ballots cast and registered voters.
Dropping a fuller extract into `sample_data/` requires no code changes.

## Pipeline

```
main.py                  Entry point: prep + validation + summary
pipeline/
  prep.py                Raw CSVs -> dim_state / dim_candidate / fact_results
  validate.py            Reconciliation checks that fail loudly (non-zero exit)
  summary.py             Vote-share and swing tables computed from the data
sample_data/
  results_2020.csv       Raw county-level results, 2020 cycle (68 rows)
  results_2024.csv       Raw county-level results, 2024 cycle (68 rows)
measures.dax             The report's full DAX measure library
model.md                 Data model, relationships, report pages, rebuild steps
tests/                   Reconciliation tests (pytest-compatible)
out/                     Generated star-schema CSVs (git-ignored)
```

The model is a star schema at county grain. County-level values that repeat
on every candidate row (county total votes, ballots cast, registered voters)
are de-duplicated by the DAX measures rather than the fact table — see
`model.md` for why, and how the measures do it.

Validation runs on every build and checks, for every county race, that
candidate votes sum exactly to the recorded county total, that vote shares
sum to 100%, and that ballots cast cover the office total — then reconciles
the modeled tables back to the raw extracts (row counts, total votes,
foreign keys). A tampered fixture produces:

```
ERROR: raw data validation failed:
  - (2020, 'PA', 'Philadelphia'): candidate votes sum to 741996, county_total_votes says 742000
```

## DAX measures (measures.dax)

- **Vote Share %** — candidate share of the race in context (`ALL` on the
  candidate dimension inside `CALCULATE`)
- **Two-Party Vote Share %** — share normalized over DEM + REP votes only
- **Turnout %** — office votes ÷ ballots cast, built on county totals
  de-duplicated with `SUMX ( SUMMARIZE ( ..., MAX ( ... ) ) )`
- **Margin (Votes) / Margin %** — winner's lead over the runner-up, computed
  with `ADDCOLUMNS` / `MAXX` over the candidates in context
- **Winner** — name of the winning candidate in context
- **Vote Share Swing (pp)** and **Vote Growth %** — cycle-over-cycle change
  against `Cycle - 4` (presidential cycles)

## How to run

```bash
python main.py
```

This loads the extracts, runs all validations, writes the star schema to
`out/`, and prints the state-level vote-share summary. Then follow the
rebuild steps in `model.md` to assemble the report in Power BI Desktop.

## Sample output

```
== Vote share by state (%) ==
State            DEM 2020  REP 2020  DEM 2024  REP 2024  DEM swing
------------------------------------------------------------------
Arizona             50.7%     47.3%     48.1%     50.1%      -2.6p
Georgia             67.4%     30.6%     66.7%     31.5%      -0.8p
Michigan            60.2%     37.8%     60.1%     38.1%      -0.0p
Pennsylvania        67.4%     30.6%     66.5%     31.7%      -0.9p
Wisconsin           63.6%     34.4%     63.7%     34.5%      +0.1p
```

(Shares are over the sampled counties in each state, which are the
most populous ones.)

## Tests

```bash
python tests/run_tests.py     # dependency-free runner
pytest tests/                 # also works if pytest is installed
```

The suite verifies fixture reconciliation (candidate votes sum to county
totals, shares sum to 100% per race), star-schema integrity (row counts,
total-vote reconciliation, foreign keys, dimension uniqueness) and the
swing calculations against the fixture design.
