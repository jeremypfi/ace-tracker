# Contributing to ACE Tracker

Thanks for your interest in contributing! This is a personal project, but contributions are welcome.

## How to Contribute

### Reporting Bugs
1. Check if the bug has already been reported in [Issues](https://github.com/jeremypfi/ace-tracker/issues)
2. If not, create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Your Python version and OS

### Suggesting Features
1. Open an issue with the `enhancement` label
2. Describe the feature and why it would be useful
3. Include examples if possible

### Submitting Code
1. Fork the repository
2. Create a new branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `python3 test_ace_tracker.py`
5. Commit with clear message: `git commit -m "Add feature: description"`
6. Push to your fork: `git push origin feature-name`
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/ace-tracker.git
cd ace-tracker

# Install dependencies
pip3 install -r requirements.txt

# Run tests
python3 test_ace_tracker.py

# Run the tracker
python3 ace_tracker.py
```

## Code Style
- Follow PEP 8 Python style guidelines
- Add docstrings to new functions
- Keep functions focused and small
- Add tests for new features

## Testing
- All existing tests must pass
- Add new tests for new features
- Aim for high test coverage

## Pull Request Guidelines
- Keep PRs focused on a single feature/fix
- Update documentation if needed
- Add entry to CHANGELOG.md (if we create one)
- Be patient - this is a personal project!

## Questions?
Open an issue or reach out to [@jeremypfi](https://github.com/jeremypfi)

Thank you! 🌀
