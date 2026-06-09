# Continus Bench CLI shim
# Allows `python3 -m continusbench` as an alternative to the `continusbench` binary
from continuousbench.cli.main import app

__all__ = ["app"]
