import gmail_client


class TemporaryError(Exception):
    pass


class Request:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def execute(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise TemporaryError("temporary quota issue")
        return {"ok": True}


def test_execute_with_backoff_retries_retryable_error(monkeypatch):
    request = Request(failures=2)
    waits = []
    monkeypatch.setattr(gmail_client, "_is_retryable_google_error", lambda exc: True)
    result = gmail_client._execute_with_backoff(request, sleep=waits.append, retries=3)
    assert result == {"ok": True}
    assert request.calls == 3
    assert len(waits) == 2


def test_execute_with_backoff_does_not_retry_nonretryable_error(monkeypatch):
    request = Request(failures=1)
    waits = []
    monkeypatch.setattr(gmail_client, "_is_retryable_google_error", lambda exc: False)
    try:
        gmail_client._execute_with_backoff(request, sleep=waits.append, retries=3)
    except TemporaryError:
        pass
    else:
        raise AssertionError("Expected non-retryable error to be raised")
    assert request.calls == 1
    assert waits == []
