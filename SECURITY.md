# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**⚠️ Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**security@infant-stack.dev**

Include as much of the following information as possible:

- Type of issue (buffer overflow, SQL injection, XSS, etc.)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Resolution Target:** Within 30 days for critical issues

## Security Controls

### Authentication & Authorization

- All API endpoints require authentication
- Role-based access control (RBAC) enforced
- JWT tokens with short expiration (15 minutes)
- Refresh token rotation

### Data Protection

- All data encrypted in transit (TLS 1.3)
- Sensitive data encrypted at rest (AES-256)
- PII anonymized in logs
- Database connections use SSL

### Infrastructure Security

- Containers run as non-root users
- Network policies restrict inter-service communication
- Secrets managed via Kubernetes secrets/Vault
- Regular security scanning (Trivy, Dependabot)

### Compliance

- SFDA regulatory compliance
- HIPAA-ready architecture
- Audit logging for all sensitive operations

## Security Headers

All HTTP responses include:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

## Dependency Management

- Dependencies reviewed before addition
- Automated vulnerability scanning via Dependabot
- Critical vulnerabilities patched within 24 hours
- Regular dependency updates (monthly)

## Acknowledgments

We appreciate responsible disclosure. Contributors who report valid security 
issues will be acknowledged (with permission) in our security hall of fame.
