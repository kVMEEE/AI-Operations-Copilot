#!/usr/bin/env bash
# exit on error
set -o errexit

echo "===> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "===> Compiling C++17 Core Analytics Engine..."
make -C cpp_engine

echo "===> Render Build Completed Successfully!"
