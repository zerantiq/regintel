# Getting Started

## Install from PyPI

```bash
python -m pip install zerantiq-regintel
```

## Verify CLI Entry Points

```bash
regintel-scan --help
regintel-applicability --help
regintel-gate --help
```

## Local Development Install

```bash
python -m pip install -e ".[dev,docs]"
make check
```

## Build Documentation

```bash
python -m pip install -e ".[docs]"
mkdocs serve
```
