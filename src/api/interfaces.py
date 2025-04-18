"""
Interfaces for API clients and services.

This module defines interfaces for the Facebook Marketing API client and related services.
These interfaces provide clear contracts for implementations and improve type checking.
"""
from typing import Protocol, List, Dict, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod


class FacebookAdsClientInterface(Protocol):
    """Interface for Facebook Ads API client."""
    
    async def get_access_token(self) -> str:
        """
        Get the access token for API requests.
        
        Returns:
            str: The access token.
            
        Raises:
            TokenNotSetError: If the token is not set.
            TokenExpiredError: If the token is expired.
        """
        ...
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                            method: str = 'GET', retries: int = 3) -> Dict:
        """
        Make a request to the Facebook Marketing API.
        
        Args:
            endpoint: The API endpoint to request.
            params: Optional parameters for the request.
            method: HTTP method to use. Default is GET.
            retries: Maximum number of retries. Default is 3.
            
        Returns:
            The JSON response from the API.
            
        Raises:
            FacebookAdsApiError: For API errors.
            NetworkError: For network-related errors.
        """
        ...
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated user.
        
        Returns:
            Dict containing user information.
        """
        ...


class AccountServiceInterface(Protocol):
    """Interface for Facebook Ad Account services."""
    
    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all ad accounts available to the user.
        
        Returns:
            List of ad account objects.
        """
        ...
    
    async def get_accounts(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Get the user's ad accounts with error handling.
        
        Returns:
            Tuple of (accounts list, error message or None).
        """
        ...


class CampaignServiceInterface(Protocol):
    """Interface for Facebook Campaign services."""
    
    async def get_campaigns(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get campaigns for a specific ad account.
        
        Args:
            account_id: The ad account ID.
            
        Returns:
            List of campaign objects.
        """
        ...
    
    async def get_campaign_insights(self, campaign_id: str, date_preset: Optional[str] = None,
                                   time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get insights for a specific campaign.
        
        Args:
            campaign_id: The campaign ID.
            date_preset: Predefined date range (e.g., "last_7_days").
            time_range: Custom time range with start and end dates.
            
        Returns:
            Campaign insights data.
        """
        ...


class AdServiceInterface(Protocol):
    """Interface for Facebook Ad services."""
    
    async def get_ads(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Get ads for a specific campaign.
        
        Args:
            campaign_id: The campaign ID.
            
        Returns:
            List of ad objects.
        """
        ...
    
    async def get_ad_insights(self, ad_id: str, date_preset: Optional[str] = None,
                             time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get insights for a specific ad.
        
        Args:
            ad_id: The ad ID.
            date_preset: Predefined date range (e.g., "last_7_days").
            time_range: Custom time range with start and end dates.
            
        Returns:
            Ad insights data.
        """
        ...


class InsightServiceInterface(Protocol):
    """Interface for Facebook Insight services."""
    
    async def get_insights(self, object_id: str, level: str, date_preset: Optional[str] = None,
                          time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get insights for a specific object.
        
        Args:
            object_id: The object ID (account, campaign, ad).
            level: The insight level (account, campaign, ad).
            date_preset: Predefined date range (e.g., "last_7_days").
            time_range: Custom time range with start and end dates.
            
        Returns:
            Insights data.
        """
        ... 