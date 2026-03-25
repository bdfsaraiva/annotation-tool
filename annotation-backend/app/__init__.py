"""
LACE annotation tool — application package.

This module makes the `app` directory a Python package and exposes the
core sub-modules at the package level so they can be imported as
``from app import crud``, etc.
"""
from . import crud, models, schemas, auth, database, dependencies, config

__all__ = ['crud', 'models', 'schemas', 'auth', 'database', 'dependencies', 'config']
