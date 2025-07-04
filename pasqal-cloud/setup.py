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
import os
from datetime import datetime, timedelta
from pathlib import Path

from setuptools import find_packages, setup

distribution_name = "pasqal-cloud"  # The name on PyPI
package_name = "pasqal_cloud"  # The main module name
description = "Software development kit for Pasqal cloud platform."
# Set deprecation date for 365 days later
deprecation_date = (datetime.today() + timedelta(days=365)).strftime("%Y-%m-%d")
current_directory = Path(__file__).parent

# Reads the version from the VERSION.txt file
with open(current_directory.parent / "VERSION.txt", "r", encoding="utf-8") as f:
    __version__ = f.read().strip()

# Changes to the directory where setup.py is
os.chdir(current_directory)

# Stashes the source code for the local version file
local_version_fpath = Path(package_name) / "_version.py"
with open(local_version_fpath, "r", encoding="utf-8") as f:
    stashed_version_source = f.read()

# Overwrites the _version.py for the source distribution (reverted at the end)
with open(local_version_fpath, "w", encoding="utf-8") as f:
    f.writelines(
        [
            f"__version__ = '{__version__}'\n",
            f"deprecation_date = '{deprecation_date}'\n",
        ]
    )

setup(
    name=distribution_name,
    version=__version__,
    packages=find_packages(),
    package_data={package_name: ["py.typed"]},
    include_package_data=True,
    description=description,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    maintainer="Pasqal Cloud Services",
    maintainer_email="pcs@pasqal.io",
    python_requires=">=3.9",
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
        "requests-mock==1.12.1",
    ],
    extras_require={
        "dev": {
            "ruff==0.6.9",
            "mypy==1.10.0",
            "pytest==8.1.1",
            "pytest-cov==5.0.0",
            "types-requests==2.31.0.1",
        },
        "docs": {
            "mkdocs==1.6.1",
            "mkdocs-material==9.5.50",
            "mkdocstrings==0.27.0",
            "mkdocstrings-python==1.13.0",
        },
    },
)

# Restores the original source code of _version.py
with open(local_version_fpath, "w", encoding="utf-8") as f:
    f.write(stashed_version_source)
