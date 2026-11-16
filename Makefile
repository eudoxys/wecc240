# `source` is a bash builtin; /bin/sh (dash on Ubuntu runners) lacks it
SHELL := /bin/bash
PACKAGE=$(notdir $(PWD))
SOURCE=$(wildcard $(PACKAGE)/*.py)
LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"
# scripts that run, or need files or packages, at import time; see issue #11
EXCLUDE='!wecc240.aggregate_.*' '!wecc240.build_.*' '!wecc240.viewer' '!wecc240.wecc240_gentypes'

all: docs test

docs: $(SOURCE)
	test -d .venv || python3 -m venv .venv
	(source .venv/bin/activate ; pip install --upgrade pip)
	(source .venv/bin/activate ; pip install --upgrade pdoc . -r requirements.txt)
	(source .venv/bin/activate ; pdoc $(PACKAGE)/__init__.py $(EXCLUDE) -o $@ --logo $(LOGO) --math --mermaid --logo-link $(LINK))

test:
	test -d .venv || python3 -m venv .venv
	(source .venv/bin/activate ; pip install -e . pytest ; pytest)

manifest:
	python3 .github/check_manifest.py

.PHONY: docs test manifest
