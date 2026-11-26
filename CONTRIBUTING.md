# Contributing

Thanks for helping improve Archive2MD. This guide describes a small, repeatable workflow for changes to the CLI, archive intake, converters, OCR services, and Markdown output.

## Development environment

- Windows 10/11 is the primary supported environment.
- Python 3.10 or newer is required.
- For a first-time Windows setup, start with the repository's `setup.bat` as described in [README.md](README.md).
- For a manual environment, create a virtual environment and install the project requirements:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Follow the README's model and CUDA setup instructions when working on the local Vision OCR backend. Do not download model weights just to change documentation or unrelated CLI code.

## Where changes belong

Trace the existing flow before changing behavior:

`cli.py → core/ → services/`

- Keep archive discovery and recursive intake in `core/`.
- Keep format classification and conversion orchestration separate from individual converter integrations.
- Put backend-specific setup and resource handling in `services/`.
- Preserve the existing CLI options and output modes unless a change explicitly updates the documentation and user-facing behavior together.

## Validation before opening a pull request

Run the inexpensive checks first:

```powershell
.venv\Scripts\python.exe -m compileall -q cli.py core services
.venv\Scripts\python.exe cli.py --help
```

For changes to runtime behavior, also run a small representative input through the affected path. Archive-intake changes should cover at least one ordinary archive and, when relevant, a nested archive. Conversion or OCR changes should verify the resulting Markdown and report the selected backend accurately.

The repository does not currently declare a single automated test command in `pyproject.toml`; do not report an unrun test suite as passing.

## Repository hygiene and privacy

- Do not commit `.env`, API keys, access tokens, personal documents, or real user archives.
- Keep virtual environments, downloaded model weights, generated output, and temporary cache data out of commits.
- Use small synthetic fixtures for reproducible examples.
- Do not add prompts, document contents, tensor dumps, or other private user data to logs.
- Keep generated artifacts in the project's intended local directories and avoid writing into unrelated user folders.

## Pull request checklist

- [ ] Explain the user-visible behavior or bug being changed.
- [ ] Keep the change focused and update README/docs when behavior or CLI options change.
- [ ] Run the applicable validation commands and include the actual results.
- [ ] Confirm no credentials, private documents, model weights, cache, or generated output are included.
