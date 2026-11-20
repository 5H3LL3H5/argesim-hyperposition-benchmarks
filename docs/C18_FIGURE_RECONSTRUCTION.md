# C18 identification on the published curves

The figure demo reads the four vector traces drawn in Figures 1 and 2 of
Belič's C18 definition. It covers both thickening and force for the first
(training) and second (validation) muscle. Each signal has 2,000 samples
on the 100 Hz grid from 0.00 to 19.99 s. The original instrument or filtered
measurement files have not been recovered. C18 therefore remains `specified`.

## Provenance and reproduction

The extract uses the axis frames in the publisher's PDF. Their horizontal
extent spans 20 s and their vertical extent spans 0 to 1. The endpoints of
the artwork's line and cubic Bézier segments lie within 0.249 of a 100 Hz
sample interval of the corresponding integer grid locations. The extractor
snaps the endpoints to that grid. Between them it inverts the Bézier's time
coordinate before evaluating its ordinate. It verifies continuity across PDF
paths. The final vertex is at sample 1,999. Six decimal places preserve the
reconstruction for reproduction. They do not describe instrument accuracy.

The package includes the numerical CSV, so running the benchmark requires
only Python. Regeneration uses PyMuPDF 1.26.6 and the edition identified below.
The extractor checks the PDF hash before reading its layout. The two related
signals for each muscle have a separate combined signal hash in the CLI output.

| Input or artifact | SHA-256 |
|---|---|
| Publisher's definition PDF | `af31e3a2c385d498529c89482f20764b8629f42e353b25a7017f0bd3d7507886` |
| [Packaged reconstruction](../argesim_benchmarks/data/c18_figure_traces.csv) | `36ca0ab924cb98d34cd285a2147b358cc941452c6c5c7fafbeb7ae6dd1c75a42` |

An independent check solved the cubic polynomials for the 4,712 interior
sample abscissas on those curves. It compared all 8,000 ordinates against the
packaged CSV. The maximum difference was 0.00000050, consistent with the
CSV rounding. The older demo interpolated 101 anchors per channel and added
an endpoint at 20 s. Reproduction of that historical demo remains available
at commit `5082b9a1c27a07e4ce2cdd60689260346a3a6b73`.

```sh
python scripts/c18_digitize_definition.py C18-definition.pdf /tmp/c18_figure_traces.csv
cmp /tmp/c18_figure_traces.csv argesim_benchmarks/data/c18_figure_traces.csv
python -m argesim_benchmarks run C18 all --kwargs-json '{"use_digitized":true}'
python -m argesim_benchmarks run C18 all --kwargs-json '{"training":"train.csv","validation":"holdout.csv"}'
```

## Linear reference and identification results

Applying the published second-order transfer coefficients without fitting to
the reconstructed curves yields correlations of 0.95347 and 0.94231 over the
full displayed signals. Both round to the 0.95 and 0.94 reported by Belič.
Least-squares refitting to the digitization produces different coefficients
(1.760091, −0.769501, 0.308333, −0.301893). Agreement of the published model's
correlations does not recover the input samples used for its identification.

The table gives the results of the default 400-epoch run on the packaged
figure demo. Each scored prediction starts at index 2. The first two measured
outputs supply the initial state and are excluded from the metrics.

| Model | Training correlation | Independent muscle correlation |
|---|---:|---:|
| Refit second-order ARX | 0.94180 | 0.93299 |
| ARX plus static residual network | 0.95811 | 0.94371 |
| Dynamic network, free-running feedback | 0.89965 | 0.88609 |
| Dynamic network, one-step prediction with measured history | 0.98581 | 0.98482 |

Task C trains from seeds 18, 19 and 20. Each candidate learns from the first
muscle's one-step examples and is ranked by its free-running training RMSE.
The three RMSEs are 0.14567, 0.16580 and 0.14047, so seed 20 is selected.
The second muscle is used to evaluate that selection. The CLI returns every
trial and the selected seed. A single seed can be requested explicitly through
`dynamic_seeds`. Identical training and validation signal pairs are rejected
even if CSV filenames or numeric formatting differ.

The original C18 definition calls for repeated dynamic-network training. The
reference solution distinguishes linear, parallel and dynamic model results.
The official catalog and the SNE index link the definition and solution
papers. No original training/validation data pair was found in those links.

- A. Belič, *Identification of Nonlinear Dynamics – Neural Networks versus Transfer Functions*, 2005. [Definition PDF](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf).
- A. Belič, *A Classic MATLAB-based Solution of ARGESIM Benchmark C18*, SNE 17(3–4), pp. 77–78. [Publication](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_17_34/sne.17.34.pdf).
- [ARGESIM catalog](https://www.argesim.org/benchmarks/c18) · [SNE definition and solutions](https://www.sne-journal.org/benchmarks/c18).
