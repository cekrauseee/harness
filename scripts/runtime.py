"""Private process entry point, separate from the public command surface."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness.config import Home
from harness.processes import guard, supervise

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
commands = parser.add_subparsers(dest="operation", required=True)
p = commands.add_parser("supervise")
p.add_argument("run")
p = commands.add_parser("guard")
p.add_argument("run")
p.add_argument("pid", type=int)
p.add_argument("identity")
args = parser.parse_args()
if args.operation == "supervise":
    supervise(Home(args.root), args.run)
else:
    guard(Home(args.root), args.run, args.pid, args.identity)
