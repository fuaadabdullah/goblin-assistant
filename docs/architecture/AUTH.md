# Auth — Engine Pillar

## Purpose

The Auth pillar provides user authentication, session management, authorization, and request protection. It supports multiple authentication methods (email/password, Google OAuth, passkeys/WebAuthn), JWT-based sessions, CSRF protection, rate limiting, and security hardening through middleware.

---

## Architecture

```
Client Request
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│                    Middleware Layer                          │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Authentication   │  │  Security        │                 │
│  │ Middleware        │  │  Headers         │                 │
│  │ (JWT validation,  │  │  Middleware      │                 │
│  │  cookie/session) │  │  (CSP, HSTS,     │                 │
│  │                  │  │   XFO, XCTO)    │                 │
│  └────────┬─────────┘  └────────┬─────────┘                 │
│           │                     │                           │
│  ┌────────▼─────────────────────▼─────────┐                 │
│  │  CORS Middleware                       │                 │
│  │  (origin validation per environment)  │                 │
│  └────────────────┬───────────────────────┘                 │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│                    Auth Router                               │
│  /api/v1/auth/*                                             │
│                                                              │
│  ┌────────────┐ ┌──────────┐ ┌──────────────────┐          │
│  │ Login/     │ │ Passkey  │ │ Google OAuth     │          │
│  │ Register/  │ │ Challenge│ │ URL Generation   │          │
│  │ Logout     │ │ Register │ │ Callback Handler │          │
│  │ Validate   │ │ Auth     │ │                  │          │
│  └────────────┘ └──────────┘ └──────────────────┘          │
│                                                              │
│  ┌────────────┐ ┌──────────────────┐                        │
│  │ CSRF Token │ │ Password Reset   │                        │
│  │ Issue      │ │ (if implemented) │                        │
│  └────────────┘ └──────────────────┘                        │
└────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│                    Backend Services                          │
│                                                              │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────────┐      │
│  │ JWT        │ │ bcrypt       │ │ Supabase Auth    │      │
│  │ Sign/Verify│ │ Hash/Verify  │ │ (optional        │      │
│  │            │ │              │ │  integration)    │      │
│  └────────────┘ └──────────────┘ └──────────────────┘      │
│                                                              │
│  ┌────────────────────┐  ┌──────────────────────┐          │
│  │ Redis-backed       │  │ In-memory Fallback   │          │
│  │ CSRF Token Store   │  │ CSRF Token Store     │          │
│  └────────────────────┘  └──────────────────────┘          │
└────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Auth Router (`auth/router.py`)

The FastAPI router exposes all authentication endpoints under `/api/v1/auth/`.

| Endpoint | Method | Purpose | Rate Limited? |
|---|---|---|---|
| `/api/v1/auth/register` | POST | Create account with email/password | Yes (10/min/IP) |
| `/api/v1/auth/login` | POST | Authenticate with email/password | Yes (10/min/IP) |
| `/api/v1/auth/logout` | POST | Invalidate current session | No |
| `/api/v1/auth/validate` | GET | Validate JWT token validity | No |
| `/api/v1/auth/google/url` | GET | Generate Google OAuth authorization URL | No |
| `/api/v1/auth/google` | GET | Handle Google OAuth callback | No |
| `/api/v1/auth/google/callback` | GET | Process Google OAuth callback | No |
| `/api/v1/auth/passkey/challenge` | POST | Generate WebAuthn registration challenge | No |
| `/api/v1/auth/passkey/register` | POST | Register a new passkey | No |
| `/api/v1/auth/passkey/auth` | POST | Authenticate with a passkey | No |
| `/api/v1/auth/csrf/token` | GET | Issue a one-time CSRF token | No |

### 2. Authentication Methods

#### Email/Password

1. User submits `POST /api/v1/auth/register` with `{email, password}`
2. Password is hashed with bcrypt (via passlib)
3. User record is created in the database
4. JWT access token is generated and returned
5. HTTP-only cookie is set with the token

1. User submits `POST /api/v1/auth/login` with `{email, password}`
2. Password is verified against stored bcrypt hash
3. On success, JWT access token is generated and returned
4. HTTP-only cookie is set
5. On failure, `401 INVALID_CREDENTIALS` is returned

#### Google OAuth

1. Frontend requests `GET /api/v1/auth/google/url`
2. Backend generates and returns the Google OAuth authorization URL with `state` parameter
3. Frontend redirects the user to Google
4. User authorizes the application
5. Google redirects to `/api/v1/auth/google/callback` with `code` and `state`
6. Backend exchanges the code for tokens, validates `state`
7. User is looked up or created, JWT is generated
8. Browser is redirected to the frontend with the session

#### Passkey (WebAuthn)

1. Client requests `POST /api/v1/auth/passkey/challenge` to get a registration challenge
2. Client uses the challenge to create a credential via the WebAuthn browser API
3. Client sends the credential to `POST /api/v1/auth/passkey/register`
4. Backend stores the public key associated with the user
5. On subsequent login, client requests authentication challenge
6. Client signs the challenge using the private key
7. Backend verifies the signature against the stored public key
8. JWT is generated and returned

### 3. Token Management

**JWT Specification**:

| Claim | Type | Description |
|---|---|---|
| `sub` | string | User ID |
| `email` | string | User email address |
| `exp` | integer | Expiration timestamp (Unix epoch, 24h from issuance) |
| `iat` | integer | Issued at timestamp (Unix epoch) |
| `type` | string | Token type: `"access"` |

**Validation flow**:
1. Token is extracted from `Authorization: Bearer <token>` header or `token` cookie
2. JWT signature is verified using the server's secret key
3. Expiration `exp` is checked; if expired, `401 TOKEN_EXPIRED` is returned
4. User is looked up by `sub` claim
5. Token validation event is emitted

**Logout flow**:
1. Token is invalidated server-side (added to a denylist in Redis)
2. Cookie is cleared
3. `auth.user_logged_out` event is emitted

### 4. CSRF Protection

CSRF tokens protect state-changing operations (login, register, etc.) from cross-site request forgery attacks.

**Token lifecycle**:
1. Frontend requests `GET /api/v1/auth/csrf/token` before making a state-changing request
2. Backend generates a one-time token with an expiry (default 5 minutes)
3. Token is stored in Redis (key: `csrf:{token}`, value: expiry timestamp)
4. Frontend includes the token in the `X-CSRF-Token` header of state-changing requests
5. Backend validates the token exists and has not expired
6. Token is consumed (one-time use) and deleted from Redis

**Fallback**: If Redis is unavailable, CSRF tokens are stored in an in-memory dictionary. A warning is logged: "Redis unavailable for CSRF generation; using in-memory fallback".

### 5. Security Middleware

#### Authentication Middleware (`middleware.py`)

Validates JWT on every request, excluding public paths:

**Excluded paths** (no auth required):
```
/health, /health/all, /health/ready, /health/live
/auth/register, /auth/login, /auth/google/*, /auth/passkey/*
/auth/csrf/token
/docs, /openapi.json, /redoc
/metrics
/sandbox/* (uses API key instead)
```

**Behavior**:
- Missing or invalid token → `401 Unauthorized`
- Expired token → `401 TOKEN_EXPIRED`
- Valid token → request proceeds with `current_user` set in request state

#### Security Headers Middleware (`middleware.py`)

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS |
| `Content-Security-Policy` | Restricted per environment | Prevents XSS and data injection |

#### CORS Middleware

- Allowed origins are configured per environment
- Production restricts to the deploy domain(s)
- Non-production environments allow broader origins for development

Configuration via `security_config.py`:
```python
def build_allowed_origins(environment: str, raw_origins: str) -> List[str]:
    if environment == "production":
        return [raw_origins]  # Single production origin
    return [origin.strip() for origin in raw_origins.split(",")]
```

### 6. Rate Limiting

Rate limiting is applied to auth endpoints to prevent brute force attacks:

| Endpoint | Limit | Window | Scope |
|---|---|---|---|
| `/auth/login` | 10 attempts | 1 minute | Per IP address |
| `/auth/register` | 10 attempts | 1 minute | Per IP address |

Implemented via `optimizations.py`:
```python
@rate_limit(max_requests=10, window_seconds=60)
async def login(...):
    ...
```

When rate limit is exceeded, `429 RATE_LIMITED` is returned.

### 7. Security Configuration (`security_config.py`)

Central configuration for all security-related settings:

```python
class SecurityConfig:
    # Origins
    ALLOWED_ORIGINS: List[str] = []

    # CORS
    ALLOWED_HEADERS: List[str] = ["*"]
    ALLOW_CREDENTIALS: bool = True

    # Auth
    AUTH_COOKIE_SAMESITE: str = "lax"  # Production: "strict"
    AUTH_COOKIE_SECURE: bool = True     # Production only
    JWT_EXPIRY_HOURS: int = 24

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: int = 10
    REGISTER_RATE_LIMIT: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # CSRF
    CSRF_TOKEN_EXPIRY_SECONDS: int = 300    # 5 minutes
    CSRF_TOKEN_LENGTH: int = 64
```

---

## Auth Flow (Step by Step)

### Registration Flow

1. Client requests CSRF token via `GET /api/v1/auth/csrf/token`
2. Client sends `POST /api/v1/auth/register` with `{email, password}` and `X-CSRF-Token` header
3. Middleware validates CSRF token
4. Router validates email format and password strength
5. Password is hashed with bcrypt
6. Rate limiter checks IP (10/min)
7. User is created in the database
8. JWT is generated with `sub`, `email`, `exp=24h`, `iat`, `type=access`
9. HTTP-only cookie is set with the JWT
10. Response returns `{token, user: {id, email}}`
11. `auth.user_registered` event is emitted with `method=email`

### Login Flow

1. Client requests CSRF token via `GET /api/v1/auth/csrf/token`
2. Client sends `POST /api/v1/auth/login` with `{email, password}` and `X-CSRF-Token` header
3. Middleware validates CSRF token
4. Rate limiter checks IP (10/min)
5. Password is verified against stored bcrypt hash
6. On failure: `401 INVALID_CREDENTIALS`, `auth.rate_limit_hit` if threshold exceeded
7. On success: JWT is generated, HTTP-only cookie is set
8. Response returns `{token, user: {id, email}}`
9. `auth.user_logged_in` event is emitted with `method=email`

### Token Validation Flow (every authenticated request)

1. Request arrives at middleware
2. Path is checked against the exclude list
3. Token is extracted from `Authorization` header or `token` cookie
4. JWT signature is verified
5. Expiration is checked
6. If invalid: `401` response, `auth.token_validated` event with `valid=false`
7. If valid: `current_user` is set in request state, request proceeds
8. `auth.token_validated` event with `valid=true`

---

## Error Contract

| HTTP Status | Error Code | Condition | Recovery |
|---|---|---|---|
| 400 | `INVALID_EMAIL` | Email format is invalid | Provide a valid email address |
| 400 | `WEAK_PASSWORD` | Password does not meet strength requirements | Use a stronger password (min 8 chars, mixed case, numbers) |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password | Retry with correct credentials |
| 401 | `TOKEN_EXPIRED` | JWT has expired (24h) | Re-authenticate via login or refresh |
| 401 | `INVALID_TOKEN` | JWT malformed or invalid signature | Re-authenticate via login |
| 401 | `INVALID_CSRF` | CSRF token missing, expired, or consumed | Request a new CSRF token |
| 401 | `UNAUTHORIZED` | No token provided | Include token in Authorization header or cookie |
| 409 | `EMAIL_EXISTS` | Registration with existing email | Use a different email or login |
| 429 | `RATE_LIMITED` | Too many requests in the rate limit window | Wait and retry |

---

## Security Hardening Summary

| Layer | Control | Implementation |
|---|---|---|
| Transport | HTTPS enforcement | `Strict-Transport-Security` header, cloud TLS termination |
| Request | CORS | Environment-aware origin validation |
| Request | CSRF | One-time tokens, Redis-backed with in-memory fallback |
| Request | Rate limiting | Per-IP limiting for auth endpoints |
| Authentication | Password storage | bcrypt hashing (via passlib) |
| Authentication | JWT | Signed tokens with 24h expiry |
| Authentication | Session | HTTP-only cookies + Bearer header support |
| Authentication | Passkey | WebAuthn challenge/response with server-side public key storage |
| Response | Security headers | `XCTO`, `XFO`, `HSTS`, `CSP` |
| Monitoring | Audit logging | All auth events logged with user_id, method, result |

---

## Key Configuration

```python
# From environment / config
JWT_SECRET = os.getenv("JWT_SECRET")                         # JWT signing secret
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))   # Token TTL
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")              # Google OAuth client ID
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")      # Google OAuth client secret
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")         # Controls CORS, cookie security
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))
REGISTER_RATE_LIMIT = int(os.getenv("REGISTER_RATE_LIMIT", "10"))
```

---

## Events Emitted

| Event | Payload | Trigger |
|---|---|---|
| `auth.user_registered` | user_id, method (email/google/passkey) | Successful registration |
| `auth.user_logged_in` | user_id, method | Successful login |
| `auth.user_logged_out` | user_id | Successful logout |
| `auth.token_validated` | user_id, valid (bool), reason (if invalid) | Token validation attempt |
| `auth.csrf_issued` | user_id, expiry | CSRF token generation |
| `auth.rate_limit_hit` | identifier, endpoint, window | Rate limit threshold exceeded |

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_auth_contract.py`: Assert auth endpoint request/response shape
- `apps/api/src/api/tests/test_auth_security.py`: CSRF protection, rate limiting, passkey flow

### Integration Tests
- `tests/integration/engine/test_auth_registration.py`: Register, validate token, logout, verify token invalid
- `tests/integration/engine/test_auth_login_failure.py`: Attempt login with wrong password, verify rate limiting
- `tests/integration/engine/test_auth_google_oauth.py`: Mock Google OAuth, verify end-to-end flow
- `tests/integration/engine/test_auth_passkey.py`: Register passkey, authenticate with it, verify JWT issued

### Security Tests
- `tests/integration/engine/test_auth_csrf_replay.py`: Use same CSRF token twice, verify second request rejected
- `tests/integration/engine/test_auth_rate_limit_reset.py`: Hit rate limit, wait for window, verify request succeeds
- `tests/integration/engine/test_auth_token_expiry.py`: Use expired token, verify 401 with `TOKEN_EXPIRED`

### Performance Tests
- `tests/performance/test_auth_throughput.py`: Measure login endpoint throughput (target > 100 req/s per instance)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `apps/api/src/api/auth/router.py` — Auth route definitions
- `apps/api/src/api/middleware.py` — Authentication and security middleware
- `apps/api/src/api/security_config.py` — Security configuration
- `apps/api/src/api/core/csrf_manager.py` — CSRF token management
- `apps/api/src/api/optimizations.py` — Rate limiting decorator
- `apps/api/src/api/input_validation.py` — Input sanitization
- `apps/web/src/lib/api/auth.ts` — Frontend auth API client