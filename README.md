# Fingerprinter

This utility library can be used to create SHA256 fingerprints
using globs and paths. It is meant to be a replacement
for the `sources/fingerprints.sh` in 
[common-build-scripts].

## Installation

- using **pip**: `pip install git+https://github.com/UWIT-IAM/fingerprinter@0.1`
- using **poetry**: `fingerprinter = { git = "https://github.com/UWIT-IAM/fingerprinter.git", tag="v0.1" }`


## Use

```
python -m fingerprinter.cli --help
```


### Configuration File

To get started, you'll need a configuration file. This file is a yaml file
that defines your fingerprint targets. 

```yaml
targets:
  target-name: 
    include-paths:
      - src/**.py   # Glob to match all python files recursively under a directory
      - src/        # Will match every file under src/, recursively. (Same as 'src/**')
      - src         # interchangeable with `src/` or `src/**`
      - src/foo.py  # Include a specific file
```

You may also declare other targets as dependencies:

```yaml
# This example has a source fingerprint that is generated for all python files
# under the src/ directory, but the fingerprint is dependent on the 
# dependency locks. This means that even if all python files remain
# untouched, an update to the dependencies will generate a new
# source fingerprint. 
# `fingerprints.yaml` is also included here to ensure that changes
# to the actual fingerprint configuration regenerates all fingerprints.
targets:
  dependencies:
    include-paths:
      - poetry.lock
      - fingerprints.yaml 
  source:
    depends-on: [dependencies]
    include-paths: ['src/**.py']
```

**All paths will be lexicographically sorted at runtime**, however dependencies
are always resolved in the order provided.

`python -m fingerprinter.cli -f fingerprints.yaml -t source` will do the rest!

### Excluding Files

There may be some paths that you never want to consider. For instance `__pycache__` is
always excluded by default, no matter where it falls. 

You can exclude paths at the base of your yaml:

```yaml
ignore-paths:
  - __pycache__   # Never necessary, this path is always ignored
  - .secrets      # Entire directory will always be ignored wherever it is in the tree
  - secret.py     # Will be ignored in every directory it exists in.

targets:
  foo:
    # Will include src/foo/bar, but not src/.secrets/sekret or src/foo/__pycache__/blah
    include-paths: ['src']
```


[common-build-scripts]: https://github.com/uwit-iam/common-build-scripts
