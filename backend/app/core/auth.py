import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)

_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client() -> PyJWKClient:
    settings = get_settings()
    url = settings.clerk_jwks_url
    if url in _jwks_clients:
        return _jwks_clients[url]

    headers: dict[str, str] = {"User-Agent": "KnowledgeFlow-API/0.1.0"}
    if "api.clerk.com" in url and settings.clerk_secret_key:
        headers["Authorization"] = f"Bearer {settings.clerk_secret_key}"

    client = PyJWKClient(url, headers=headers)
    _jwks_clients[url] = client
    return client


def verify_clerk_token(token: str) -> str:
    """Return Clerk user id (JWT sub claim)."""
    settings = get_settings()
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "options": {"verify_aud": False},
        }
        if settings.clerk_jwt_issuer:
            decode_kwargs["issuer"] = settings.clerk_jwt_issuer

        payload = jwt.decode(token, signing_key.key, **decode_kwargs)
    except jwt.PyJWTError:
        # Retry without issuer check (Clerk iss formats vary by instance)
        try:
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False, "verify_iss": False},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user id",
        )
    return str(user_id)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    settings = get_settings()
    if settings.clerk_secret_key:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token",
            )
        return verify_clerk_token(credentials.credentials)

    # Local dev without Clerk — single shared user
    return "dev-user"
