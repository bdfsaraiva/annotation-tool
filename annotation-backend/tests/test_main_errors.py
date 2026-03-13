import pytest

from app import main as app_main


class FakeSession:
    def __init__(self):
        self.closed = False

    def query(self, *args, **kwargs):
        class Q:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return None
        return Q()

    def add(self, *args, **kwargs):
        pass

    def commit(self):
        raise Exception("boom")

    def refresh(self, *args, **kwargs):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def test_create_first_admin_exception(monkeypatch):
    monkeypatch.setattr(app_main, "SessionLocal", lambda: FakeSession())
    with pytest.raises(Exception):
        app_main.create_first_admin()
