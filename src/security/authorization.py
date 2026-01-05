import os
from typing import Annotated

import cognitojwt
from fastapi import Header, Depends
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.queries.user import get_or_create_user


REGION = os.getenv('AWS_COGNITO_REGION')
USERPOOL_ID = os.getenv('AWS_COGNITO_USERPOOL_ID')
APP_CLIENT_ID = os.getenv('AWS_COGNITO_APP_CLIENT_ID')


async def get_aws_user(
    access_token: Annotated[str, Header(alias="Cognito-Authorization")],
    identification: Annotated[str | None, Header(alias="Cognito-ID")],
    db: AsyncSession = Depends(get_db),
):
    try:
        _: dict = await cognitojwt.decode_async(
            access_token, REGION, USERPOOL_ID, app_client_id=APP_CLIENT_ID, testmode=False,
        )
        identity_verification: dict = await cognitojwt.decode_async(
            identification, REGION, USERPOOL_ID, app_client_id=APP_CLIENT_ID, testmode=False,
        )

        user = await get_or_create_user(
            db, email=identity_verification['email'], username=identity_verification['cognito:username'])
        return user
    except cognitojwt.CognitoJWTException as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )
