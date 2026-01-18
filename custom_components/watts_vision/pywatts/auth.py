"""Authentication client for Watts Vision API.

Handles obtaining and refreshing OAuth tokens from the Watts Vision authentication server,
which are required for accessing the Watts Vision API (https://smarthome.wattselectronics.com/).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import TypedDict

import aiohttp

from .errors import WattsInvalidCredentialsError

# region Constants

WATTS_API_TOKEN_URL: str = "https://auth.smarthome.wattselectronics.com/realms/watts/protocol/openid-connect/token"
WATTS_GRANT_TYPE_PASSWORD: str = "password"
WATTS_GRANT_TYPE_REFRESH_TOKEN: str = "refresh_token"
WATTS_CLIENT_ID: str = "app-front"

# endregion

# region API Types


class WattsTokenResponse(TypedDict):
    """Response from the Watts OAuth token endpoint."""

    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    token_type: str
    not_before_policy: int
    session_state: str
    scope: str


class WattsTokenRequestPayload(TypedDict):
    """Payload for requesting a token from the Watts OAuth token endpoint."""

    grant_type: str
    username: str | None
    password: str | None
    refresh_token: str | None
    client_id: str


# endregion

# region Credentials and Authentication model


@dataclass
class WattsCredentials:
    """Credentials for Watts Vision API authentication."""

    username: str
    password: str


@dataclass
class WattsAuthentication:
    """Authentication tokens for Watts Vision API.

    Contains the information about the current session, including
    necessary tokens and their expiration times.
    """

    username: str
    access_token: str
    access_token_expiration_time: datetime
    refresh_token: str
    refresh_token_expiration_time: datetime

    def has_valid_token(self) -> bool:
        """Check if the access token is still valid."""
        return self.access_token and self.access_token_expiration_time > datetime.now()

    def can_refresh_token(self) -> bool:
        """Check if the refresh token is still valid."""
        return (
            self.refresh_token and self.refresh_token_expiration_time > datetime.now()
        )

    @staticmethod
    def from_token_response(
        username: str, token_response: WattsTokenResponse
    ) -> "WattsAuthentication":
        """Create a WattsAuthentication instance from a token response."""
        return WattsAuthentication(
            username=username,
            access_token=token_response["access_token"],
            access_token_expiration_time=datetime.now()
            + timedelta(seconds=token_response["expires_in"]),
            refresh_token=token_response["refresh_token"],
            refresh_token_expiration_time=datetime.now()
            + timedelta(seconds=token_response["refresh_expires_in"]),
        )


# endregion

_LOGGER = logging.getLogger(__name__)


class WattsAuthenticationClient:
    """Client for handling Watts Vision authentication."""

    def __init__(self, session: aiohttp.ClientSession, credentials: WattsCredentials):
        """Initialize the Watts Vision authentication client."""
        self.credentials: WattsCredentials = credentials
        self._session: aiohttp.ClientSession = session

    async def async_create_authentication(self) -> WattsAuthentication:
        """Create a new Watts Vision authentication by logging in with credentials.

        It uses the OAuth password grant to obtain access and refresh tokens, and
        returns a WattsAuthentication instance containing the tokens and their expiration times.
        """

        # Implementation of login logic to obtain tokens
        payload: WattsTokenRequestPayload = {
            "grant_type": WATTS_GRANT_TYPE_PASSWORD,
            "username": self.credentials.username,
            "password": self.credentials.password,
            "client_id": WATTS_CLIENT_ID,
        }

        _LOGGER.debug(
            "Logging in to get an access token from Watts OAuth server. Username: %s",
            self.credentials.username,
        )

        async with self._session.post(
            url=WATTS_API_TOKEN_URL, data=payload
        ) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Failed to authenticate with Watts Vision API: %s",
                    await response.text(),
                )
                raise WattsInvalidCredentialsError

            token_data: WattsTokenResponse = await response.json()

            return WattsAuthentication.from_token_response(
                self.credentials.username, token_data
            )

    async def async_refresh_authentication(
        self, authentication: WattsAuthentication
    ) -> WattsAuthentication:
        """Refresh the given Watts Vision authentication using the refresh token.

        It uses the OAuth refresh token grant to obtain new access and refresh tokens,
        and returns a new WattsAuthentication instance containing the updated tokens and their expiration times.
        """

        if not authentication.can_refresh_token():
            _LOGGER.error("Cannot refresh token: refresh token is invalid or expired.")
            raise WattsInvalidCredentialsError(
                "Expired refresh token cannot be used to refresh authentication."
            )

        payload: WattsTokenRequestPayload = {
            "grant_type": WATTS_GRANT_TYPE_REFRESH_TOKEN,
            "refresh_token": authentication.refresh_token,
            "client_id": WATTS_CLIENT_ID,
        }

        _LOGGER.debug("Refreshing access token using refresh token.")

        async with self._session.post(
            url=WATTS_API_TOKEN_URL, data=payload
        ) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Failed to refresh authentication with Watts Vision API: %s",
                    await response.text(),
                )
                raise WattsInvalidCredentialsError(
                    "Invalid refresh token cannot be used to refresh authentication."
                )

            token_data: WattsTokenResponse = await response.json()

            return WattsAuthentication.from_token_response(
                self.credentials.username, token_data
            )

    async def async_create_or_refresh_authentication(
        self, authentication: WattsAuthentication | None
    ) -> WattsAuthentication:
        """Create a new Watts Vision authentication or refresh the existing one.

        Basically ensures that a valid authentication is returned, either by
        creating a new one or refreshing the existing one if needed.
        """

        if authentication is None or not authentication.has_valid_token():
            if authentication and authentication.can_refresh_token():
                _LOGGER.debug("Refreshing existing authentication.")
                return await self.async_refresh_authentication(authentication)
            _LOGGER.debug("Creating new authentication.")
            return await self.async_create_authentication()

        _LOGGER.debug("Existing authentication is still valid.")
        return authentication
