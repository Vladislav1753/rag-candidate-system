"""
Test script to verify rate limiting with Redis.
"""

import time

import requests

from app.core.config import settings


def test_rate_limiting(endpoint: str = "/search", max_requests: int = 25) -> None:
    """
    Test rate limiting by sending multiple requests.

    Args:
        endpoint: API endpoint to test
        max_requests: Number of requests to send
    """
    print(f"\n{'=' * 60}")
    print(f"Testing Rate Limiting on {endpoint}")
    print(f"{'=' * 60}\n")

    success_count = 0
    rate_limited_count = 0

    for i in range(max_requests):
        try:
            response = requests.post(
                f"{settings.app.api_url}{endpoint}",
                json={"query": "Python developer"},
                timeout=5,
            )

            if response.status_code == 200:
                success_count += 1
                print(f"✅ Request {i + 1:2d}: Success (200 OK)")
            elif response.status_code == 429:
                rate_limited_count += 1
                retry_after = response.headers.get("Retry-After", "N/A")
                print(
                    f"🚫 Request {i + 1:2d}: Rate Limited (429) - Retry after {retry_after}s"
                )

                # Show response body
                try:
                    data = response.json()
                    print(f"   Message: {data.get('message', 'N/A')}")
                except ValueError:
                    pass
            else:
                print(f"❌ Request {i + 1:2d}: Error {response.status_code}")

        except Exception as e:
            print(f"❌ Request {i + 1:2d}: Exception - {e}")

        # Small delay between requests
        time.sleep(0.1)

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  ✅ Successful requests: {success_count}")
    print(f"  🚫 Rate limited requests: {rate_limited_count}")
    print(f"  📊 Total requests: {max_requests}")
    print(f"{'=' * 60}\n")


def test_with_api_key(api_key: str = "test_user_123") -> None:
    """
    Test rate limiting with API key.
    """
    print(f"\n{'=' * 60}")
    print(f"Testing Rate Limiting with API Key: {api_key}")
    print(f"{'=' * 60}\n")

    headers = {"X-API-Key": api_key}

    for i in range(5):
        try:
            response = requests.post(
                f"{settings.app.api_url}/search",
                json={"query": "Python developer"},
                headers=headers,
                timeout=5,
            )

            print(f"Request {i + 1}: Status {response.status_code}")

        except Exception as e:
            print(f"Request {i + 1}: Exception - {e}")

        time.sleep(0.1)


if __name__ == "__main__":
    print("\n🚀 Starting Rate Limiting Tests\n")

    test_rate_limiting(endpoint="/search", max_requests=25)

    print("\n⏳ Waiting 5 seconds before next test...\n")
    time.sleep(5)

    test_with_api_key(api_key="test_user_123")

    print("\n✅ All tests completed!\n")
