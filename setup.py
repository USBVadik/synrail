from setuptools import setup


setup(
    name="synrail",
    version="0.1.0",
    description="Guided control for reliable agent execution.",
    py_modules=["alpha", "reference_runner"],
    packages=["synrail", "synrail.tools", "synrail.tools.reference"],
    package_dir={"synrail": "."},
    include_package_data=True,
    package_data={"synrail": ["schemas/*.json", "tools/reference/*.sh"]},
    zip_safe=False,
    entry_points={"console_scripts": ["synrail=alpha:main"]},
)
