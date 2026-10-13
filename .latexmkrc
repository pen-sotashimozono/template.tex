# LuaLaTeX + BibTeX
$lualatex   = 'lualatex -shell-escape -interaction=nonstopmode -synctex=1 -file-line-error %O %S';
$pdf_mode   = 4;    # lualatex
$bibtex_use = 1;

# PDFs stand in out/, everything else in out/tmp/.
$out_dir = 'out';
$aux_dir = 'out/tmp';

$clean_ext = 'bcf run.xml synctex.gz synctex(busy) idx ind ilg acn acr alg glg glo gls ist nav snm vrb xdv';

# latexmk reads this file for every call, so calls that compile nothing are
# told apart here, from @ARGV.
my $compiles = !grep { /^--?(c|C|CA|v|version|h|help|commands|showextraoptions)$/ } @ARGV;

# Move what a build or an earlier version left in out/ besides PDFs.
if ( $compiles ) {
    mkdir $_ for grep { !-d } ( 'out', 'out/tmp' );
    if ( opendir( my $dh, 'out' ) ) {
        for my $f ( grep { !/^\./ && !/\.pdf$/ && -f "out/$_" } readdir $dh ) {
            rename "out/$f", "out/tmp/$f";
        }
        closedir $dh;
    }
}

# Figure pages: build the PDFs under figures/generated/ that are missing or
# older than their page. A failing page stops the build in CI only.
my $figure_build = '.github/tools/figures/build.sh';
if ( $compiles && -d 'figures/src' && -f $figure_build ) {
    my $status = system( 'bash', $figure_build, '--pdf-only' );
    if ( $status == -1 ) {
        warn "latexmk: no bash to run $figure_build; the figure PDFs were not built\n";
    }
    elsif ( $status != 0 ) {
        my $message = "latexmk: a figure page did not build; run $figure_build --pdf-only to see it";
        die "$message\n" if $ENV{CI} || $ENV{GITHUB_ACTIONS} || $ENV{GITHUB_RUN_ID};
        warn "$message\n";
    }
}

# After a build: for a document with `auto_diff = true` in docs.toml, render
# what changed since the last commit (skipped where the script is absent, as in
# the submission bundle). The synctex file, which latexmk writes next to the PDF,
# is moved to out/tmp/.
$success_cmd = 'if [ -f .github/scripts/auto_diff.sh ]; then sh .github/scripts/auto_diff.sh %R; fi; mv -f out/*.synctex.gz out/tmp/ 2>/dev/null; true';
