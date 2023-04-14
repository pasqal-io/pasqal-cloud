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
    python_requires=">=3.7",
    license="Apache 2.0",
    # TODO:
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
    ],
    url="https://github.com/pasqal-io/pasqal-cloud",
    install_requires=[
        "auth0-python==3.23.1",
        "requests==2.25.1",
        "pyjwt[crypto]==2.5.0",
    ],
    extras_require={
        "dev": {
            "black==20.8b1",
            "flake8==3.9.0",
            "flake8-import-order==0.18.1",
            "mypy==0.982",
            "pytest==6.2.5",
            "pytest-cov==2.11.1",
            "types-requests==2.25.1",
            "requests-mock==1.9.3",
        },
        ":python_version == '3.7'": [
            "typing-extensions==4.4.0",
        ],
    },
)
