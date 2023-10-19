.PHONY: docs
init:
	python -m pip install -r requirements-dev.txt
test:
	# This runs all of the tests on all supported Python versions.
	tox -p
ci:
	python -m pytest tests --verbose --junitxml=report.xml

coverage:
	python -m pytest --cov-config .coveragerc --verbose --cov-report term --cov-report xml --cov=niquests tests

docs:
	cd docs && make html
	@echo "\033[95m\n\nBuild successful! View the docs homepage at docs/_build/html/index.html.\n\033[0m"
