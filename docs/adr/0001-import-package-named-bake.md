# Import package is `bake`, not `bakefile`

The PyPI package is `bakefile`, but the import package is `bake`. Users' task files are named `bakefile.py`, and a `bakefile` package on the import path would be shadowed by, or shadow, that file when it is loaded as a module. Renaming later would break every user's `from bake import ...`.
