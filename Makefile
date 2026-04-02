PYTHON ?= python3

.PHONY: install-dev test smoke build check

install-dev:
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke:
	printf '/exit\n' | $(PYTHON) -m codecore
	printf '/exit\n' | $(PYTHON) -m codecore --split

build:
	$(PYTHON) -m build --no-isolation

check: test smoke build
