"""Lanceur de tâches multiplateforme (Windows n'a pas `make`). Le Makefile y délègue.

Usage : python tasks.py <tâche>    (ex. python tasks.py test)
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
NPM = shutil.which("npm") or shutil.which("npm.cmd") or "npm"

TASKS = {
    "data": [[PY, "-m", "ligue1lab.core"]],                      # télécharge + contrôle
    "train": [[PY, "-m", "ligue1lab.ml"]],                       # modèles ML, test final
    "artifacts": [[PY, "make_artifacts.py"]],                    # JSON du site
    "predict": [[PY, "-m", "ligue1lab.predict"]],                # paper trading hebdo
    "test": [[PY, "-m", "pytest"]],
    "lint": [[PY, "-m", "ruff", "check", "."]],
    "check": [[PY, "-m", "ruff", "check", "."], [PY, "-m", "pytest"]],
    "app": [[PY, "-m", "streamlit", "run", "app.py"]],           # outil de labo interne
    "web": [[NPM, "--prefix", "web", "run", "build"]],
    "web-dev": [[NPM, "--prefix", "web", "run", "dev"]],
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        print(__doc__ + "\nTâches : " + ", ".join(TASKS))
        sys.exit(2)
    for cmd in TASKS[sys.argv[1]]:
        print("$", " ".join(map(str, cmd)))
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc:
            sys.exit(rc)


if __name__ == "__main__":
    main()
