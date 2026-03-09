# Contributing

Thanks for taking a look at this project. The goal here is to keep the codebase small, readable, and realistic for a single-person data science project. If you want to open an issue, suggest an improvement, or extend the analysis to another city, this is how to do it.

## Ways to contribute

- Fix a bug or edge case in the data pipeline or feature engineering
- Add a new notebook that explores a question the core project doesn’t answer yet
- Improve tests or add coverage for a part of the pipeline that isn’t currently checked
- Port the project to a different metro area with similar data sources

## How to get started

1. **Fork the repo**
   - Click “Fork” on GitHub and work from your own copy.

2. **Create a feature branch**
   ```bash
   git checkout -b my-feature-name
   ```

3. **Set up the environment**
   - Install Python 3.10+.
   - Install dependencies:
     ```bash
     py -m pip install -r requirements.txt
     ```
   - Copy the example env file and add your own API keys:
     ```bash
     cp .env.example .env
     ```

4. **Run the pipeline and tests locally**
   ```bash
   py src/data_pipeline.py
   py src/features.py
   py src/model.py
   py src/monitor.py

   py -m pytest tests/ -v
   ```

   Make sure all tests pass before you open a pull request.

## Code style

The project uses a straightforward, standard Python style:

- Prefer clear, explicit code over clever one-liners
- Keep functions small and focused
- Add docstrings where the intent isn’t obvious from the name
- Avoid introducing heavy new dependencies unless they clearly earn their keep

If you use type hints, keep them lightweight and consistent with existing code.

## Pull request guidelines

When you open a PR, please include:

- A short summary of what you changed and *why*
- Any new dependencies you added, and where they’re used
- Screenshots or notebook snippets if you changed visuals or analysis

Try to keep PRs focused on a single logical change. Smaller, targeted PRs are easier to review and less likely to introduce regressions.

## Extending to a new city

If you want to adapt this project to another metro area:

- Start by duplicating the repo to your own namespace
- Swap out the county FIPS codes and any metro-specific FRED series
- Update the README and notebooks to reflect the new geography

If you discover general improvements (better feature engineering, more robust drift checks, clearer visuals) while you’re doing that, feel free to open a PR back to this repo with those changes.
