# Installation Instructions

## Local Installation

### Using pip (Editable Mode)

For development purposes, install the package in editable mode:

```bash
pip install -e .
```

This allows you to make changes to the code and have them reflected immediately without reinstalling.

### Using pipx (Recommended for CLI Tools)

pipx installs Python packages in isolated environments, making them ideal for CLI tools:

```bash
# Install pipx if not already installed
pip install pipx

# Install gitaut
pipx install .
```

After installation, you can run `gitaut` from any directory:

```bash
gitaut --help
gitaut --verbose
```

### Installing from Git Repository

```bash
pipx install git+https://github.com/Pro100kir2/GitAut.git
```

or with pip:

```bash
pip install git+https://github.com/Pro100kir2/GitAut.git
```

## Traditional Usage (Backward Compatibility)

The traditional way of running the script still works:

```bash
python main.py
python main.py --verbose
python main.py --help
```

## Development Installation

For development, install the package with optional development dependencies:

```bash
pip install -e ".[dev]"
```

This will install additional tools like:
- ruff (linter)
- black (code formatter)
- isort (import sorter)
- pytest (testing framework)

## System Requirements

- Python 3.8 or higher
- Git
- GitHub CLI (gh) - required for PR operations
- Operating System: Linux, macOS, or Windows

## Dependencies

Core dependencies:
- pyyaml

Development dependencies (optional):
- ruff>=0.1.0
- black>=23.0.0
- isort>=5.12.0
- pytest>=7.0.0

## Verification

After installation, verify that the command works:

```bash
gitaut --help
```

You should see the help output with all available options.

## Uninstallation

### Using pip

```bash
pip uninstall gitaut
```

### Using pipx

```bash
pipx uninstall gitaut
```

## Publishing to PyPI

### Prerequisites

1. Create an account on [PyPI](https://pypi.org/)
2. Create an API token at https://pypi.org/manage/account/token/
3. Install build and twine packages:

```bash
pip install build twine
```

### Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/

# Build the package
python -m build
```

This will create a `dist/` directory with the built package.

### Test the Package Locally

Before publishing, test the package locally:

```bash
# Install from the built package
pip install dist/gitaut-1.0.0-py3-none-any.whl

# Test the command
gitaut --help

# Uninstall
pip uninstall gitaut
```

### Upload to PyPI

#### Upload to TestPyPI (Recommended First)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ gitaut

# Test
gitaut --help

# Uninstall
pip uninstall gitaut
```

#### Upload to Production PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*
```

### Install from PyPI

After publishing, users can install the package:

```bash
pip install gitaut
```

or with pipx:

```bash
pipx install gitaut
```

## Version Management

To release a new version:

1. Update the version in `pyproject.toml`:

```toml
[project]
version = "1.0.1"  # Increment version
```

2. Build and upload the new version:

```bash
python -m build
python -m twine upload dist/*
```

## Troubleshooting

### Command Not Found

If `gitaut` command is not found after installation:

- Check that the installation directory is in your PATH
- For pipx: `pipx ensurepath` to add pipx directories to PATH
- For pip: Check the location where pip installs scripts and add it to PATH

### Import Errors

If you encounter import errors when running `python main.py`:

- Ensure you're in the project root directory
- Try installing in editable mode: `pip install -e .`
- Check that all dependencies are installed

### Permission Errors

If you encounter permission errors during installation:

- Use a virtual environment
- Or use `--user` flag: `pip install --user gitaut`
