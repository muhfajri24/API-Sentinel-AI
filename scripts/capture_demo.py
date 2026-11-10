"""Run optional Chromium QA/capture against owned fixture services; never calls Meta."""

import subprocess
from .local_services import ROOT, local_services


def main():
    with local_services(controller=True, ui=True):
        subprocess.run(["node", str(ROOT / "scripts/browser_check.cjs")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
