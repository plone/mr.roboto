# mr.roboto development

### Defensive settings for make:
#     https://tech.davis-hansson.com/p/make/
SHELL:=bash
.ONESHELL:
.SHELLFLAGS:=-xeu -o pipefail -O inherit_errexit -c
.SILENT:
.DELETE_ON_ERROR:
MAKEFLAGS+=--warn-undefined-variables
MAKEFLAGS+=--no-builtin-rules


# Top-level targets

.PHONY: all
## Default target, build everything but don't run anything
all: build

.PHONY: build
## Install the buildout
build: ./.installed.cfg

.PHONY: run
## Run the web application development server
run: ./development.ini build
	./bin/pserve "$(<)" --reload

.PHONY: test
## Run the tests
test: build
# Run all checks but fail if any fail
	exit_status=0
	./bin/pytest || exit_status=$$?
	./bin/code-analysis --return-status-codes || exit_status=$$?
	./bin/versioncheck || exit_status=$$?
	exit $$exit_status

.PHONY: clean
## Remove all build artifacts
clean:
	rm -rf "./.venv/" "./bin/" \
	    "./eggs/" "./develop-eggs/" "./parts/" "./.installed.cfg"


# Real targets

 ./development.ini: ./development.ini.sample
	if test -e "$(@)"
	then
# Template has updated but the local version exists, stop running
	    diff -u "$(@)" "$(<)"
	    false
	else
# Copy the template initially
	    cp --backup=numbered -v "$(<)" "$(@)"
	fi

./.installed.cfg: ./.venv/bin/buildout ./src/mr.roboto/setup.py ./buildout.cfg
	"$(<)"

./.venv/bin/buildout: ./requirements.txt ./.venv/bin/pip
	.venv/bin/pip install --upgrade --upgrade-strategy=eager "wheel" "pip"
	.venv/bin/pip install -r "$(<)"

./.venv/bin/pip:
# Match ./.travis.yml
	python3.7 -m "venv" "$(@:%/bin/pip=%/)"
