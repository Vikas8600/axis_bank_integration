from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in axis_bank_integration/__init__.py
from axis_bank_integration import __version__ as version

setup(
	name="axis_bank_integration",
	version=version,
	description="Axis Bank Integration",
	author="Dexciss",
	author_email="skuthe@dexciss.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
