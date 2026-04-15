from setuptools import find_packages, setup


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
    zip_safe=False,
    entry_points={"console_scripts": ["synrail=alpha:main"]},
)
