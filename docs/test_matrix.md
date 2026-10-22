# Test matrix

| # | Scenario | Where tested | Owner | Status |
|---|---|---|---|---|
| 1 | Success chain, outputs correct | integration/test_api_flow.py | P5 | todo |
| 2 | Branch and merge order is stable | integration/test_api_flow.py | P5 | todo |
| 3 | Cycle rejected with clear error | integration/test_api_flow.py | P5 | todo |
| 4 | Version conflict gives 409 | integration/test_api_flow.py | P5 | todo |
| 5 | Retry then success (2 attempts) | integration/test_api_flow.py | P5 | todo |
| 6 | Retries exhausted, downstream skipped | integration/test_api_flow.py | P5 | todo |
| 7 | Old run unchanged after graph edit | integration/test_api_flow.py | P5 | todo |
| 8 | Bad input gives 4xx, not 500 | integration/test_api_flow.py | P5 | todo |
| 9 | Foreign keys enforced | integration/test_db_rules.py | P5 | todo |
| 10 | Duplicate edge rejected by DB | integration/test_db_rules.py | P5 | todo |
| 11 | Restart marks stale run INTERRUPTED | manual | P5 | todo |
| 12 | Refresh keeps workflows and history | manual | P5 | todo |
| 13 | Keyboard use and labels in editor | manual review | P5 | todo |
| 14 | Clean migration on empty DB | manual | P5 | todo |