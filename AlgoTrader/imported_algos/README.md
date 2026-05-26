# Imported Algorithms

This folder stores algorithms extracted from external projects by the `import_project` module.

## How it works

1. Drop any Nifty option trading project folder into `/Users/com/Desktop/R&D/`
2. Run: `python -m import_project.analyse <folder_name>`
3. The scanner detects strategy patterns, extracts entry/exit logic, and generates an AlgoBase class
4. The new algo file is saved here as `imported_algos/{folder}_{strategy}.py`
5. The new algo is auto-registered and can be backtested / compared with algo1/algo2/algo3

## Naming Convention

`{source_project}_{strategy_name}.py`

Example: `nifty_bot_v2_ema_crossover.py`
