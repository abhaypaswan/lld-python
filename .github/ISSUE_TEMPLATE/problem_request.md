---
name: Request a problem
about: Suggest a low-level design problem to add
title: 'Add: '
labels: new problem
---

**The problem**

What would a candidate be asked to design?

**What it teaches that the existing ones do not**

This is the part that decides it. Seventeen problems already cover all twenty
patterns in `schema/problem.schema.json`, so a new one earns its place by
exercising something they do not — a constraint, a failure mode, a trade-off.

Have a look at [docs/patterns.md](../../docs/patterns.md) and the existing
problem list first.

**Patterns you would expect it to use**

**Where it is asked**

Companies known to ask it, if you know of any. Reported, not guessed.

**Are you planning to write it?**

If so, `python3 scripts/new_problem.py <slug>` scaffolds the whole directory,
and `CONTRIBUTING.md` says what each piece needs.
