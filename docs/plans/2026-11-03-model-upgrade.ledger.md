# Ledger — plan: docs/plans/2026-11-03-model-upgrade.md

Task 1: complete (commit 8184dca, tests: pytest tests/test_v1_basics.py tests/test_invariants.py -v → 22 passed)
Task 2: complete (included in Task 1 commit - invariant tests created and passing)
Task 3: complete (included in Task 1 commit - v1 documentation created)
Task 4: complete (commit 53295b1, tests: pytest tests/test_v2_basics.py -v → 6 passed, full suite: 28 passed)
Task 5: complete (commit ae91d0a, tests: pytest tests/test_v2_financial.py -v → 3 passed, full suite: 31 passed)
Task 6: complete (commit 64c1201, tests: pytest tests/test_v2_market.py -v → 5 passed, full suite: 36 passed)
Task 7: complete (commit 14904eb, tests: pytest tests/test_v2_monitors.py -v → 9 passed, full suite: 45 passed)
Task 8: complete (commit 6a2f310, tests: pytest tests/test_v1_v2_comparison.py -v → 8 passed, full suite: 53 passed)
Task 9: complete (commit e264a11 - v2 documentation and comparison report created)
Task 10: complete (commit current - sweep scripts created, final verification passed, folder structure reorganized)

**Final Structure:**
```
TheGreatRetrofit/
├── v1/                          # Original model (queueing-financial)
│   ├── src/retrofit_v1/         # Core v1 package
│   ├── test_v1/                 # v1 tests (22 tests)
│   ├── docs/v1_documentation.md # v1 documentation
│   └── README.md
├── v2/                          # Upgraded model (agent-based)
│   ├── src/retrofit_v2/         # Core v2 package (8 modules)
│   ├── test_v2/                 # v2 tests (31 tests)
│   ├── docs/v2_documentation.md # v2 documentation
│   └── README.md
├── common/                      # Shared utilities
│   ├── src/common/              # rng, validation
│   └── (tests)
├── scripts/                     # Sweep & plotting scripts
├── docs/                        # Top-level docs
│   ├── comparison_report.md     # v1 vs v2 comparison
│   └── plans/                   # Implementation plans
├── data/                        # Output data
├── pyproject.toml
└── README.md (to be created)
```