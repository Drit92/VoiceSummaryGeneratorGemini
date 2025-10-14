#!/bin/bash

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create Streamlit config directory
mkdir -p ~/.streamlit/

# Write Streamlit configuration
echo "\
[server]\n\
headless = true\n\
enableCORS = false\n\
port = $PORT\n\
\n\
" > ~/.streamlit/config.toml
