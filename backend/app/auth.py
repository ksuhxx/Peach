import json
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionDep
from app.models import User


settings = get_settings()
bearer = HTTPBearer(auto_error=False)


async def current_user(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
) -> User:

    if not settings.auth_configured:
        if not settings.is_development:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not configured",
            )

        user = await session.scalar(
            select(User).where(User.cognito_sub == "local-dev-user")
        )

        if user is None:
            user = User(
                cognito_sub="local-dev-user",
                email="dev@localhost",
                name="Local Developer",
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)

        return user

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials

    try:
        if settings.cognito_jwks:
            jwks = json.loads(settings.cognito_jwks)

            jwk_client = PyJWKClient(
                settings.cognito_issuer + "/.well-known/jwks.json",
                cache_jwk_set=True,
            )

            jwk_client.jwk_set_cache.put(jwks)

        else:
            jwk_client = PyJWKClient(
                settings.cognito_issuer + "/.well-known/jwks.json"
            )

        signing_key = jwk_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.cognito_issuer,
        )

        if claims.get("token_use") != "id":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    cognito_sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name") or claims.get("given_name") or email

    if not cognito_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required claims",
        )

    user = await session.scalar(
        select(User).where(User.cognito_sub == cognito_sub)
    )

    if user is None:
        user = User(
            cognito_sub=cognito_sub,
            email=email,
            name=name,
        )

        session.add(user)
        await session.flush()
        await session.refresh(user)

    else:
        user.email = email
        user.name = name

    return user


CurrentUser = Annotated[User, Depends(current_user)]
