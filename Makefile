.PHONY: docs
docs:
	@sphinx-build -b html docs/api docs/_build
