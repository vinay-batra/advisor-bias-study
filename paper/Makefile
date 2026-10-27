# Build the paper. Requires tectonic (brew install tectonic); it downloads
# the packages it needs on first run and caches them.
#
# Two builds from one source. body.tex is shared; the \ifsubmission switch in
# shared.tex decides whether a section prints inline or as an appendix pointer.
#
#   main.pdf      reading build, single column, everything inline
#   main_acl.pdf  submission build, ACL two column, body under the page limit
#
# Nothing is cut between them: material that leaves the submission body moves
# to the appendix, where the venue's page limit does not reach.
#
# The appendix and the Method section's example pair are generated from
# data/items.jsonl, not written by hand, so `make` regenerates them first.
# Editing example_pair.tex or items_appendix.tex directly is pointless:
# the next build overwrites both.

TECTONIC ?= tectonic
PYTHON ?= python3
# analysis/figures.py needs numpy and matplotlib, which the repo venv has and
# the system python does not.
VENVPY ?= ../.venv/bin/python

GENERATED = example_pair.tex items_appendix.tex
# Each moved section, table and figure is its own file pulled in by body.tex.
# Without these a build after editing one of them alone is skipped as up to
# date and `make check` passes on the previous PDF.
PARTS = $(wildcard sec_*.tex) $(wildcard tab_*.tex) $(wildcard fig_*.tex)
# Tectonic ignores TEXINPUTS, so the style files live next to the paper as
# copies of the vendored originals rather than being found on a path.
ACLSTYLE = acl.sty acl_natbib.bst
FIGS = ../figures/fig1_forest_acl.pdf ../figures/fig2_effort_acl.pdf \
       ../figures/fig4_forest_pct_acl.pdf ../figures/fig5_effort_pct_acl.pdf

all: main.pdf main_acl.pdf

# --keep-intermediates keeps the .aux, the only record of what number or
# appendix letter each label resolved to. Without it tectonic skips writing
# one and a leftover from an earlier run sits beside a fresh PDF reading as
# current.
main.pdf: main.tex shared.tex body.tex refs.bib $(GENERATED) $(PARTS) $(FIGS)
	$(TECTONIC) -X compile main.tex --keep-logs --keep-intermediates --untrusted

main_acl.pdf: main_acl.tex shared.tex body.tex refs.bib $(GENERATED) \
              $(PARTS) $(ACLSTYLE) $(FIGS)
	$(TECTONIC) -X compile main_acl.tex --keep-logs --keep-intermediates --untrusted

acl.sty: aclstyle/acl.sty
	cp $< $@

acl_natbib.bst: aclstyle/acl_natbib.bst
	cp $< $@

$(GENERATED): ../data/items.jsonl render_items.py
	cd .. && $(PYTHON) paper/render_items.py

$(FIGS): ../analysis/figures.py ../data/responses.jsonl
	cd .. && $(VENVPY) analysis/figures.py

# The submission body must fit the venue page limit. References, appendices
# and Limitations do not count, so this measures to \label{xbodyend} rather
# than counting pages in the PDF.
pages: main_acl.pdf
	@$(PYTHON) pagecheck.py main_acl.log

# Fails loudly on anything that would embarrass the paper in review: an
# unresolved citation, a dangling cross reference, a duplicated label, a line
# past the margin, or a body over the page limit.
check: main.pdf main_acl.pdf
	@for f in main main_acl; do \
	  ! grep -qE "undefined" $$f.log || { echo "$$f:"; grep -E "undefined" $$f.log; exit 1; }; \
	  ! grep -q "multiply defined" $$f.log || { echo "$$f:"; grep "multiply defined" $$f.log; exit 1; }; \
	  ! grep -q "Overfull" $$f.log || { echo "$$f:"; grep "Overfull" $$f.log; exit 1; }; \
	done
	@echo "clean: no undefined references, no duplicate labels, no overfull lines"
	@$(PYTHON) pagecheck.py main_acl.log
	@$(PYTHON) branchaudit.py
	@$(PYTHON) numaudit.py

clean:
	rm -f main.pdf main.log main.blg main.aux main.bbl main.out main.xdv
	rm -f main_acl.pdf main_acl.log main_acl.blg main_acl.aux main_acl.bbl \
	      main_acl.out main_acl.xdv

.PHONY: all check clean pages
