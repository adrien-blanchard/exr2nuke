"""Generate 1 grouped multilayer EXR output(s)."""

from .setup import create_setup as _create


def create_setup():
    return _create(1)
