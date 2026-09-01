.PHONY: install install-claudish uninstall test build publish release

install:
	python3 scripts/install.py install

install-claudish:
	python3 scripts/install.py install --target claude --with-claudish \
		--provider "$(or $(PROVIDER),ollama)"

uninstall:
	python3 scripts/install.py uninstall

test:
	python3 -m py_compile scripts/install.py scripts/release.py \
		src/claude_humanize_speaking/*.py tests/test_install.py
	python3 tests/test_install.py

build: test
	uv build

publish: build
	uv publish

release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=0.1.0" && exit 2)
	python3 scripts/release.py "$(VERSION)"
