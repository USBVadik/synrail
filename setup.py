import sys

from setuptools import find_packages, setup


# Some tester environments install through legacy `setup.py install` without
# `wheel`, which can otherwise fail while writing bytecode caches outside the
# venv on macOS command-line Python builds.
sys.dont_write_bytecode = True


setup(
    name="synrail",
    version="0.1.0",
    description="Guided control for reliable agent execution.",
    py_modules=["alpha", "reference_runner"],
    packages=find_packages(include=["tools*", "schemas"]),
    include_package_data=True,
    package_data={
        "tools": ["reference/*.json", "reference/*.sh"],
        "schemas": ["*.json"],
    },
    options={"install": {"compile": False}},
    zip_safe=False,
    entry_points={"console_scripts": ["synrail=alpha:main"]},
)
