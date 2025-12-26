# Contributing Guide

We welcome contributions to Aivonx Proxy! Here's how to get started.

## Getting Started

1. **Fork the Repository**
   - Fork the project on GitHub
   - Clone your fork locally
   ```bash
   git clone https://github.com/YOUR_USERNAME/aivonx_proxy.git
   cd aivonx_proxy
   ```

2. **Set Up Development Environment**
   ```bash
   # Install dependencies
   uv sync
   
   # Run migrations
   uv run src/manage.py migrate
   
   # Create superuser
   uv run src/manage.py createsuperuser
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

Before submitting changes, ensure all tests pass:

```bash
# Run all tests
python src/manage.py test

# Run specific app tests
python src/manage.py test proxy

# Run with coverage
coverage run --source='.' src/manage.py test
coverage report
```

### Code Style

- Follow existing code style and conventions
- Use meaningful variable and function names
- Add docstrings to new functions and classes
- Keep functions focused and modular

### Making Changes

1. Make your changes in your feature branch
2. Write or update tests as needed
3. Update documentation if necessary
4. Run tests to ensure everything works
5. Commit with clear, descriptive messages

```bash
git add .
git commit -m "[Types] description of changes"
```

Types: `[update]`, `[fix]`, `[tests]`, `[docs]`

## Submitting a Pull Request

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template with:
     - Description of changes
     - Motivation and context
     - Related issue numbers
     - Testing performed

3. **PR Review Process**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

## Guidelines

### Code Quality

- Write clean, readable code
- Follow Django and Python best practices
- Avoid unnecessary complexity
- Keep commits atomic and focused

### Documentation

- Update relevant documentation
- Add docstrings to public APIs
- Update CHANGELOG if applicable
- Include examples for new features

### Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for good test coverage
- Test edge cases and error conditions

### Commit Messages

Follow conventional commit format:

```
- Description 1
- Description 2
- Description 3
```

## What to Contribute

### Good First Issues

- Documentation improvements
- Bug fixes
- Test coverage improvements
- Code comments and clarifications

### Feature Requests

- Open an issue first to discuss
- Get feedback before implementing
- Ensure it aligns with project goals

### Bug Reports

When reporting bugs, include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

## Code of Conduct

- Be respectful and professional
- Welcome newcomers
- Provide constructive feedback
- Focus on collaboration

## Questions?

If you have questions:
- Check existing documentation
- Search closed issues
- Open a new issue for discussion
- Join community discussions

Thank you for contributing!