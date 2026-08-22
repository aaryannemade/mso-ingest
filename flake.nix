{
  description = "mso-ingest: intelligently convert Microsoft Office files to agent-friendly formats (md/html/csv/png)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      forAllSystems =
        f:
        nixpkgs.lib.genAttrs systems (
          system:
          f {
            inherit system;
            pkgs = nixpkgs.legacyPackages.${system};
          }
        );

      # Python interpreter + libraries. markitdown is the primary driver; the
      # per-format libraries are listed explicitly so conversion logic can fall
      # back to them when markitdown's generic output is not good enough
      # (e.g. reading cell formulas, extracting embedded images).
      pythonFor =
        pkgs:
        pkgs.python3.withPackages (ps: [
          ps.markitdown # docx/pptx/xlsx/pdf -> markdown
          ps.python-docx # .docx structure access
          ps.python-pptx # .pptx structure access
          ps.openpyxl # .xlsx read/write
          ps.xlrd # legacy .xls
          ps.pandas # tabular normalisation -> csv/markdown
          ps.tabulate # dataframe -> markdown tables
          ps.pdfminer-six # pdf text extraction
          ps.pdf2image # pdf -> PIL images (needs poppler)
          ps.pillow # image handling / png output
          ps.beautifulsoup4 # html post-processing
          ps.lxml
          ps.markdownify # html -> markdown
          ps.magika # content-based file type detection
          ps.puremagic
          ps.rich # CLI output
          ps.typer # CLI framework
        ]);

      # External CLI tools invoked by the converter.
      toolsFor =
        pkgs:
        [
          pkgs.pandoc # universal document converter
          pkgs.csvkit # in2csv / csvlook / csvjson
          pkgs.poppler-utils # pdftoppm, pdftotext
          pkgs.imagemagick # png post-processing
        ]
        ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [
          # LibreOffice is the only reliable way to render Office documents to
          # PDF/PNG with layout preserved. Linux-only here: the Darwin build in
          # nixpkgs is a wrapper around a manual install.
          pkgs.libreoffice
        ];

      devTools = pkgs: [
        pkgs.ruff
        pkgs.uv
        pkgs.nixfmt-tree
      ];
    in
    {
      devShells = forAllSystems (
        { pkgs, ... }:
        let
          python = pythonFor pkgs;
          tools = toolsFor pkgs;
        in
        {
          default = pkgs.mkShell {
            name = "mso-ingest";

            packages = [ python ] ++ tools ++ devTools pkgs;

            shellHook = ''
              export MSO_INGEST_ROOT="$PWD"
              # Keep LibreOffice's profile inside the project so batch
              # conversion never touches the user's real ~/.config.
              export LIBREOFFICE_USER_PROFILE="$PWD/.cache/libreoffice"
              mkdir -p "$LIBREOFFICE_USER_PROFILE"

              echo "mso-ingest dev shell"
              echo "  python     $(python3 --version 2>&1 | cut -d' ' -f2)"
              echo "  markitdown $(markitdown --version 2>/dev/null || echo 'n/a')"
              echo "  pandoc     $(pandoc --version | head -n1 | cut -d' ' -f2)"
              echo "  csvkit     $(in2csv --version 2>&1 | cut -d' ' -f2)"
              ${pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isLinux ''
                echo "  soffice    $(soffice --version 2>/dev/null | cut -d' ' -f2 || echo 'n/a')"
              ''}
            '';
          };
        }
      );

      formatter = forAllSystems ({ pkgs, ... }: pkgs.nixfmt-tree);
    };
}
