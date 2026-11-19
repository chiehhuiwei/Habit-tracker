#!/bin/bash
set -e

cd /home/a0976395798/Habit-tracker

conda activate dev

# Install uv if not already present (single binary, no extra deps)
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install Python dependencies with uv (10-100x faster than pip)
uv pip install -r requirements.txt

sudo apt install -y fonts-wqy-zenhei fonts-wqy-microhei
