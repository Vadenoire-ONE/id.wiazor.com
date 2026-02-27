# id.wiazor.com — Identity Service

Authentication & Organization management service for the DTKT Platform.

## Overview

**id.wiazor.com** handles:

- User registration & authentication (JWT: HS256 / RS256)
- Organization CRUD & user-org membership
- RBAC with 7 identity-scoped permissions
- NATS events: `identity.user.registered`, `identity.org.created/updated`
- JWKS endpoint for public key distribution

## Quick Start

```bash
# Install as a library (monolith mode)
pip install -e .

# Run as standalone microservice
uvicorn identity.main:app --host 0.0.0.0 --port 8200

# Docker
docker build -t wiazor-identity .
docker run -p 8200:8200 wiazor-identity
```

## Configuration

Environment variables (see `identity/config.py` → `IdentitySettings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `IDENTITY_DB_URL` | `postgresql://...` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | — | HMAC shared secret (HS256) |
| `JWT_PRIVATE_KEY_PATH` | — | RSA/EC private key (RS256/ES256) |
| `JWT_PUBLIC_KEY_PATH` | — | RSA/EC public key |
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

## Package

```toml
# In consumer's pyproject.toml
[project.optional-dependencies]
monolith = ["wiazor-identity>=1.0,<2.0"]
```

## API

- `POST /api/v1/auth/register` — register user
- `POST /api/v1/auth/login` — login → JWT
- `POST /api/v1/auth/token/refresh` — refresh token
- `GET  /api/v1/auth/me` — current user
- `GET  /api/v1/organizations/` — list organizations
- `POST /api/v1/organizations/` — create organization
- `GET  /api/v1/internal/users/{id}` — internal: get user
- `GET  /api/v1/internal/orgs/{id}` — internal: get organization
- `GET  /.well-known/jwks.json` — JWKS public keys
- `GET  /api/v1/health` — health check

## License

MIT
