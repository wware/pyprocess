#!/bin/bash -xe

export PYTHONPATH=$(pwd)

flake8 $(git ls-files | grep -E '\.py$')
python -m pylint $(git ls-files | grep -E '\.py$')

pytest replit_clone/tests/
pytest replit_clone/tests/ --test-mode=project-storage
pytest replit_clone/tests/ --test-mode=file-storage
pytest replit_clone/tests/ --test-mode=code-executor
pytest replit_clone/tests/ --test-mode=runtime-env
