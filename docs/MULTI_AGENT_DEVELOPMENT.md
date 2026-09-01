# Multi-Agent Critical Development Workflow

This workflow is the review gate for changes to prediction, scoring, risk,
backtesting, data persistence, and dashboard behavior.

## Roles

1. **Implementer** owns the change, its assumptions, and the initial tests.
2. **Quantitative skeptic** independently checks formulas, units, calibration,
   look-ahead/survivorship bias, leakage, sample sufficiency, and whether claims
   exceed what the data supports.
3. **Integration auditor** traces the full contract from live scan through raw
   and summary persistence into both dashboards, including legacy data.
4. **Adversarial validator** attacks missing, sparse, NaN, infinite, stale, and
   malformed inputs and verifies chart and UI behavior.
5. **Lead synthesizer** resolves disagreements, applies fixes, runs the final
   gates, and records accepted residual risk. The implementer cannot self-approve
   a high-impact model change.

## Required gates

Every prediction or risk change must pass these gates before commit:

- **Claim gate:** State exactly what is predicted and what only measures risk.
- **Temporal gate:** Training and validation splits preserve time order; no
  future feature, revised fundamental, or forward-filled target leaks backward.
- **Baseline gate:** Compare against a naive/base-rate benchmark and the current
  production model using walk-forward evaluation.
- **Calibration gate:** Report probability calibration (Brier score or log loss)
  in addition to direction accuracy and return metrics.
- **Risk gate:** Report drawdown, volatility, expected shortfall, turnover, and
  transaction-cost sensitivity; never optimize on Sharpe alone.
- **Contract gate:** Live scan, nightly scan, SQLite migration, V1 dashboard,
  V2 dashboard, CSV export, and legacy rows remain compatible.
- **Adversarial gate:** Tests cover insufficient history, zero variance, gaps,
  invalid numeric data, low liquidity, and empty/missing dashboard columns.
- **Reproducibility gate:** Record data window, universe, seed, dependencies,
  model artifact hash, and configuration used to produce results.

## Review protocol

The lead gives all reviewers the same change description and acceptance
criteria. Reviewers work independently and return findings labeled:

- `P0`: corrupts data or can generate materially unsafe/misleading output
- `P1`: incorrect result or broken primary workflow
- `P2`: important robustness, calibration, or maintainability gap
- `P3`: polish or optional improvement

Each finding must contain evidence, affected path/line, impact, and a proposed
test. The lead deduplicates findings and records one disposition: fixed,
accepted with rationale, or deferred with an owner. P0/P1 findings block the
change. P2 findings require an explicit disposition.

## Final evidence packet

The handoff should contain:

- changed files and user-visible behavior;
- test commands and exact pass/fail counts;
- model/data evaluation window and baselines, when applicable;
- unresolved findings and limitations;
- confirmation that no live trading or personalized advice is produced.

For the current risk-analysis change, run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app.py app_v2.py run_nightly_scan.py backtest data debate indicators ml scoring ui tests
git diff --check
```
