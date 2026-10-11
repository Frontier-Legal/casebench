"""An agent run as a command: prints its answer, or fails when asked to."""

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--question", required=True)
arguments = parser.parse_args()
if arguments.question == "fail":
    print("the model is unreachable", file=sys.stderr)
    sys.exit(3)
print(f"Answer to: {arguments.question}")
