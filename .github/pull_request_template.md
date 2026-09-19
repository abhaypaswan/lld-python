## What this changes

<!-- One or two sentences. -->

## If this adds a problem

- [ ] `README.md` with requirements, a ```mermaid class diagram, and the
      reasoning behind each pattern used
- [ ] `meta.json` listing only patterns the code genuinely uses
- [ ] `src/main.py` runs to completion with no input
- [ ] Implementation uses the standard library only
- [ ] Tests cover the cases the design exists to handle, not just the happy path

**What does it teach that the existing problems do not?**

<!-- The question that decides whether it goes in. -->

## Checks

```bash
python3 -m pytest
python3 scripts/validate.py
python3 scripts/build_catalog.py
ruff check . && ruff format .
```

- [ ] All of the above pass
- [ ] Generated files (`catalog.json`, the README table, `docs/patterns.md`)
      are committed and current

## Anything worth a second look

<!-- A trade-off you were unsure about, a test you could not write, a follow-up
     you deliberately left out. Saying so is more useful than leaving it. -->
