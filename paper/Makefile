# Build the paper. Requires tectonic (brew install tectonic); it downloads
# the packages it needs on first run and caches them.
#
# The appendix and the Method section's example pair are generated from
# data/items.jsonl, not written by hand, so `make` regenerates them first.
# Editing example_pair.tex or items_appendix.tex directly is pointless:
# the next build overwrites both.

TECTONIC ?= tectonic

all: main.pdf

main.pdf: main.tex refs.bib example_pair.tex items_appendix.tex
	$(TECTONIC) -X compile main.tex --keep-logs --untrusted

example_pair.tex items_appendix.tex: ../data/items.jsonl render_items.py
	cd .. && python3 paper/render_items.py

# Fails loudly on anything that would embarrass the paper in review:
# an unresolved citation, a dangling cross reference, or a line past the
# margin.
check: main.pdf
	@! grep -qE "undefined" main.log || { grep -E "undefined" main.log; exit 1; }
	@! grep -q "Overfull" main.log || { grep "Overfull" main.log; exit 1; }
	@echo "clean: no undefined references, no overfull lines"

clean:
	rm -f main.pdf main.log main.blg main.aux main.bbl main.out main.xdv

.PHONY: all check clean
