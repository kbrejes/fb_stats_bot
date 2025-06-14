"""
OAuth authentication for Facebook API.
"""

import asyncio
import ssl
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import aiohttp

from config.settings import (FB_API_VERSION, FB_APP_ID, FB_APP_SECRET,
                             FB_REDIRECT_URI)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create SSL context that ignores verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class FacebookOAuth:
    """
    Handles the Facebook OAuth 2.0 authentication flow.
    """

    def __init__(
        self,
        app_id: str = FB_APP_ID,
        app_secret: str = FB_APP_SECRET,
        redirect_uri: str = FB_REDIRECT_URI,
        api_version: str = FB_API_VERSION,
    ):
        """
        Initialize the OAuth handler.

        Args:
            app_id: Facebook App ID.
            app_secret: Facebook App Secret.
            redirect_uri: The URI to redirect to after authentication.
            api_version: Facebook API version to use.
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        self.api_version = api_version

        if not all([app_id, app_secret, redirect_uri]):
            logger.error("Facebook OAuth credentials are not configured properly")
            raise ValueError("Facebook OAuth credentials are missing")

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Get the Facebook authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            The authorization URL.
        """
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "ads_read",  # Minimum required scope
            "response_type": "code",
        }

        if state:
            params["state"] = state

        auth_url = f"https://www.facebook.com/{self.api_version}/dialog/oauth?{urlencode(params)}"
        logger.debug(f"Generated authorization URL: {auth_url}")

        return auth_url

    async def exchange_code_for_token(
        self, code: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Exchange an authorization code for an access token.

        Args:
            code: The authorization code received from Facebook.

        Returns:
            A tuple containing (token_data, error_message).
            token_data includes access_token, expires_in, and possibly refresh_token.
            If an error occurs, token_data will be None and error_message will contain the error.
        """
        try:
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            }

            token_url = (
                f"https://graph.facebook.com/{self.api_version}/oauth/access_token"
            )
            print(f"DEBUG: Requesting token from {token_url}")

            # Using a ClientSession with SSL verification disabled
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(token_url, params=params) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        print(
                            f"DEBUG: Successfully received token - Keys: {', '.join(token_data.keys())}"
                        )

                        # Check for required fields
                        if "access_token" not in token_data:
                            print("DEBUG: Error - access_token not in response")
                            return None, "Access token not found in response"

                        if "expires_in" not in token_data:
                            print(
                                "DEBUG: Warning - expires_in not in response, using default 3600"
                            )
                            token_data["expires_in"] = 3600
                        else:
                            print(
                                f"DEBUG: Token expires in: {token_data['expires_in']} seconds"
                            )

                        logger.info("Successfully exchanged code for access token")
                        return token_data, None
                    else:
                        try:
                            error_data = await response.json()
                            error_message = error_data.get("error", {}).get(
                                "message", "Unknown error"
                            )
                            print(f"DEBUG: Token exchange error: {error_message}")
                            logger.error(
                                f"Failed to exchange code for token: {error_message}"
                            )
                        except:
                            error_text = await response.text()
                            print(f"DEBUG: Token exchange error (raw): {error_text}")
                            error_message = f"Failed with status {response.status}: {error_text[:100]}"
                            logger.error(
                                f"Failed to exchange code for token: {error_message}"
                            )

                        return None, error_message

        except Exception as e:
            print(f"DEBUG: Exception during token exchange: {str(e)}")
            logger.error(f"Exception during token exchange: {str(e)}")
            return None, str(e)

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token.

        Returns:
            A tuple containing (token_data, error_message).
            token_data includes the new access_token and expires_in.
            If an error occurs, token_data will be None and error_message will contain the error.
        """
        try:
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": refresh_token,
            }

            token_url = (
                f"https://graph.facebook.com/{self.api_version}/oauth/access_token"
            )

            # Using a ClientSession with SSL verification disabled
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(token_url, params=params) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        logger.info("Successfully refreshed access token")
                        return token_data, None
                    else:
                        error_data = await response.json()
                        error_message = error_data.get("error", {}).get(
                            "message", "Unknown error"
                        )
                        logger.error(f"Failed to refresh token: {error_message}")
                        return None, error_message

        except Exception as e:
            logger.error(f"Exception during token refresh: {str(e)}")
            return None, str(e)

    async def validate_token(self, access_token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an access token.

        Args:
            access_token: The access token to validate.

        Returns:
            A tuple containing (is_valid, error_message).
            If the token is valid, is_valid will be True and error_message will be None.
            If the token is invalid, is_valid will be False and error_message will contain the error.
        """
        try:
            params = {
                "input_token": access_token,
                "access_token": f"{self.app_id}|{self.app_secret}",
            }

            debug_url = f"https://graph.facebook.com/{self.api_version}/debug_token"

            # Using a ClientSession with SSL verification disabled
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(debug_url, params=params) as response:
                    if response.status == 200:
                        debug_data = await response.json()
                        data = debug_data.get("data", {})

                        is_valid = data.get("is_valid", False)
                        if is_valid:
                            logger.info("Token is valid")
                            return True, None
                        else:
                            error_message = data.get("error", {}).get(
                                "message", "Token is invalid"
                            )
                            logger.warning(f"Token validation failed: {error_message}")
                            return False, error_message
                    else:
                        error_data = await response.json()
                        error_message = error_data.get("error", {}).get(
                            "message", "Unknown error"
                        )
                        logger.error(f"Failed to validate token: {error_message}")
                        return False, error_message

        except Exception as e:
            logger.error(f"Exception during token validation: {str(e)}")
            return False, str(e)


# Create a singleton instance
oauth_handler = FacebookOAuth()
