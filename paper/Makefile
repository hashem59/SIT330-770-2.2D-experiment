# Makefile — SIT330-770 Distinction Task 2.2D
# Build: pdflatex → biber → pdflatex → pdflatex
# Requires: pdflatex, biber  (latexmk optional — not used here)

TEXFILE = introduction
PDFLATEX = pdflatex -interaction=nonstopmode

.PHONY: all clean

all: $(TEXFILE).pdf

$(TEXFILE).pdf: $(TEXFILE).tex references.bib
	@echo "==> Pass 1: pdflatex"
	$(PDFLATEX) $(TEXFILE).tex
	@echo "==> Biber: process bibliography"
	biber $(TEXFILE)
	@echo "==> Pass 2: pdflatex"
	$(PDFLATEX) $(TEXFILE).tex
	@echo "==> Pass 3: pdflatex (resolve cross-references)"
	$(PDFLATEX) $(TEXFILE).tex
	@echo "==> Done. Output: $(TEXFILE).pdf"

clean:
	@echo "==> Removing build artefacts"
	rm -f $(TEXFILE).aux \
	      $(TEXFILE).bbl \
	      $(TEXFILE).bcf \
	      $(TEXFILE).blg \
	      $(TEXFILE).log \
	      $(TEXFILE).out \
	      $(TEXFILE).run.xml \
	      $(TEXFILE).synctex.gz \
	      $(TEXFILE)-blx.bib
	@echo "==> Clean done."
