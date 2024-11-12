#!/usr/bin/env bash

# Exit if something fails
set -e

# Find and change to the repository directory
repo_dir=$(git rev-parse --show-toplevel)
cd "${repo_dir}"

# Removing existing files in /dist
rm -rf dist

# Build the packages
for pkg in pasqal-cloud pulser-pasqal
do
  echo "Packaging $pkg"
  python -m build $pkg --sdist --wheel --outdir dist/
  rm -r $pkg/build
done

echo "Built distributions:"
ls dist
