# Fork-only GfPlane native Python smoke (2026-10-23)

The CI workflow on this isolated branch checks out `kvnloo/OpenUSD` commit
`00efda239ab962ffa036f3f35f5863d9ce33a140` (fork PR #48),
installs the published `usd-core==26.8` binary, and executes the existing
`pxr/base/gf/testenv/testGfPlane.py` module. The smoke has a short timeout and
uses only read permissions.

**Validation boundary:** native `pxr` behavior with the exact candidate **test
file**, not C++ compiled from the candidate SHA. It cannot be substituted for
BuildUSD on the current OpenUSD codebase. A queued/running/green status is not
asserted until a real GitHub Actions run URL and logs have been checked.

No default-branch or upstream write; original PR #48 branch is untouched.
