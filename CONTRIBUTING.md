# Contributing to Infant-Stack

Thank you for your interest in contributing to Infant-Stack! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose v2.x
- Python 3.11+
- Node.js 20 LTS
- Git

### Local Setup

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/infant-stack.git
cd infant-stack

# Create a feature branch
git checkout -b feature/your-feature-name

# Start development environment
docker-compose up -d

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

---

## Development Workflow

### Branch Naming Convention

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/short-description` | `feature/add-alarm-dashboard` |
| Bug Fix | `fix/short-description` | `fix/mqtt-reconnection` |
| Docs | `docs/short-description` | `docs/api-documentation` |
| Refactor | `refactor/short-description` | `refactor/pairing-service` |

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```
feat(pairing): add infant-mother tag pairing endpoint
fix(gateway): resolve MQTT reconnection timeout
docs(readme): update quickstart instructions
```

---

## Pull Request Process

1. **Ensure all tests pass locally**
   ```bash
   # Backend tests
   cd backend && pytest -v
   
   # Frontend tests
   cd dashboards && npm test
   
   # Linting
   pre-commit run --all-files
   ```

2. **Update documentation** if your changes affect:
   - API endpoints
   - Configuration options
   - Database schema
   - User-facing features

3. **Fill out the PR template** completely

4. **Request review** from at least one maintainer

5. **Address feedback** promptly and push updates

### PR Checklist

- [ ] Tests added/updated for changes
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Commits squashed if needed
- [ ] PR description explains the "why"

---

## Code Style Guidelines

### Python (Backend)

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://github.com/psf/black) for formatting (line length: 88)
- Use [isort](https://github.com/PyCQA/isort) for import sorting
- Use type hints for function signatures
- Docstrings in [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

```python
def process_tag_event(tag_id: str, event_type: str) -> bool:
    """Process an incoming tag event.
    
    Args:
        tag_id: The unique identifier of the tag.
        event_type: Type of event (e.g., "proximity", "button_press").
        
    Returns:
        True if the event was processed successfully.
    """
    ...
```

### TypeScript (Frontend)

- Follow [ESLint](https://eslint.org/) rules in `.eslintrc`
- Use [Prettier](https://prettier.io/) for formatting
- Prefer functional components with hooks
- Use descriptive variable and function names

```typescript
interface TagStatusProps {
  tagId: string;
  status: 'active' | 'inactive' | 'alert';
}

const TagStatus: React.FC<TagStatusProps> = ({ tagId, status }) => {
  // Component implementation
};
```

---

## Testing Requirements

### Backend Tests

- Unit tests for all service functions
- Integration tests for API endpoints
- Minimum 80% code coverage

```bash
cd backend
pytest -v --cov=services --cov-report=html
```

### Frontend Tests

- Unit tests for components
- Integration tests for pages
- Accessibility tests

```bash
cd dashboards/nurse-dashboard
npm run test
npm run test:a11y
```

---

## Questions?

- Open a [GitHub Discussion](https://github.com/YOUR_ORG/infant-stack/discussions)
- Check existing [Issues](https://github.com/YOUR_ORG/infant-stack/issues)

Thank you for contributing! 🎉
