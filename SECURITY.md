# Security Policy

## Supported Python versions

| Version | Tested in CI |
| ------- | ------------ |
| 3.13.x  | ✅ |
| 3.12.x  | ✅ |
| 3.11.x  | ✅ |
| 3.10.x  | ✅ |
| ≤ 3.9   | ❌ |

3.10 is the floor: the implementations use `X | None` in annotations that are
evaluated at runtime.

## Scope

This repository is teaching material. Every problem is a self-contained
command-line program using only the standard library — nothing here opens a
socket, reads a credential, or runs untrusted input. The realistic issues are
therefore bugs in the designs themselves rather than vulnerabilities, and those
are best raised as [issues](https://github.com/abhaypaswan/lld-python/issues).

Do not copy these implementations into production systems without review. They
are written to make a design idea legible, and several deliberately leave out
concerns a real system needs — concurrency above all. Each problem's README
lists what it omits under "Follow-ups".

## Reporting

If you do find something genuinely security-relevant, or a problem with the
repository's CI or dependencies:

- [Open an issue](https://github.com/abhaypaswan/lld-python/issues), or
- Email Abhay Paswan — work.abhaypaswan@gmail.com
