---
name: Bug report
about: Something in a problem's code, tests or write-up is wrong
title: '[problem-slug] '
labels: bug
---

**Which problem**

e.g. `parking-lot`

**What is wrong**

A design that does not hold up is as much a bug as code that crashes. Both are
welcome.

**How to see it**

The most useful report is a failing test. If you can write one, paste it here —
it does not have to pass review, it just has to demonstrate the problem.

```python
def test_shows_the_bug(): ...
```

Otherwise, the commands you ran and what happened:

```
$ cd problems/... && python3 src/main.py
```

**What you expected instead**

**Environment**

- Python version:
- OS:
