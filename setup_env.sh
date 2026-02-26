#!/bin/bash

set -e

echo "Creating virtual environment..."
python3 -m venv gym_env

echo "Activating virtual environment..."
source gym_env/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing swig (required for Box2D)..."
pip install swig

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "Setup complete, activate the environment with:"
echo "  source gym_env/bin/activate"
