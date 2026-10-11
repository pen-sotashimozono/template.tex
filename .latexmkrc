# LuaLaTeX + BibTeX (revtex4-2 uses bibtex, not biber)
$lualatex   = 'lualatex -shell-escape -interaction=nonstopmode -synctex=1 -file-line-error %O %S';
$pdf_mode   = 4;    # 1=pdflatex, 4=lualatex, 5=xelatex
$bibtex_use = 1;    # 1=bibtex

# Output directory (relative to root .tex file)
$out_dir = 'out';

# Clean targets (in addition to latexmk defaults)
$clean_ext = 'bcf run.xml synctex.gz synctex(busy) idx ind ilg acn acr alg glg glo gls ist nav snm vrb xdv';

# Figure pages. The PDFs under figures/assets/ are built from figures/src/ and
# not committed, so they are made here, before the document is compiled: the
# ones that are missing or older than their page, and nothing else. This is
# what lets a fresh clone, a CI runner and a release build the document with
# no step of their own. A page that fails stops the build.
my $figure_build = '.github/tools/figures/build.sh';
if ( -d 'figures/src' && -f $figure_build ) {
    system( 'bash', $figure_build, '--pdf-only' ) == 0
      or die "latexmk: the figure pages did not build; run $figure_build --pdf-only to see why\n";
}
