import types
import sys
import pytest
from types import SimpleNamespace

# Inject a fake 'kubernetes' module before importing the webhook
fake_k8s = types.SimpleNamespace()


class FakeV1TokenReviewSpec:
    def __init__(self, token=None, audiences=None):
        self.token = token
        self.audiences = audiences


class FakeV1TokenReview:
    def __init__(self, spec=None):
        self.spec = spec


class FakeAuthApi:
    def __init__(
        self,
        authenticated: bool = True,
        username: str = "system:serviceaccount:ns:sa",
    ):
        self._authenticated = authenticated
        self._username = username

    def create_token_review(self, body):
        # body is unused in the fake implementation
        return types.SimpleNamespace(
            status=types.SimpleNamespace(
                authenticated=self._authenticated,
                user=types.SimpleNamespace(username=self._username),
            ),
        )


fake_client = SimpleNamespace(
    V1TokenReviewSpec=FakeV1TokenReviewSpec,
    V1TokenReview=FakeV1TokenReview,
    AuthenticationV1Api=lambda: FakeAuthApi(),
)

fake_config = SimpleNamespace(load_incluster_config=lambda: None)

fake_k8s.client = fake_client
fake_k8s.config = fake_config

sys.modules['kubernetes'] = fake_k8s
sys.modules['kubernetes.config'] = fake_k8s.config

# Now import the module under test
import api.attestation_webhook as webhook  # noqa: E402


@pytest.mark.asyncio
async def test_verify_service_account_token_success():
    # With the fake kubernetes module, TokenReview should return username
    username = webhook.verify_service_account_token('dummy-token')
    assert username == 'system:serviceaccount:ns:sa'


@pytest.mark.asyncio
async def test_rate_limiter_exceeded(monkeypatch):
    # Provide a fake service with a Redis-like client
    class FakeRedis:
        def __init__(self):
            self.store = {}

        def incr(self, k):
            v = int(self.store.get(k, 0)) + 1
            self.store[k] = v
            return v

        def expire(self, k, s):
            # no-op for test
            pass

    fake_service = SimpleNamespace(redis_client=FakeRedis())

    monkeypatch.setattr(
        webhook,
        'get_attestation_service',
        lambda: fake_service,
    )

    # Force verified identity to be a stable SA
    monkeypatch.setattr(
        webhook,
        'get_verified_identity',
        lambda req: 'system:serviceaccount:ns:sa',
    )

    # Create a fake request object
    fake_request = SimpleNamespace()
    fake_request.headers = {'Authorization': 'Bearer dummy'}
    fake_request.client = SimpleNamespace(host='1.2.3.4')
    fake_request.state = SimpleNamespace()

    # Decorate a simple async function
    async def handler(req):
        return 'ok'

    decorated = webhook.rate_limit(limit_per_min=1)(handler)

    # First call should succeed
    result = await decorated(fake_request)
    assert result == 'ok'

    # Second call within same minute should raise HTTPException (429)
    with pytest.raises(webhook.HTTPException) as exc:
        await decorated(fake_request)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_require_mtls_header_allows_and_denies(monkeypatch):
    async def handler(req):
        return 'ok'

    decorated = webhook.require_mtls(handler)

    # Allowed when header indicates success
    allowed_req = SimpleNamespace()
    allowed_req.headers = {'X-SSL-Client-Verify': 'SUCCESS'}
    allowed_req.url = SimpleNamespace(path='/validate')
    allowed_req.state = SimpleNamespace()
    allowed_req.client = None

    assert await decorated(allowed_req) == 'ok'

    # Denied when header missing
    denied_req = SimpleNamespace()
    denied_req.headers = {}
    denied_req.url = SimpleNamespace(path='/validate')
    denied_req.state = SimpleNamespace()
    denied_req.client = None

    with pytest.raises(webhook.HTTPException) as exc:
        await decorated(denied_req)
    assert exc.value.status_code == 403
