## What a user will notice

<!-- One or two sentences. -->

## The test that proves it

<!-- Name the test. A scenario gets one test named after that scenario, the way a user would describe it. -->

## Decision record

<!-- If this adds a dependency, changes a public interface or changes a storage format, link the new or amended record under docs/decisions/. Otherwise write "none". -->

## Checklist

- [ ] Commit messages follow Conventional Commits and every commit is signed off (`git commit -s`).
- [ ] `uv run pytest`, `uv run ruff check .` and `uv run pyright` pass locally.
- [ ] Every file I touched still does the one job its docstring names, and no budget, limit or timeout is a bare number without its source.
