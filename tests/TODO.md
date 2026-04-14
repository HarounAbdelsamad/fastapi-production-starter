# TODO - `tests/`

Integration and behavior tests belong here.

## How to add tests
- Mirror production modules with `test_<module>.py`.
- Cover success path + validation failures + auth failures.
- Use fixtures from `conftest.py` and keep tests isolated.

## Rule
- Every new endpoint/service behavior should include tests before merge.
