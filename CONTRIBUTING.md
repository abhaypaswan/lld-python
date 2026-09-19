# Contributing

New problems are the most useful thing you can add. Fixes to existing ones —
especially a test that shows a design is wrong — are just as welcome.

## Setting up

```bash
git clone https://github.com/abhaypaswan/lld-python.git
cd lld-python
pip install -r requirements-dev.txt
python3 -m pytest
```

## Adding a problem

Start with the scaffold rather than an empty directory:

```bash
python3 scripts/new_problem.py your-problem --difficulty medium --minutes 60
```

That creates every file described below, filled in with placeholders. It
already runs, already passes `validate.py`, and is already lint-clean — so you
can replace the pieces one at a time and keep everything green instead of
having nothing working until the end.

The layout it creates, under `problems/<slug>/` with a kebab-case slug:

```
problems/your-problem/
├── README.md
├── meta.json
├── src/
│   ├── main.py
│   └── your_problem/        # slug with underscores — see below
│       └── ...
└── tests/
    └── test_your_problem.py
```

**The package name must be the slug with underscores.** Every problem's `src/`
goes on `sys.path` at once (see the root `conftest.py`), so a shared package
name like `model` would mean the second problem to define it silently gets the
first one's module.

### What each piece needs

**`README.md`** — the problem statement, requirements, assumptions, a
` ```mermaid ` class diagram, an explanation of *why* the design is shaped the
way it is, how to run it, and the follow-ups an interviewer would ask.

The design rationale is the part that matters. "This uses the Strategy pattern"
is not interesting; "this uses Strategy because the eviction rule and the cache
change for different reasons, and here is the bug that avoids" is.

**`meta.json`** — validated against `schema/problem.schema.json`. Only list a
pattern the code genuinely uses. Claiming Observer because there is a callback
somewhere makes the catalog less useful for everyone.

**`src/main.py`** — a runnable demo. It must complete **without input** when run
as `python3 src/main.py`, because CI runs every demo. Put interactive mode
behind `--interactive`, and check `sys.stdin.isatty()` if you prompt.

Show something worth seeing. The best demos make a design decision visible: the
rate limiter runs all four algorithms over the same traffic, the cache replays
one access pattern under three eviction policies.

**`src/<package>/`** — standard library only. If a problem seems to need a
dependency, that is usually a sign the design is doing something the problem
did not ask for.

**`tests/`** — not for coverage. Pin down the behaviour the design exists to
guarantee, and the cases that are easy to get wrong:

- the failure that must leave nothing changed behind
- the arithmetic that has to come out exact
- the rule everyone forgets (a king may not castle *through* an attacked
  square; a pawn does not attack the square in front of it)

If a published oracle exists for your domain, test against it. Chess uses
perft counts; that one test is worth more than fifty hand-written ones.

Inject clocks and random sources rather than calling `time.time()` or
`random.random()` inside. No test should sleep.

## Before opening a pull request

```bash
python3 -m pytest              # all green
python3 scripts/validate.py    # every problem complete and consistent
python3 scripts/build_catalog.py   # refresh catalog.json, the README table, docs/patterns.md
ruff check . && ruff format .
```

CI runs all of these, plus every problem's demo, on Python 3.10 through 3.13.

Never hand-edit `catalog.json`, the problem table in `README.md`, or
`docs/patterns.md` — all three are generated from the `meta.json` files. The one
hand-written part of the patterns index is each pattern's explanation, which
lives in `scripts/patterns_reference.py`.

## Pull requests

1. Fork the repository
2. Branch: `problem/design-a-thing` for a new problem, `fix/...` otherwise
3. One problem per pull request
4. Say in the description what the problem teaches that the existing twelve
   do not

Thanks for contributing.
