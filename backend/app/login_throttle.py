"""Bounded, process-local login attempt budget for the single-process demo."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


class LoginThrottle:
    def __init__(self, limit=10, window_seconds=300, max_clients=4096, clock=monotonic):
        self.limit = limit
        self.window = window_seconds
        self.max_clients = max_clients
        self.clock = clock
        self.clients = OrderedDict()
        self.lock = Lock()

    def check(self, address: str) -> None:
        # Reserve a slot BEFORE password hashing, including concurrent attempts.
        with self.lock:
            now = self.clock()
            attempts = self.clients.pop(address, deque())
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            self.clients[address] = attempts
            if len(attempts) >= self.limit:
                retry = max(1, int(attempts[0] + self.window - now) + 1)
                raise HTTPException(429, "Too many login attempts. Try again later.",
                                    headers={"Retry-After": str(retry)})
            attempts.append(now)
            while len(self.clients) > self.max_clients:
                self.clients.popitem(last=False)


login_throttle = LoginThrottle()


def limit_login(request: Request) -> None:
    # Never parse user-supplied forwarding headers here. Configure trusted
    # reverse proxies explicitly in Uvicorn when deploying behind one.
    login_throttle.check(request.client.host if request.client else "unknown")
