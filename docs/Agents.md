# Repository Guidelines for Codex

These instructions apply to every file in this repository.

- **Do not create new branches.** Work directly on the default branch.

## Development workflow

- Use **Python&nbsp;3.8+**.
- After editing a `.py` file, run `python -m py_compile` on that file to catch syntax errors.
- When adding major features or making broad changes, create new modules instead of heavily rewriting old ones. Summarize important updates in `changelog.md`.
- Update `DeepSOC架构文档.md` whenever the architecture changes.
- Keep `sample.env` synchronized with any `.env` modifications.
- Place tests in the `test` directory. Temporary or helper scripts belong in `tools` and should include brief usage instructions.

## Running the project

Initialize the database and start all services with:

```bash
python main.py -init          # first-time database setup
python tools/run_all_agents.py  # launch the web service and agent roles
```

See `README.md` for further details.
