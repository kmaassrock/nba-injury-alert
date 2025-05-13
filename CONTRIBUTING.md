# Contributing to NBA Injury Alert

Thank you for considering contributing to the NBA Injury Alert project! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/nba-injury-alert.git`
3. Set up the development environment:
   ```bash
   cd nba-injury-alert
   pip install -e ".[dev]"
   ```

## Development Environment

You can set up the development environment in two ways:

### Using Docker

The easiest way to get started is using Docker and Docker Compose:

```bash
make docker-build
make docker-up
```

This will start the API server, PostgreSQL database, and pgAdmin for database management.

### Local Development

1. Install dependencies:
   ```bash
   make install
   ```

2. Set up a PostgreSQL database and update the `.env` file with your database connection details.

3. Run database migrations:
   ```bash
   make migrate
   ```

4. Start the development server:
   ```bash
   make dev
   ```

## Project Structure

- `backend/`: Main package containing all the backend code
  - `api/`: FastAPI application and routers
  - `fetcher/`: Data retrieval components
  - `models/`: Database models
  - `notifier/`: Notification components
  - `processor/`: Data processing components
  - `utils/`: Utility modules
- `alembic/`: Database migrations
- `tests/`: Test suite
  - `unit/`: Unit tests
  - `integration/`: Integration tests

## Testing

Run the test suite:

```bash
make test
```

## Code Style

We use the following tools to maintain code quality:

- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

Format your code before submitting:

```bash
make format
```

Check for linting issues:

```bash
make lint
```

## Pull Request Process

1. Create a new branch for your feature or bugfix
2. Make your changes
3. Run tests and ensure they pass
4. Format your code
5. Submit a pull request

Please include a clear description of the changes and update any relevant documentation.

## Creating a New Feature

1. Check the issues and discussions to see if your feature has been discussed
2. Create a new issue to discuss the feature if it doesn't exist
3. Implement the feature in a new branch
4. Add tests for your feature
5. Update documentation as needed
6. Submit a pull request

## Reporting Bugs

When reporting bugs, please include:

- A clear and descriptive title
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Screenshots if applicable
- Environment details (OS, Python version, etc.)

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.
