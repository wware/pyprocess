# FROM ollama/ollama
FROM python:3.11-slim

# Install Python and pip with build dependencies
# RUN apt update && apt install -y --no-install-recommends \
#     python3-minimal \
#     python3-pip

# Install our testing tools
RUN pip3 install flake8 pylint pytest ruff

# Clean up apt cache to keep image size down a bit
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# COPY . /app
WORKDIR /app

# CMD ["python", "loop_runner.py", "."]
