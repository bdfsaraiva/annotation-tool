from app.config import Settings


def test_dynamic_cors_origins_non_localhost():
    settings = Settings(
        SERVER_IP="10.0.0.5",
        FRONTEND_PORT="9999",
        CORS_ORIGINS=["http://example.com"]
    )
    origins = settings.dynamic_cors_origins
    assert "http://10.0.0.5:9999" in origins
    assert "http://example.com" in origins
