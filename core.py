"""Compatibilité : `python core.py` = `python -m ligue1lab.core`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("ligue1lab.core", run_name="__main__")
