PY ?= python
TASKS = data train artifacts predict test lint check app web web-dev
.PHONY: $(TASKS)

$(TASKS):
	$(PY) tasks.py $@
