# Greenwash's own tests

Not a Suite. That word belongs to a Corpus Case's own tests, and blurring the
two is how you end up editing evidence. See `CONTEXT.md`.

```bash
.venv/bin/python -m pytest selftests -q
```

Runs offline. `test_verification_gate.py` drives the real Gate against
`corpus/01_invoice_extractor`, so it takes a few seconds per case run.
