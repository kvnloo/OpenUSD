# usdview Labs routing evaluation

This harness asks one narrow question: **where, if anywhere, does Jev improve
usdview routing over the deterministic typed grammar?**

It generates exactly 144 labeled requests across:

- explicit prim selection;
- focus/path selection;
- raw prim paths;
- clear-selection aliases;
- viewer-mode aliases;
- read-only scene questions;
- deliberately unsupported / potentially mutating language.

The important negative cases are read-only questions and unsupported language.
A useful model router must learn to choose **no mutable action** there.

## Deterministic baseline

No network or provider dependency:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/experiments/intent_eval.py
```

This should be exact against the corpus by construction. If it regresses, fix
the deterministic contract before evaluating a model.

## Jev shadow evaluation

Live provider scoring is explicit:

```bash
python extras/usd/examples/usdviewPlugins/usdviewLabs/experiments/intent_eval.py \
  --jev --jsonl /tmp/usdview-jev-eval.jsonl
```

This uses the existing `JevShadowAdapter` and therefore the same:

- `jevkit.client`;
- `jevkit.keystore`;
- pinned requested revision `jev-1.13.0`;
- no-execution guarantee.

The summary reports accuracy/agreement per family and Jev p50/p95/max route
latency when available.

## Decision rule

Do not activate Jev merely because overall accuracy is high.

A useful activation experiment needs evidence that Jev improves a defined
ambiguous family while preserving near-perfect abstention on read-only and
unsupported requests, without unacceptable latency.
