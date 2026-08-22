# Microsoft Office Ingest Flake

Converts Microsoft Office files to plaintext `.md`, `.png` and `.csv` for use
with AI agents.

## Usage

```sh
nix run . -- ./documents -o ./out     # or: nix develop, then mso-ingest ...
```

Every input gets its own directory under the output root, so the layout does
not change shape depending on the input type:

```
out/
  manifest.json
  report/    report.md                       # docx
  deck/      deck.md  slides/slide-01.png    # pptx
  book/      sheets/Sales-Q1.csv             # xlsx
  scanned/   scanned.md                      # pdf
```

## Routing

| Input        | Output                                                    |
|--------------|-----------------------------------------------------------|
| `.docx`      | one markdown file, plus `media/` if images are embedded    |
| `.pptx`      | markdown with each slide's PNG linked inline under its heading |
| `.xlsx`      | one CSV per worksheet, in workbook order                   |
| `.pdf`       | one page-delimited markdown file, OCR'd where there is no text layer |
| `.doc` `.ppt`| upgraded by LibreOffice, then as above                     |
| `.xls`       | read directly, one CSV per worksheet                       |

Engines: pandoc for `.docx` (markitdown as fallback), markitdown for `.pptx`
text, LibreOffice + pdftoppm for slide rendering, csvkit for worksheets,
pdfminer + tesseract for PDFs.

## manifest.json

Written at the output root, describing every artifact produced:

```json
{
  "summary": { "documents": 5, "ok": 5, "partial": 0, "error": 0 },
  "documents": [
    {
      "source": "documents/book.xlsx",
      "kind": "xlsx",
      "status": "ok",
      "output_dir": "book",
      "sha256": "fae0fc51f714...",
      "artifacts": [
        {
          "path": "book/sheets/Sales-Q1.csv",
          "role": "csv",
          "bytes": 61,
          "meta": { "sheet": "Sales Q1", "index": 1, "rows": 3, "columns": 4 }
        }
      ],
      "warnings": []
    }
  ]
}
```

`status` is `ok`, `partial` (output exists but something was lost or guessed --
always accompanied by a warning) or `error`. The original sheet name is kept in
`meta` because the filename is sanitised. Exit status is 1 if any document
failed.

## Options

```
--dpi 150             resolution for rendered slides
--ocr / --no-ocr      OCR PDF pages with no text layer (default on)
--ocr-lang eng        tesseract language codes, e.g. 'eng+deu' (129 available)
--recursive           descend into directories (default on)
-q, --quiet           only report problems
```

## Notes

Some behaviour here is deliberate, and each of these was verified against the
tools rather than assumed:

* **csvkit type inference is disabled** (`-I`). With inference on, a column
  containing only `0`/`1` is coerced to boolean and `1` is written as `True`.
* **`in2csv --write-sheets` is not used.** It writes its output next to the
  *input* file, which would scribble into your source tree. Sheets are
  extracted one at a time with `--sheet` and redirected instead.
* **Slides are rendered via PDF.** `soffice --convert-to png` only ever emits
  the first slide of a deck.
* **File type comes from content, not just the extension.** A `.docx` that is
  really a PDF, or really a legacy OLE2 document, is routed correctly; a
  `.docx` that is not a zip container at all is reported as an error rather
  than having its raw bytes passed through as "text".
* **LibreOffice gets a throwaway profile per invocation**, since it serialises
  on a shared profile lock.
* LibreOffice is Linux-only in this flake; the nixpkgs Darwin build is a
  wrapper around a manual install. `.pptx` rendering and legacy `.doc`/`.ppt`
  support are therefore unavailable on macOS.
