.PHONY: docs
init:
	python -m pip install nox coverage
test:
	# This runs all of the tests on all supported Python versions.
	nox -s test
ci:
	nox -s test

coverage:
	python -m coverage combine && python -m coverage report --ignore-errors --show-missing

docs:
	nox -s docs
	@echo "\033[95m\n\nBuild successful! View the docs homepage at docs/_build/html/index.html.\n\033[0m"
