# Trust Report — 09_sql_verified

**The feature.** Turns a question into a SQLite query — the same feature as case 06, guarded by a suite that runs it.

**The suite.** Executes each query against a fixture database and checks the answer against numbers worked out by hand. The second precision control.

**Kill rate: 100%** — 4 of 4 sabotages were noticed.

No sabotage survived this suite.

## What the auditor expected, before it ran anything

Predicted misses: `sql.swap_aggregate`

Actually missed: (none)

> The suite checks for correct aggregate functions and row counts, so a SUM to COUNT swap would likely be caught, while dropping WHERE clauses would fail the row count test.

The prediction is kept as evidence and never reported as a finding. Findings come from runs.
