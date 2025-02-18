# Copyright 2020 Pasqal Cloud Services development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import find_packages, setup

__version__ = ""
exec(open("pasqal_cloud/_version.py").read())

setup(
    name="pasqal-cloud",
    version=__version__,
    description="Software development kit for Pasqal cloud platform.",
    packages=find_packages(),
    package_data={"pasqal_cloud": ["py.typed"]},
    include_package_data=True,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    maintainer="Pasqal Cloud Services",
    maintainer_email="pcs@pasqal.io",
    python_requires=">=3.8",
    license="Apache 2.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
    ],
    url="https://github.com/pasqal-io/pasqal-cloud",
    install_requires=[
        "auth0-python >= 3.23.1, <4.0.0",
        "requests>=2.25.1, <3.0.0",
        "pyjwt[crypto]>=2.5.0, <3.0.0",
        "pydantic >= 2.6.0, <3.0.0",
    ],
    extras_require={
        "dev": {
            "ruff==0.6.9",
            "mypy==1.10.0",
            "pytest==8.1.1",
            "pytest-cov==5.0.0",
            "types-requests==2.31.0.1",
            "requests-mock==1.12.1",
        },
        "docs": {
            "mkdocs==1.6.1",
            "mkdocs-material==9.5.50",
            "mkdocstrings==0.27.0",
            "mkdocstrings-python==1.13.0",
        }
    },
)
