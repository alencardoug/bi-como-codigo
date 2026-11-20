"""The prototype's modules are scripts of `prototypes/framework/`, not a package."""

import pathlib
import sys

FRAMEWORK = pathlib.Path(__file__).resolve().parents[1]
if str(FRAMEWORK) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK))
