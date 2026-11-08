"""Local candidate A-only perimeter; not a deployment launcher or a website proxy."""
from dataclasses import dataclass
import re
from urllib.parse import parse_qsl

from backend.mini_api import ACCOUNT_PREFIX as A, PREFIX as G, MiniGateway, error_response
from backend.mini_auth import MiniError

REGISTRATION_ACTIONS = frozenset({'register', 'verify-email', 'resend-verification'})


@dataclass(frozen=True)
class AccountBoundaryOptions:
    enabled: bool = False
    cloud_writes: bool = False
    registration: bool = False

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.cloud_writes) is not bool:
            raise ValueError('Account switches must be explicit booleans')
        if self.cloud_writes and not self.enabled:
            raise ValueError('Cloud writes require an enabled account component')
        if type(self.registration) is not bool or (self.registration and (not self.enabled or self.cloud_writes)):
            raise ValueError('Registration acceptance requires an enabled read-only account service')


class AccountBoundary:
    """The factory must return the existing MiniGateway with account_a_only=True.

    Disabled construction never calls the factory, opens state or initializes API.
    The gateway owns exact Host, trusted proxy/IP, authentication and rate limits.
    Use a separate same-database website app, never forward website paths here.
    """
    def __init__(self, factory, options=None):
        self.options = options or AccountBoundaryOptions()
        self.app = factory() if self.options.enabled else None
        if self.app is not None and (not isinstance(self.app, MiniGateway) or self.app.account is None
                                    or self.app.account.state.native_a_only is not True):
            raise ValueError('A-only boundary requires the existing account gateway with account_a_only=True')

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                event = await receive()
                if event['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif event['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        if scope['type'] == 'websocket':
            return await send({'type': 'websocket.close', 'code': 1008})
        headers = {k.lower(): v for k, v in scope.get('headers', [])}
        method, path = scope['method'], scope['path']
        error = None
        if self.app is None:
            error = MiniError(404, 'NATIVE_DISABLED', 'Account preparation is disabled')
        elif b'cookie' in headers or b'origin' in headers or method == 'OPTIONS':
            error = MiniError(403, 'NATIVE_ONLY', 'Native requests require independent Bearer authentication')
        else:
            allowed = (method, path) in {
                ('POST', G+'/session'), ('GET', G+'/snapshot'),
                ('GET', A+'/session'), ('DELETE', A+'/session'),
                ('POST', A+'/auth/login'), ('POST', A+'/auth/reauth'),
                ('GET', A+'/profile'), ('PUT', A+'/profile')}
            if self.options.registration and method == 'POST':
                allowed = allowed or path in {A+'/auth/'+action for action in REGISTRATION_ACTIONS}
            if method == 'GET' and re.fullmatch(re.escape(A)+r'/operations/[A-Za-z0-9_-]{16,80}', path):
                pairs = parse_qsl(scope.get('query_string', b'').decode('latin1'), keep_blank_values=True)
                query = dict(pairs)
                allowed = (pairs in [[('action', 'login')], [('action', 'reauth')]] or
                           len(pairs) == 2 and set(query) == {'action', 'server'} and
                           query['action'] == 'profile-save' and query['server'] in ('cn', 'global'))
                if self.options.registration and len(pairs) == 1 and pairs[0][0] == 'action':
                    allowed = allowed or pairs[0][1] in REGISTRATION_ACTIONS
            if not allowed:
                error = MiniError(404, 'ACCOUNT_ROUTE_PENDING', 'Route is outside this A preparation scope')
            elif method == 'PUT' and not self.options.cloud_writes:
                error = MiniError(503, 'ACCOUNT_CLOUD_WRITE_DISABLED', 'Explicit cloud-write acceptance is not enabled')
        if error is None:
            return await self.app(scope, receive, send)
        response = error_response(error)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'no-referrer'})
        return await response(scope, receive, send)
