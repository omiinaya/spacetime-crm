def test_get_http_client():
    from client import get_http_client; c = get_http_client(); assert c is not None
def test_shared_client():
    from client import _shared_client; assert _shared_client is not None
