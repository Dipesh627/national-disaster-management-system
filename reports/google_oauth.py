"""
reports/google_oauth.py
=========================================================
NDMS -- GOOGLE OAUTH 2.0 / OIDC HELPER (STANDARD LIBRARY ONLY)
=========================================================
A hand-rolled Authorization Code + PKCE flow against Google's own,
real OAuth 2.0 / OpenID Connect endpoints -- not django-allauth.

Why not django-allauth (the master prompt's preferred choice):
this was implemented in a sandbox with no network access to install
new packages, and pulling in allauth's much larger app stack
(django.contrib.sites, allauth.account, allauth.socialaccount --
its own migrations, its own email-verification flow, its own
templates) would touch far more of this project than a single
"Continue with Google" button needs, on top of NDMS already having
its own hand-written login/register/session/"remember me"/password-
reset flow around a custom `reports.User` model. Everything below
talks directly to Google's documented endpoints over HTTPS and adds
ZERO new third-party dependencies -- only Python's standard
library. If a maintainer later wants django-allauth (e.g. to add
more social providers), this module plus the three views in
reports/views.py that use it (`google_login`, `google_callback`,
`google_signup_confirm`) are the only integration points to swap
out; nothing else in the project depends on this file.

Security properties implemented here:
  * `state`          -- CSRF protection on the OAuth redirect
  * PKCE (S256)       -- protects the authorization code in transit
  * `nonce`           -- binds the ID token to this exact browser
                          session, blocking token replay
  * ID token verified -- via Google's own tokeninfo endpoint, i.e.
                          Google itself checks the RS256 signature,
                          issuer, audience and expiry, server-to-
                          server over HTTPS. NDMS never trusts an
                          unverified token.
  * email_verified    -- a Google account CAN carry an unverified
                          email address; that is required before
                          NDMS treats the address as proof of
                          identity for account linking/creation.

For very high request volumes, Google recommends verifying the ID
token's signature locally against their published JWKS instead of
calling tokeninfo on every sign-in. Swap the implementation of
verify_id_token() if that becomes necessary -- every caller only
depends on the claims dict it returns.
=========================================================
"""

import base64
import hashlib
import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger('reports.google_oauth')


AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
TOKENINFO_ENDPOINT = 'https://oauth2.googleapis.com/tokeninfo'

# Minimum scopes needed to identify the person and greet them by
# name -- nothing else. No Drive/Gmail/Calendar/Contacts access is
# ever requested.
SCOPES = 'openid email profile'

# Google must respond promptly or the request fails cleanly instead
# of hanging.
REQUEST_TIMEOUT = 10


class GoogleOAuthError(Exception):
    """
    Raised for any problem in the Google OAuth exchange. `reason` is
    a short machine-readable code the view maps to a clean,
    user-facing message (reports/views.py -> GOOGLE_LOGIN_MESSAGES);
    the real detail is only ever written to the server log, never
    shown to the person signing in.
    """

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def is_configured():
    """
    True once real Client ID/Secret are set in the environment.
    google_login() uses this to show a clear, developer-facing
    configuration error instead of the button silently pretending
    to work (see master-prompt requirement: never fake Google
    auth when credentials are missing).
    """

    return bool(
        getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
        and getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
    )


def _new_code_verifier():
    # RFC 7636: 43-128 unreserved characters.
    return secrets.token_urlsafe(64)[:128]


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


def start_flow(redirect_uri):
    """
    Build everything one trip to Google's authorization endpoint
    needs. Returns (authorization_url, session_values). The caller
    (views.google_login) is responsible for storing session_values
    in request.session so the callback can verify them -- this
    function does not touch the session directly, so it is easy to
    unit test on its own.
    """

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = _new_code_verifier()

    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': SCOPES,
        'state': state,
        'nonce': nonce,
        'code_challenge': _code_challenge(code_verifier),
        'code_challenge_method': 'S256',
        'access_type': 'online',
        'prompt': 'select_account',
        'include_granted_scopes': 'true',
    }

    authorization_url = (
        f'{AUTHORIZATION_ENDPOINT}?{urllib.parse.urlencode(params)}'
    )

    session_values = {
        'state': state,
        'nonce': nonce,
        'code_verifier': code_verifier,
    }

    return authorization_url, session_values


def _post_form(url, data):

    body = urllib.parse.urlencode(data).encode('ascii')

    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT
        ) as response:
            return json.loads(response.read().decode('utf-8'))

    except urllib.error.HTTPError as exc:

        detail = exc.read().decode('utf-8', errors='replace')

        logger.warning(
            'Google OAuth token endpoint returned HTTP %s: %s',
            exc.code, detail,
        )

        raise GoogleOAuthError('token_exchange_failed') from exc

    except (urllib.error.URLError, TimeoutError) as exc:

        logger.warning('Google OAuth token endpoint unreachable: %s', exc)

        raise GoogleOAuthError('provider_unavailable') from exc

    except (ValueError, json.JSONDecodeError) as exc:

        logger.warning(
            'Google OAuth token endpoint returned invalid JSON: %s', exc
        )

        raise GoogleOAuthError('token_exchange_failed') from exc


def _get_json(url, params):

    full_url = f'{url}?{urllib.parse.urlencode(params)}'

    try:
        with urllib.request.urlopen(
            full_url, timeout=REQUEST_TIMEOUT
        ) as response:
            return json.loads(response.read().decode('utf-8'))

    except urllib.error.HTTPError as exc:

        detail = exc.read().decode('utf-8', errors='replace')

        logger.warning(
            'Google tokeninfo endpoint returned HTTP %s: %s',
            exc.code, detail,
        )

        raise GoogleOAuthError('invalid_token') from exc

    except (urllib.error.URLError, TimeoutError) as exc:

        logger.warning('Google tokeninfo endpoint unreachable: %s', exc)

        raise GoogleOAuthError('provider_unavailable') from exc

    except (ValueError, json.JSONDecodeError) as exc:

        logger.warning(
            'Google tokeninfo endpoint returned invalid JSON: %s', exc
        )

        raise GoogleOAuthError('invalid_token') from exc


def exchange_code(code, redirect_uri, code_verifier):
    """
    Authorization code -> tokens, at Google's real token endpoint.
    Raises GoogleOAuthError on any failure: expired/reused/invalid
    code, redirect URI mismatch, network issue, etc. NDMS's Client
    Secret is sent here, server-to-server, and nowhere else.
    """

    data = _post_form(TOKEN_ENDPOINT, {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'code': code,
        'code_verifier': code_verifier,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    })

    if 'id_token' not in data:

        logger.warning(
            'Google token endpoint response had no id_token (keys: %s)',
            list(data.keys()),
        )

        raise GoogleOAuthError('token_exchange_failed')

    return data


def verify_id_token(id_token, expected_nonce):
    """
    Verify the ID token by asking Google itself: the tokeninfo
    endpoint checks the RS256 signature, issuer and expiry
    server-side before returning the claims. NDMS additionally
    checks here that the token was issued for THIS Client ID
    (audience), carries the nonce THIS browser session generated
    (replay protection), and has a Google-verified email address.

    Returns the verified claims dict on success. Raises
    GoogleOAuthError('invalid_token' | 'email_not_verified' |
    'provider_unavailable') otherwise.
    """

    claims = _get_json(TOKENINFO_ENDPOINT, {'id_token': id_token})

    if claims.get('aud') != settings.GOOGLE_OAUTH_CLIENT_ID:

        logger.warning(
            'Google id_token audience mismatch: got %r', claims.get('aud')
        )

        raise GoogleOAuthError('invalid_token')

    if claims.get('iss') not in (
        'https://accounts.google.com', 'accounts.google.com'
    ):

        logger.warning(
            'Google id_token issuer mismatch: got %r', claims.get('iss')
        )

        raise GoogleOAuthError('invalid_token')

    if claims.get('nonce') != expected_nonce:

        logger.warning('Google id_token nonce did not match this session')

        raise GoogleOAuthError('invalid_token')

    if claims.get('email_verified') not in ('true', True):
        raise GoogleOAuthError('email_not_verified')

    if not claims.get('email'):
        raise GoogleOAuthError('invalid_token')

    if not claims.get('sub'):

        # `sub` is the stable Google identity identifier NDMS links
        # accounts by (see reports.models.User.google_sub) -- a
        # token without one cannot be used for account matching at
        # all, verified email or not.
        logger.warning('Google id_token had no sub claim')

        raise GoogleOAuthError('invalid_token')

    return claims