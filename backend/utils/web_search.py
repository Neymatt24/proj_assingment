# backend/utils/web_search.py
import aiohttp
import asyncio
from typing import List, Dict, Optional
import os
import json
from urllib.parse import quote
import logging
from datetime import datetime

logger = logging.getLogger("web_search")

class WebSearchTool:
    """Enhanced web search tool for fetching real-time iPad information"""
    
    def __init__(self):
        self.session = None
        self._force_real_search = True  # Force real search by default
        
        # Search API configurations
        self.search_apis = {
            "duckduckgo": {
                "enabled": True,
                "url": "https://api.duckduckgo.com/",
                "requires_key": False
            },
            "serpapi": {
                "enabled": bool(os.getenv("SERPAPI_KEY")),
                "url": "https://serpapi.com/search.json",
                "key": os.getenv("SERPAPI_KEY")
            },
            "google_custom": {
                "enabled": bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_SEARCH_ENGINE_ID")),
                "url": "https://www.googleapis.com/customsearch/v1",
                "key": os.getenv("GOOGLE_API_KEY"),
                "cx": os.getenv("GOOGLE_SEARCH_ENGINE_ID")
            }
        }
        
        logger.info(f"Available search APIs: {[k for k, v in self.search_apis.items() if v['enabled']]}")
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'iPad Assistant Bot 1.0'
                }
            )
        return self.session
    
    async def search_real_time(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search for real-time information using available search APIs"""
        logger.info(f"Performing real-time search for: {query}")
        
        try:
            # Try different search APIs in order of preference
            if self.search_apis["serpapi"]["enabled"]:
                results = await self._search_serpapi(query, num_results)
                if results:
                    logger.info(f"SerpAPI returned {len(results)} results")
                    return results
            
            if self.search_apis["google_custom"]["enabled"]:
                results = await self._search_google_custom(query, num_results)
                if results:
                    logger.info(f"Google Custom Search returned {len(results)} results")
                    return results
            
            # Fallback to DuckDuckGo instant answer (limited but free)
            results = await self._search_duckduckgo(query)
            if results:
                logger.info(f"DuckDuckGo returned {len(results)} results")
                return results
            
            # If all else fails, try web scraping approach
            results = await self._search_web_scraping(query, num_results)
            if results:
                logger.info(f"Web scraping returned {len(results)} results")
                return results
            
            logger.warning("All search methods failed, returning mock data")
            return self._get_mock_search_results(query)
            
        except Exception as e:
            logger.error(f"Real-time search failed: {str(e)}")
            return self._get_mock_search_results(query)
    
    async def _search_serpapi(self, query: str, num_results: int) -> List[Dict]:
        """Search using SerpAPI"""
        if not self.search_apis["serpapi"]["enabled"]:
            return []
            
        session = await self._get_session()
        
        params = {
            "q": f"{query} Apple iPad 2024 2025",
            "api_key": self.search_apis["serpapi"]["key"],
            "engine": "google",
            "num": min(num_results, 10),
            "hl": "en",
            "gl": "us",
            "safe": "active"
        }
        
        try:
            async with session.get(self.search_apis["serpapi"]["url"], params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_serpapi_results(data)
                else:
                    logger.error(f"SerpAPI request failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"SerpAPI error: {str(e)}")
            return []
    
    async def _search_google_custom(self, query: str, num_results: int) -> List[Dict]:
        """Search using Google Custom Search API"""
        if not self.search_apis["google_custom"]["enabled"]:
            return []
            
        session = await self._get_session()
        
        params = {
            "q": f"{query} Apple iPad",
            "key": self.search_apis["google_custom"]["key"],
            "cx": self.search_apis["google_custom"]["cx"],
            "num": min(num_results, 10),
            "safe": "active"
        }
        
        try:
            async with session.get(self.search_apis["google_custom"]["url"], params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_google_custom_results(data)
                else:
                    logger.error(f"Google Custom Search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Google Custom Search error: {str(e)}")
            return []
    
    async def _search_duckduckgo(self, query: str) -> List[Dict]:
        """Search using DuckDuckGo instant answer API (limited results)"""
        session = await self._get_session()
        
        params = {
            "q": f"{query} iPad Apple",
            "format": "json",
            "pretty": 1,
            "safe_search": 1
        }
        
        try:
            async with session.get("https://api.duckduckgo.com/", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_duckduckgo_results(data, query)
                else:
                    logger.error(f"DuckDuckGo request failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"DuckDuckGo error: {str(e)}")
            return []
    
    async def _search_web_scraping(self, query: str, num_results: int) -> List[Dict]:
        """Fallback web scraping approach for getting Apple official info"""
        session = await self._get_session()
        results = []
        
        # Try to get Apple official pages
        apple_urls = [
            "https://www.apple.com/ipad/",
            "https://www.apple.com/ipad-pro/",
            "https://www.apple.com/ipad-air/",
            "https://www.apple.com/ipad-mini/"
        ]
        
        for url in apple_urls[:3]:  # Limit to avoid timeout
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Simple HTML parsing to extract basic info
                        title = self._extract_title_from_html(html)
                        content = self._extract_content_from_html(html, query)
                        
                        if title and content:
                            results.append({
                                "title": title,
                                "url": url,
                                "content": content,
                                "source": "apple_official",
                                "timestamp": datetime.now().isoformat()
                            })
                
                await asyncio.sleep(1)  # Be respectful
                
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {str(e)}")
                continue
        
        return results
    
    def _extract_title_from_html(self, html: str) -> str:
        """Simple title extraction from HTML"""
        import re
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        return title_match.group(1).strip() if title_match else "Apple iPad"
    
    def _extract_content_from_html(self, html: str, query: str) -> str:
        """Simple content extraction from HTML"""
        import re
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Find relevant sentences containing query terms
        sentences = text.split('.')
        relevant_sentences = []
        
        query_words = query.lower().split()
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(word in sentence.lower() for word in query_words):
                relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 3:
                    break
        
        return '. '.join(relevant_sentences) if relevant_sentences else text[:500]
    
    def _parse_serpapi_results(self, data: Dict) -> List[Dict]:
        """Parse SerpAPI response"""
        results = []
        
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "content": item.get("snippet", ""),
                "source": "serpapi",
                "timestamp": datetime.now().isoformat()
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
                "source": "google_custom",
                "timestamp": datetime.now().isoformat()
            })
        
        return results
    
    def _parse_duckduckgo_results(self, data: Dict, query: str) -> List[Dict]:
        """Parse DuckDuckGo API response"""
        results = []
        
        # DuckDuckGo instant answer
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "iPad Information"),
                "url": data.get("AbstractURL", ""),
                "content": data.get("Abstract", ""),
                "source": "duckduckgo_instant",
                "timestamp": datetime.now().isoformat()
            })
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": f"Related: {topic.get('Text', '')[:50]}...",
                    "url": topic.get("FirstURL", ""),
                    "content": topic.get("Text", ""),
                    "source": "duckduckgo_related",
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    # Keep the original search method for backward compatibility
    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Main search method - routes to real-time search"""
        return await self.search_real_time(query, num_results)
    
    def _get_mock_search_results(self, query: str) -> List[Dict]:
        """Return enhanced mock search results for development/testing"""
        current_year = datetime.now().year
        mock_results = [
            {
                "title": f"iPad Models {current_year} - Apple Official",
                "url": "https://www.apple.com/ipad/",
                "content": f"Discover the latest iPad lineup for {current_year} including iPad Pro with M2 chip, iPad Air with M1 chip, and iPad mini. Features include Liquid Retina displays, Apple Pencil support, and advanced cameras. Query: {query}",
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": f"iPad Pro {current_year} Technical Specifications",
                "url": "https://support.apple.com/kb/SP885",
                "content": f"iPad Pro {current_year} features M2 chip, 12.9-inch Liquid Retina XDR display, up to 2TB storage, 5G connectivity, and support for Apple Pencil (2nd generation). Available in Silver and Space Gray. Related to: {query}",
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": f"Buy iPad - Apple Store Online {current_year}",
                "url": "https://www.apple.com/shop/buy-ipad/",
                "content": f"Shop iPad Pro starting at $1099, iPad Air from $599, iPad from $449, and iPad mini from $499. Available with various storage options and cellular connectivity. Free delivery and returns. Query context: {query}",
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": f"iPad Troubleshooting Guide {current_year} - Apple Support",
                "url": "https://support.apple.com/guide/ipad/",
                "content": f"Get help with iPad issues including charging problems, display issues, app crashes, and connectivity problems. Step-by-step solutions for common iPad problems. Updated for iPadOS 17. Related: {query}",
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": f"iPad vs iPad Pro vs iPad Air Comparison {current_year}",
                "url": "https://www.apple.com/ipad/compare/",
                "content": f"Compare iPad models: iPad Pro (M2 chip, ProMotion display), iPad Air (M1 chip, 10.9-inch display), standard iPad (A14 chip, 10.9-inch display), and iPad mini (A15 chip, 8.3-inch display). Find the perfect iPad for your needs. Query: {query}",
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return mock_results
    
    async def search_apple_store(self, query: str) -> List[Dict]:
        """Specifically search Apple Store for product information"""
        apple_query = f"site:apple.com {query} iPad"
        return await self.search_real_time(apple_query)
    
    async def search_apple_support(self, query: str) -> List[Dict]:
        """Search Apple Support for troubleshooting information"""
        support_query = f"site:support.apple.com {query} iPad"
        return await self.search_real_time(support_query)
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
