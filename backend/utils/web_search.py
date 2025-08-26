# backend/utils/web_search.py
import aiohttp
import asyncio
from typing import List, Dict, Optional
import os
import json
from urllib.parse import quote
import logging

logger = logging.getLogger("web_search")

class WebSearchTool:
    """Web search tool for fetching real-time iPad information"""
    
    def __init__(self):
        self.session = None
        # You can use multiple search APIs - Google Custom Search, Bing, SerpAPI, etc.
        self.search_apis = {
            "serpapi": {
                "url": "https://serpapi.com/search.json",
                "key": os.getenv("SERPAPI_KEY")
            },
            "google_custom": {
                "url": "https://www.googleapis.com/customsearch/v1",
                "key": os.getenv("GOOGLE_API_KEY"),
                "cx": os.getenv("GOOGLE_SEARCH_ENGINE_ID")
            }
        }
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search for information using available search APIs"""
        try:
            # Try SerpAPI first
            if self.search_apis["serpapi"]["key"]:
                return await self._search_serpapi(query, num_results)
            
            # Fallback to Google Custom Search
            elif (self.search_apis["google_custom"]["key"] and 
                  self.search_apis["google_custom"]["cx"]):
                return await self._search_google_custom(query, num_results)
            
            else:
                # If no API keys available, return mock data for development
                return self._get_mock_search_results(query)
                
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return self._get_mock_search_results(query)
    
    async def _search_serpapi(self, query: str, num_results: int) -> List[Dict]:
        """Search using SerpAPI"""
        session = await self._get_session()
        
        params = {
            "q": f"{query} site:apple.com OR site:support.apple.com OR iPad",
            "api_key": self.search_apis["serpapi"]["key"],
            "engine": "google",
            "num": min(num_results, 10),
            "hl": "en",
            "gl": "us"
        }
        
        async with session.get(self.search_apis["serpapi"]["url"], params=params) as response:
            if response.status == 200:
                data = await response.json()
                return self._parse_serpapi_results(data)
            else:
                logger.error(f"SerpAPI request failed with status {response.status}")
                return []
    
    async def _search_google_custom(self, query: str, num_results: int) -> List[Dict]:
        """Search using Google Custom Search API"""
        session = await self._get_session()
        
        params = {
            "q": f"{query} iPad Apple",
            "key": self.search_apis["google_custom"]["key"],
            "cx": self.search_apis["google_custom"]["cx"],
            "num": min(num_results, 10)
        }
        
        async with session.get(self.search_apis["google_custom"]["url"], params=params) as response:
            if response.status == 200:
                data = await response.json()
                return self._parse_google_custom_results(data)
            else:
                logger.error(f"Google Custom Search failed with status {response.status}")
                return []
    
    def _parse_serpapi_results(self, data: Dict) -> List[Dict]:
        """Parse SerpAPI response"""
        results = []
        
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "source": "serpapi"
            })
        
        return results
    
    def _parse_google_custom_results(self, data: Dict) -> List[Dict]:
        """Parse Google Custom Search API response"""
        results = []
        
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "source": "google_custom"
            })
        
        return results
    
    def _get_mock_search_results(self, query: str) -> List[Dict]:
        """Return mock search results for development/testing"""
        mock_results = [
            {
                "title": "iPad - Apple",
                "url": "https://www.apple.com/ipad/",
                "content": f"Explore iPad models including iPad Pro, iPad Air, and iPad mini. Find the perfect iPad for your needs with features like Apple Pencil support, advanced displays, and powerful processors. Related to: {query}",
                "source": "mock"
            },
            {
                "title": "iPad Technical Specifications - Apple Support",
                "url": "https://support.apple.com/kb/SP785",
                "content": f"Technical specifications for iPad including display, processor, storage, and connectivity options. Learn about the latest features and capabilities. Query context: {query}",
                "source": "mock"
            },
            {
                "title": "Buy iPad - Apple Store",
                "url": "https://www.apple.com/shop/buy-ipad/",
                "content": f"Shop for iPad with various storage options, colors, and accessories. Compare prices and find the best iPad for your budget and needs. Search: {query}",
                "source": "mock"
            },
            {
                "title": "iPad User Guide - Apple Support",
                "url": "https://support.apple.com/guide/ipad/",
                "content": f"Complete guide for using your iPad including setup, troubleshooting, and advanced features. Get help with common issues and learn new tips. Related query: {query}",
                "source": "mock"
            },
            {
                "title": "Compare iPad Models - Apple",
                "url": "https://www.apple.com/ipad/compare/",
                "content": f"Compare different iPad models side by side including iPad Pro 12.9-inch, iPad Pro 11-inch, iPad Air, and iPad mini. See differences in features, pricing, and specifications. Query: {query}",
                "source": "mock"
            }
        ]
        
        return mock_results
    
    async def search_apple_store(self, query: str) -> List[Dict]:
        """Specifically search Apple Store for product information"""
        apple_query = f"site:apple.com {query} iPad"
        return await self.search(apple_query)
    
    async def search_apple_support(self, query: str) -> List[Dict]:
        """Search Apple Support for troubleshooting information"""
        support_query = f"site:support.apple.com {query} iPad"
        return await self.search(support_query)
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None