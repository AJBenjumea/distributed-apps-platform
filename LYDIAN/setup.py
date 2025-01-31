#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

version = {}
with open("lydian/__init__.py") as fp:
    exec(fp.read(), version)

# Dependencies
deps = []
with open("requirements.txt") as fp:
    deps = fp.read().splitlines()
deps = [x.strip() for x in deps]
deps = [x for x in deps if x and not x.startswith('#')]

setuptools.setup(
    name="vmware-lydian",
    version=version['__version__'],
    author="Vipin Sharma, Pradeep Singh, Spiro Kourtessis, Gavin Chang, Mahima Kothari, Kaustabh Duorah",
    author_email="sharmavipin@vmware.com",
    description="A generic Distributed (Python) Applications Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vmware/distributed-apps-platform",
    install_requires=deps,
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    package_data={
        'lydian.data': ['*']
        }
)
