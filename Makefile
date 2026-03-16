.PHONY: test lint install-dev validate-examples dry-run-examples

install-dev:
	pip install -r requirements-dev.txt

test:
	python3 -m pytest tests/ -v

lint:
	ruff check scripts/ tests/

coverage:
	coverage run -m pytest tests/ -v
	coverage report --fail-under=75

validate-examples:
	python3 scripts/validate-config-json.py examples/01-simple-edit.json
	python3 scripts/validate-config-json.py examples/02-multi-file-edit.json
	python3 scripts/validate-config-json.py examples/03-file-operations.json
	python3 scripts/validate-config-json.py examples/04-modern-code-edit.json
	python3 scripts/validate-config-json.py examples/05-all-edit-actions.json

dry-run-examples:
	python3 scripts/execute-json-ops.py examples/01-simple-edit.json --dry-run
	python3 scripts/execute-json-ops.py examples/02-multi-file-edit.json --dry-run
	python3 scripts/execute-json-ops.py examples/03-file-operations.json --dry-run
	python3 scripts/execute-json-ops.py examples/04-modern-code-edit.json --dry-run
	python3 scripts/execute-json-ops.py examples/05-all-edit-actions.json --dry-run
