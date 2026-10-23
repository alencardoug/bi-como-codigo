# The commands of this repository. `make check` is the gate before every commit:
# commit only when it exits 0, read from its own exit code — never through a pipe.

.DEFAULT_GOAL := help
.PHONY: help sync docs-check adr-check secrets secrets-history test check

UV_RUN := uv run --frozen

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

sync: ## Install the locked environment (uv.lock) into .venv
	uv sync --frozen

docs-check: ## Links, anchors, ADR citations and pinned links into mvp_eng_dados_1
	@$(UV_RUN) python -m bi_como_codigo.docs_check

adr-check: ## The decision record as one transaction: numbering, index and the README count
	@$(UV_RUN) python .claude/skills/adr/verify.py

secrets: ## Secrets review of the tracked files and of .gitignore
	@$(UV_RUN) python -m bi_como_codigo.secrets_review

secrets-history: ## Every blob of the history, by credential shape, with no .env
	@$(UV_RUN) python -m bi_como_codigo.secrets_review --history

test: ## The test suite of the checks themselves
	@$(UV_RUN) pytest -q

# The links into mvp_eng_dados_1 carry most of the plan's facts, so the gate
# verifies them: ENG_DADOS_DIR names a local checkout of that project, by
# variable and never by a fixed path. Without it, `docs-check` lists them as
# not verified; `check` refuses to run.
check: ## The gate: secrets, history, documents, decision record and tests, stopping at the first failure; needs ENG_DADOS_DIR
	@test -n "$(ENG_DADOS_DIR)" || { echo "check: set ENG_DADOS_DIR to a checkout of mvp_eng_dados_1"; exit 2; }
	@test -e "$(ENG_DADOS_DIR)/.git" || { echo "check: ENG_DADOS_DIR=$(ENG_DADOS_DIR) is not a git checkout"; exit 2; }
	@$(UV_RUN) python -m bi_como_codigo.secrets_review
	@$(UV_RUN) python -m bi_como_codigo.secrets_review --history
	@$(UV_RUN) python -m bi_como_codigo.docs_check
	@$(UV_RUN) python .claude/skills/adr/verify.py
	@$(UV_RUN) pytest -q
