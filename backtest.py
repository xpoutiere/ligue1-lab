"""Compatibilité : `python backtest.py` = `python -m ligue1lab.backtest`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("ligue1lab.backtest", run_name="__main__")
