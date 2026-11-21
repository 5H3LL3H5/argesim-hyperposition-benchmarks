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
CSV rounding.

For a supplied recording, the CSV must contain exactly `time_s`, `thickening`
and `force`, in any column order, with finite values on a uniform 100 Hz
grid. Both files are required. CLI results retain separate file and signal
hashes for these inputs. Use `use_digitized` to select the packaged demo.
[CSV loader](../argesim_benchmarks/models/c18_nonlinear_identification.py)

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

The following CPython 3.12 results use the packaged figure data and default
settings. Each scored prediction starts at index 2. The first two measured
outputs initialize the state and are excluded from the metrics.

| Model | Training correlation | Independent muscle correlation |
|---|---:|---:|
| Refit second-order ARX | 0.94180 | 0.93299 |
| ARX plus static residual network | 0.95811 | 0.94371 |
| Dynamic network, free-running feedback | 0.99377 | 0.92642 |
| Same dynamic network, one-step prediction with measured history | 0.99875 | 0.99890 |

### Recurrent training in Task C

The classic MATLAB solution connects the output layer back to the hidden
layer, gives both the output and input connections delays of one and two
samples, and trains the connected sequence for up to 50 epochs. The Python
fit minimizes the free-running output error over the entire training
trajectory. Each predicted force feeds the following two steps. A damped
Gauss–Newton update adjusts all 61 weights and biases of the ten-unit
network. The sensitivity recurrence differentiates both feedback paths.
A central-difference check exercises every parameter type, and a separate
nonlinear synthetic system tests prediction with a new input sequence.

With 50 epochs, the free-run training RMSEs for seeds 18, 19 and 20 are
0.03492, 0.03729 and 0.03605. Seed 18 wins on training data alone. The
static parallel network retains its 400-epoch budget. Passing `epochs`
sets the maximum for both fits. The CLI records the dynamic fitting method,
epoch budget, per-seed scores and selection.

One-step fitting is available with `dynamic_fit="one-step"`.
Using its default 400 epochs gives free-running correlations of 0.89965
and 0.88609. Recurrent training recovers the published rounded training value
of 0.99. The independent-muscle result of 0.92642 falls below the published 0.98.
A one-step score uses the preceding measured forces and has a different
interpretation from an uninterrupted simulation on the second muscle.

The original C18 definition calls for repeated dynamic-network training. The
reference solution distinguishes linear, parallel and dynamic model results.
The official catalog and the SNE index link the definition and solution
papers. No original training/validation data pair was found in those links.

- A. Belič, *Identification of Nonlinear Dynamics – Neural Networks versus Transfer Functions*, 2005. [Definition PDF](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf).
- A. Belič, *A Classic MATLAB-based Solution of ARGESIM Benchmark C18*, SNE 17(3–4), pp. 77–78. [Publication](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_17_34/sne.17.34.pdf).
- [ARGESIM catalog](https://www.argesim.org/benchmarks/c18) · [SNE definition and solutions](https://www.sne-journal.org/benchmarks/c18).

The archived publisher definition page from October 2006 links to the definition PDF. Its solutions page links to two example PDFs. The published Excel solution has no embedded workbook, data files or download links. These searches yielded no original measurement pair. [Archived definition](https://web.archive.org/web/20061009001632/http://www.argesim.org/comparisons/c18/definition/c18def.html) · [Archived solutions](https://web.archive.org/web/20061009003608/http://www.argesim.org/comparisons/c18/solutions/c18sol.html) · [Excel solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-solution-Excel.pdf)
