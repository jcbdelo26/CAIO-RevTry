# Validation Commands

**Last Updated**: 2026-03-11
**Valid Through**: 2026-06-30

## Test Suite

```powershell
# Full suite (from src/ directory)
Set-Location 'E:\Greenfield Coding Workflow\Project-RevTry\src'
python -m pytest tests -q

# Or from project root
cd "E:\Greenfield Coding Workflow\Project-RevTry"
PYTHONPATH=src python -m pytest src/tests -q
```

## Syntax Check

```powershell
Get-ChildItem -Path src -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## Current Baseline

- **379 passed** (as of 2026-03-11)
- 29+ test files
