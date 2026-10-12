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
#
# latexmk reads this file whatever it was asked to do, so the calls that
# compile nothing (cleaning up, printing the version or the help) are told
# apart here, from @ARGV, which latexmk has not parsed yet. Where there is no
# bash to run the script (system returns -1), the build goes on with a
# warning: a document that includes no page still compiles, and one that does
# stops at the page it cannot find.
my $figure_build = '.github/tools/figures/build.sh';
my $compiles = !grep { /^--?(c|C|CA|v|version|h|help|commands|showextraoptions)$/ } @ARGV;
if ( $compiles && -d 'figures/src' && -f $figure_build ) {
    my $status = system( 'bash', $figure_build, '--pdf-only' );
    if ( $status == -1 ) {
        warn "latexmk: no bash to run $figure_build; the PDFs under figures/assets/ were not built\n";
    }
    elsif ( $status != 0 ) {
        die "latexmk: the figure pages did not build; run $figure_build --pdf-only to see why\n";
    }
}
