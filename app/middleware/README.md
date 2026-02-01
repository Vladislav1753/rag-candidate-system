# 🔒 Rate Limiting

This document explains the rate limiting system implemented in the RAG Candidate System to protect API endpoints from abuse and ensure fair usage.

## Overview

Rate limiting restricts the number of requests a client can make to the API within a specified time window. This helps:

- **Prevent abuse:** Protects against DoS attacks and excessive API usage
- **Ensure fair usage:** Distributes resources fairly among all users
- **Control costs:** Limits expensive operations (LLM calls, embedding generation)
- **Maintain performance:** Prevents system overload

## Implementation

The system uses **SlowAPI**, a FastAPI extension that provides flexible rate limiting with support for:

- In-memory storage (default) or Redis for distributed systems
- IP-based throttling
- API key-based throttling (if `X-API-Key` header is provided)
- Custom error responses with retry information

## Configuration

Rate limits are configured via environment variables in the `.env` file:

```ini
# Format: "number/time_unit" where time_unit can be: second, minute, hour, day
RATE_LIMIT_SEARCH=20/hour       # Search endpoint limit
RATE_LIMIT_ONBOARDING=20/hour   # Candidate onboarding limit
RATE_LIMIT_EXTRACT=20/hour      # PDF extraction limit
RATE_LIMIT_DEFAULT=20/hour      # Default for all other endpoints

# Redis URL (optional) - if not set, uses in-memory storage
# REDIS_URL=redis://localhost:6379        # For local development
# REDIS_URL=redis://redis:6379            # For Docker environment
```

### Time Units

Supported time units:
- `second` - Per second rate limit
- `minute` - Per minute rate limit (recommended for most use cases)
- `hour` - Per hour rate limit
- `day` - Per day rate limit

### Examples

```ini
RATE_LIMIT_SEARCH=10/second     # 10 requests per second
RATE_LIMIT_SEARCH=100/minute    # 100 requests per minute
RATE_LIMIT_SEARCH=1000/hour     # 1000 requests per hour
RATE_LIMIT_SEARCH=10000/day     # 10000 requests per day
```

## Protected Endpoints

### POST `/search`
**Default:** 20 requests per hour

Search for candidates with semantic + keyword search and reranking.

### POST `/onboarding`
**Default:** 20 requests per hour

Onboard a new candidate (includes LLM summary generation and embedding).

### POST `/extract`
**Default:** 20 requests per hour

Extract structured data from PDF resume using AI workflow.

## How It Works

### 1. Client Identification

The system identifies clients by:
1. **API Key** (if `X-API-Key` header is present) - Recommended for production
2. **IP Address** (fallback) - Uses `X-Forwarded-For` header if available

### 2. Rate Limit Enforcement

When a request is received:
1. The client identifier is extracted
2. The request count is incremented for the current time window
3. If the limit is exceeded, a `429 Too Many Requests` response is returned
4. Otherwise, the request is processed normally

### 3. Error Response

When rate limit is exceeded, the API returns:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": "42"
}
```

**HTTP Status Code:** `429 Too Many Requests`
**Headers:** `Retry-After: 42` (seconds until rate limit resets)

## Usage Examples

### Using curl with IP-based limiting

```bash
# First request - OK
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python developer"}'

# ... after 20 requests in a minute ...

# 21st request - Rate limited
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python developer"}'
# Response: 429 Too Many Requests
```

### Using API Key-based limiting

```bash
# Add X-API-Key header for user-specific rate limiting
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: user_123_api_key" \
  -d '{"query": "Python developer"}'
```

### Python requests example

```python
import requests
import time

API_URL = "http://localhost:8000"
API_KEY = "user_123_api_key"  # Optional

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY  # Optional: for user-specific limits
}

for i in range(25):
    response = requests.post(
        f"{API_URL}/search",
        json={"query": "Python developer"},
        headers=headers
    )

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"Rate limited! Retrying after {retry_after} seconds...")
        time.sleep(retry_after)
        # Retry the request
    elif response.status_code == 200:
        print(f"Request {i+1}: Success")
    else:
        print(f"Request {i+1}: Error {response.status_code}")
```

## Scaling with Redis

The system automatically uses Redis for distributed rate limiting when the `REDIS_URL` environment variable is set. This is essential for production deployments with multiple backend instances.

### Configuration

**Option 1: Docker (Recommended)**

Redis is already configured in `docker-compose.yml`. Simply run:

```bash
docker-compose up -d
```

The backend service will automatically connect to Redis using `REDIS_URL=redis://redis:6379`.

**Option 2: Local Development with External Redis**

1. Start Redis locally:
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. Add to your `.env` file:
   ```ini
   REDIS_URL=redis://localhost:6379
   ```

3. Install redis dependency:
   ```bash
   pip install redis>=5.0.0
   ```

**Option 3: In-Memory (Development Only)**

Simply omit the `REDIS_URL` environment variable, and the system will use in-memory storage:

```ini
# .env file - no REDIS_URL specified
RATE_LIMIT_SEARCH=20/hour
RATE_LIMIT_ONBOARDING=20/hour
```

**Note:** In-memory storage does NOT work across multiple backend instances. Use Redis for production.

## Monitoring

To monitor rate limiting in production:

1. **Check logs** for rate limit warnings:
   ```
   WARNING: Rate limit exceeded for 192.168.1.100 on /search
   ```

2. **Track metrics** (if using Prometheus):
   - `http_requests_total{status="429"}` - Count of rate limited requests
   - `http_request_duration_seconds` - Request latency

3. **Analyze patterns** to adjust limits:
   - Too many 429 errors? Increase limits
   - Abuse detected? Decrease limits for specific IPs/keys

## Best Practices

1. **Set appropriate limits** based on:
   - Expected usage patterns
   - Backend capacity
   - Cost of operations (LLM calls are expensive)

2. **Use API keys** in production:
   - Allows per-user rate limiting
   - Better tracking and analytics
   - Easier to whitelist trusted clients

3. **Implement exponential backoff** in clients:
   - Respect `Retry-After` header
   - Don't hammer the API when rate limited

4. **Monitor and adjust** limits:
   - Start conservative
   - Analyze usage patterns
   - Adjust based on real data

## Troubleshooting

### Issue: Getting rate limited too quickly

**Solution:** Increase the limit in `.env`:
```ini
RATE_LIMIT_SEARCH=50/hour  # Increased from 20
```

### Issue: Rate limiting not working

**Check:**
1. Environment variables are loaded correctly
2. `slowapi` is installed: `pip install slowapi`
3. Middleware is added to FastAPI app
4. Endpoints have `@limiter.limit()` decorator

### Issue: Different limits for different users

**Solution:** Use API key-based limiting:
```python
# Client sends X-API-Key header
# You can implement custom logic to set different limits per API key
```

## Security Considerations

1. **Rate limiting is not authentication** - It only limits request frequency
2. **Use HTTPS** in production to protect API keys
3. **Combine with other security measures**:
   - Authentication/Authorization
   - Input validation
   - CORS configuration
4. **Monitor for abuse patterns** even with rate limiting enabled

## References

- [SlowAPI Documentation](https://github.com/laurentS/slowapi)
- [FastAPI Middleware Guide](https://fastapi.tiangolo.com/tutorial/middleware/)
- [HTTP Status Code 429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
