from app.cache.redis_cache import AsyncRedisCache
from app.services.hitl_service import HITLService, get_hitl_service


def test_get_hitl_service_uses_shared_redis_client(
    monkeypatch,
) -> None:
    redis_client = object()
    monkeypatch.setattr(AsyncRedisCache(), "redis", redis_client)

    service = get_hitl_service()

    assert isinstance(service, HITLService)
    assert service.redis is redis_client
