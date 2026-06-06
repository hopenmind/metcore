# `hopenmind-cli`

Unified `hopenmind` command — one CLI root, auto-discovers sub-packages
via entry-points, distributes their commands under the same tree.

```bash
hopenmind list                           # what's installed
hopenmind install ng-vol                 # PyPI install
hopenmind install -e ./packages/ng-vol   # editable from local path
hopenmind install git+https://github.com/hopenmind/hopenmind-suite
hopenmind doctor                         # env + hardware report
hopenmind triage -s "exp(-w**2)" --t-max 10.0
```

Sub-packages register via:

```toml
[project.entry-points."hopenmind.subcommands"]
myname = "my_package.cli:app"
```
