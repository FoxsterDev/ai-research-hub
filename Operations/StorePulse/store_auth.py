"""Transport and credential layer for Store Pulse.

Standard library only, by design: the hosts that run this have no `requests`,
`google-auth` or `PyJWT`. Asymmetric signing is delegated to the `openssl` CLI,
which is present on macOS and Linux.

Nothing here reads a credential unless a caller asks for it, and no credential
value is ever returned, logged or included in an exception message.
"""

import base64
import email.utils
import gzip
import http.client
import json
import os
import stat
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
APPLE_AUDIENCE = "appstoreconnect-v1"
APPLE_TOKEN_TTL = 15 * 60

PLAY_SCOPES = (
    "https://www.googleapis.com/auth/playdeveloperreporting",
    "https://www.googleapis.com/auth/androidpublisher",
    "https://www.googleapis.com/auth/devstorage.read_only",
)


class AuthError(Exception):
    """A credential is missing, malformed, or refused by the provider."""


class HttpError(Exception):
    def __init__(self, status, url, detail=""):
        super().__init__(f"HTTP {status} for {url}{(': ' + detail) if detail else ''}")
        self.status = status
        self.url = url
        self.detail = detail


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _openssl(args, stdin_bytes):
    try:
        proc = subprocess.run(["openssl"] + args, input=stdin_bytes,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except FileNotFoundError:
        raise AuthError("openssl not found on PATH; it is required to sign provider JWTs")
    if proc.returncode != 0:
        raise AuthError(f"openssl {args[0]} failed (exit {proc.returncode})")
    return proc.stdout


def _sign_with_pem_file(key_path, payload):
    return _openssl(["dgst", "-sha256", "-sign", key_path], payload)


def _sign_with_pem_text(pem_text, payload):
    """Sign with an in-memory PEM by staging it 0600 in a private temp file."""
    fd, path = tempfile.mkstemp(prefix="storepulse-", suffix=".pem")
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w") as fh:
            fh.write(pem_text)
        return _sign_with_pem_file(path, payload)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def der_ecdsa_to_raw(der, size=32):
    """Convert an ECDSA DER signature to the raw r||s form JWS requires."""
    if len(der) < 8 or der[0] != 0x30:
        raise AuthError("unexpected ECDSA signature encoding")
    idx = 2
    if der[1] & 0x80:  # long-form length
        idx = 2 + (der[1] & 0x7F)
    out = b""
    for _ in range(2):
        if der[idx] != 0x02:
            raise AuthError("unexpected ECDSA signature encoding")
        length = der[idx + 1]
        val = der[idx + 2: idx + 2 + length].lstrip(b"\x00")
        if len(val) > size:
            raise AuthError("ECDSA signature component too large")
        out += val.rjust(size, b"\x00")
        idx += 2 + length
    return out


def _jwt(header, claims, signer):
    signing_input = (b64url(json.dumps(header, separators=(",", ":")).encode())
                     + "." + b64url(json.dumps(claims, separators=(",", ":")).encode()))
    return signing_input + "." + b64url(signer(signing_input.encode("ascii")))


class Transport:
    """Retrying JSON/bytes HTTP client with transparent gzip handling."""

    def __init__(self, timeout=90, retries=3, backoff=2.0, user_agent="store-pulse/1",
                 deadline=None):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.user_agent = user_agent
        self.deadline = deadline
        self.calls = 0
        self._lock = threading.Lock()

    def _timeout(self, requested=None):
        value = requested or self.timeout
        if self.deadline is None:
            return value
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise HttpError(0, url="run", detail="Store Pulse run deadline exceeded")
        return min(value, max(0.1, remaining))

    def _wait(self, delay):
        delay = min(30.0, max(0.0, delay))
        if self.deadline is not None and time.monotonic() + delay >= self.deadline:
            raise HttpError(0, "run", "Store Pulse run deadline exceeded during retry")
        time.sleep(delay)

    def raw(self, url, method="GET", body=None, headers=None, timeout=None, retry_safe=False):
        if self.retries < 1:
            raise AuthError("transport misconfigured: http_retries must be at least 1")
        hdrs = {"User-Agent": self.user_agent}
        hdrs.update(headers or {})
        last = None
        attempts = self.retries if method.upper() in ("GET", "HEAD") or retry_safe else 1
        for attempt in range(attempts):
            with self._lock:
                self.calls += 1
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self._timeout(timeout)) as resp:
                    payload = resp.read()
                    if payload[:2] == b"\x1f\x8b":
                        payload = gzip.decompress(payload)
                    return payload
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:400]
                except Exception:
                    pass
                last = HttpError(exc.code, url, detail)
                if exc.code in (408, 425, 429, 500, 502, 503, 504) and attempt < attempts - 1:
                    retry_after = None
                    raw_retry_after = ""
                    try:
                        raw_retry_after = exc.headers.get("Retry-After", "")
                        retry_after = float(raw_retry_after)
                    except (AttributeError, TypeError, ValueError):
                        try:
                            retry_after = max(0.0, email.utils.parsedate_to_datetime(
                                raw_retry_after).timestamp() - time.time())
                        except (TypeError, ValueError, OverflowError):
                            pass
                    self._wait(retry_after if retry_after is not None
                               else self.backoff * (attempt + 1))
                    continue
                raise last
            except urllib.error.URLError as exc:
                last = HttpError(0, url, str(exc.reason)[:200])
                if attempt < attempts - 1:
                    self._wait(self.backoff * (attempt + 1))
                    continue
                raise last
            except (TimeoutError, OSError, EOFError, http.client.HTTPException,
                    gzip.BadGzipFile) as exc:
                # a read timeout surfaces here, not as URLError; without this branch a slow
                # endpoint silently drops the slice instead of being retried
                last = HttpError(0, url, f"{type(exc).__name__}: {str(exc)[:160]}")
                if attempt < attempts - 1:
                    self._wait(self.backoff * (attempt + 1))
                    continue
                raise last
        raise last

    def json(self, url, method="GET", payload=None, headers=None, form=None, timeout=None,
             retry_safe=False):
        hdrs = {"Accept": "application/json"}
        hdrs.update(headers or {})
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            hdrs["Content-Type"] = "application/json"
        elif form is not None:
            body = urllib.parse.urlencode(form).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        raw = self.raw(url, method=method, body=body, headers=hdrs, timeout=timeout,
                       retry_safe=retry_safe)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


class GoogleAuth:
    """Service-account bearer tokens for the Play APIs and the reports bucket."""

    def __init__(self, key_path, transport, scopes=PLAY_SCOPES):
        self.key_path = key_path
        self.transport = transport
        self.scopes = list(scopes)
        self._token = None
        self._expires = 0
        self._email = None
        self._lock = threading.Lock()

    @property
    def client_email(self):
        if self._email is None:
            self._email = self._load().get("client_email", "")
        return self._email

    def _load(self):
        if not self.key_path or not os.path.exists(self.key_path):
            raise AuthError("google service-account key file not found at the configured path")
        try:
            with open(self.key_path) as fh:
                blob = json.load(fh)
        except (OSError, ValueError):
            raise AuthError("google service-account key file is not readable JSON")
        for field in ("client_email", "private_key"):
            if not blob.get(field):
                raise AuthError(f"google service-account key is missing '{field}'")
        return blob

    def token(self):
        with self._lock:
            return self._token_locked()

    def _token_locked(self):
        now = int(time.time())
        if self._token and now < self._expires - 60:
            return self._token
        blob = self._load()
        self._email = blob["client_email"]
        assertion = _jwt(
            {"alg": "RS256", "typ": "JWT"},
            {"iss": blob["client_email"], "scope": " ".join(self.scopes),
             "aud": blob.get("token_uri", GOOGLE_TOKEN_URL), "iat": now, "exp": now + 3600},
            lambda data: _sign_with_pem_text(blob["private_key"], data),
        )
        try:
            resp = self.transport.json(
                blob.get("token_uri", GOOGLE_TOKEN_URL), method="POST",
                form={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                      "assertion": assertion}, retry_safe=True)
        except HttpError as exc:
            raise AuthError(f"google token exchange refused the service account ({exc.status})")
        if not resp.get("access_token"):
            raise AuthError("google token exchange returned no access_token")
        self._token = resp["access_token"]
        self._expires = now + int(resp.get("expires_in", 3600))
        return self._token

    def headers(self):
        return {"Authorization": "Bearer " + self.token()}


class AppleAuth:
    """App Store Connect ES256 tokens from a .p8 private key."""

    def __init__(self, key_path, key_id, issuer_id):
        self.key_path = key_path
        self.key_id = key_id
        self.issuer_id = issuer_id
        self._token = None
        self._expires = 0
        self._lock = threading.Lock()

    def token(self):
        with self._lock:
            return self._token_locked()

    def _token_locked(self):
        now = int(time.time())
        if self._token and now < self._expires - 60:
            return self._token
        if not self.key_path or not os.path.exists(self.key_path):
            raise AuthError("apple .p8 key file not found at the configured path")
        if not self.key_id or not self.issuer_id:
            raise AuthError("apple key id / issuer id are not both configured")
        exp = now + APPLE_TOKEN_TTL
        self._token = _jwt(
            {"alg": "ES256", "kid": self.key_id, "typ": "JWT"},
            {"iss": self.issuer_id, "iat": now, "exp": exp, "aud": APPLE_AUDIENCE},
            lambda data: der_ecdsa_to_raw(_sign_with_pem_file(self.key_path, data)),
        )
        self._expires = exp
        return self._token

    def headers(self):
        return {"Authorization": "Bearer " + self.token()}
