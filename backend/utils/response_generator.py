# backend/utils/response_generator.py
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, List, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger("response_generator")

class ResponseGenerator:
    """Enhanced response generator with conversation context"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
    
    async def generate(self, query: str, query_type: str, processed_info: Dict, sources: List[str]) -> str:
        """Generate response without context for backward compatibility"""
        return await self.generate_with_context(query, query_type, processed_info, sources, "")
    
    async def generate_with_context(self, query: str, query_type: str, processed_info: Dict, 
                                   sources: List[str], conversation_context: str = "") -> str:
        """Generate a comprehensive response with conversation context"""
        
        current_date = datetime.now().strftime("%B %Y")
        
        context_instruction = ""
        if conversation_context.strip():
            context_instruction = f"""
            Previous conversation context:
            {conversation_context}
            
            Consider this context when answering. If the user is asking follow-up questions, reference previous topics naturally. If they're continuing a comparison or asking for more details about something mentioned earlier, build upon that context.
            """
        
        system_prompt = f"""
        You are an expert iPad assistant providing accurate, helpful, and up-to-date answers about Apple iPads.
        Current date: {current_date}
        
        Your role:
        - Provide detailed, accurate information about iPads using the latest search results
        - Be specific with model names, prices, and technical specifications when available
        - Always prioritize information from official Apple sources (apple.com, support.apple.com)
        - Mention when information might need verification and suggest checking Apple's official website
        - Format responses clearly and conversationally
        - Use search results to provide current, real-time information
        
        Query Type: {query_type}
        
        {context_instruction}
        
        Guidelines for different query types:
        - specifications: Include technical details, performance metrics, display info, processors
        - pricing: Mention specific prices, storage options, where to buy, any deals
        - comparison: Create clear comparisons with pros/cons, help users choose
        - troubleshooting: Provide step-by-step solutions and additional resources
        - availability: Include release dates, stock status, where to find
        - features: Explain capabilities, use cases, and practical applications
        - accessories: Detail compatibility, features, and recommendations
        - setup: Provide clear setup instructions and tips
        - updates: Explain new features and how to update
        
        Response format:
        1. Direct answer to the question using latest search results
        2. Supporting details and context from search data
        3. Specific information (prices, specs, dates) when available
        4. Additional helpful tips or related information
        5. Suggestion to verify latest info on Apple's website if needed
        """
        
        # Prepare context from processed information and search results
        context = self._prepare_detailed_context(processed_info, sources)
        
        human_prompt = f"""
        User Query: {query}
        
        Latest search results and information:
        {context}
        
        Please provide a comprehensive, conversational answer using the search results above. Focus on being helpful and informative while using the most current information available.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            return self._format_response(response.content, sources, query_type)
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return self._generate_fallback_response(query, query_type)
    
    def _prepare_detailed_context(self, processed_info: Dict, sources: List[str]) -> str:
        """Prepare detailed context from processed information and search results"""
        context_parts = []
        
        # Add latest information from search results
        if processed_info.get("latest_info"):
            context_parts.append("=== LATEST SEARCH RESULTS ===")
            for i, info in enumerate(processed_info["latest_info"][:5], 1):
                context_parts.append(f"{i}. {info.get('title', 'N/A')}")
                context_parts.append(f"   Content: {info.get('content', 'N/A')}")
                context_parts.append(f"   Source: {info.get('url', 'N/A')}")
                context_parts.append("")
        
        # Add specific extracted information
        if processed_info.get("pricing") and processed_info["pricing"]:
            context_parts.append("=== PRICING INFORMATION ===")
            pricing = processed_info["pricing"]
            if pricing.get("prices_found"):
                context_parts.append(f"Prices found: {', '.join(pricing['prices_found'])}")
            if pricing.get("source"):
                context_parts.append(f"Source: {pricing['source']}")
            context_parts.append("")
        
        if processed_info.get("specifications") and processed_info["specifications"]:
            context_parts.append("=== SPECIFICATIONS MENTIONED ===")
            specs = processed_info["specifications"]
            for key, value in specs.items():
                if value:
                    context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            context_parts.append("")
        
        # Add other relevant information
        for key in ["key_facts", "features", "troubleshooting", "comparisons"]:
            if processed_info.get(key) and processed_info[key]:
                context_parts.append(f"=== {key.upper().replace('_', ' ')} ===")
                if isinstance(processed_info[key], list):
                    for item in processed_info[key]:
                        context_parts.append(f"- {item}")
                else:
                    context_parts.append(str(processed_info[key]))
                context_parts.append("")
        
        return "\n".join(context_parts) if context_parts else "No specific search results available."
    
    def _format_response(self, response: str, sources: List[str], query_type: str) -> str:
        """Format the response with sources and additional context"""
        formatted_response = response.strip()
        
        # Add query type indicator (subtle)
        type_emoji = self._get_type_emoji(query_type)
        if type_emoji:
            formatted_response = f"{type_emoji} {formatted_response}"
        
        # Add sources at the end if available
        if sources:
            valid_sources = [src for src in sources if src and src.startswith('http')][:3]
            if valid_sources:
                formatted_response += "\n\n📚 **Sources:**"
                for i, source in enumerate(valid_sources, 1):
                    # Try to make source names more readable
                    source_name = self._get_readable_source_name(source)
                    formatted_response += f"\n{i}. [{source_name}]({source})"
        
        # Add timestamp for freshness indication
        current_time = datetime.now().strftime("%B %d, %Y")
        formatted_response += f"\n\n*Information current as of {current_time}*"
        
        return formatted_response
    
    def _get_type_emoji(self, query_type: str) -> str:
        """Get emoji for query type"""
        emoji_map = {
            "specifications": "⚙️",
            "pricing": "💰",
            "comparison": "⚖️",
            "troubleshooting": "🔧",
            "availability": "📦",
            "features": "✨",
            "accessories": "🎯",
            "setup": "🚀",
            "updates": "🔄",
            "general": "ℹ️"
        }
        return emoji_map.get(query_type, "")
    
    def _get_readable_source_name(self, url: str) -> str:
        """Get readable name for source URL"""
        if "apple.com" in url:
            if "support.apple.com" in url:
                return "Apple Support"
            elif "shop" in url:
                return "Apple Store"
            else:
                return "Apple Official"
        elif "serpapi" in url or "google" in url:
            return "Web Search"
        else:
            # Extract domain name
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace("www.", "").title()
            except:
                return "External Source"
    
    def _generate_fallback_response(self, query: str, query_type: str) -> str:
        """Generate a fallback response when main generation fails"""
        current_date = datetime.now().strftime("%B %Y")
        
        fallback_responses = {
            "specifications": f"I'd be happy to help you with iPad specifications. For the most current and detailed technical specifications as of {current_date}, I recommend checking Apple's official website at apple.com/ipad or visiting an Apple Store where you can see the devices in person.",
            
            "pricing": f"For current iPad pricing information as of {current_date}, please visit Apple's official website at apple.com/shop/buy-ipad or contact your local Apple Store. Prices may vary by region and are subject to change, and Apple sometimes offers special deals for students and educators.",
            
            "comparison": f"To compare different iPad models with the latest {current_date} specifications, I recommend using Apple's comparison tool at apple.com/ipad/compare where you can see detailed side-by-side comparisons of features, specifications, and pricing.",
            
            "troubleshooting": f"For troubleshooting your iPad, please visit Apple Support at support.apple.com/ipad where you'll find updated guides for {current_date}, or contact Apple Support directly for personalized assistance with your specific issue.",
            
            "availability": f"For current iPad availability and stock information as of {current_date}, please check Apple's website at apple.com/ipad or contact your local Apple Store for real-time inventory updates.",
            
            "features": f"iPad offers many powerful features that are regularly updated. For detailed information about the latest iPad capabilities and features as of {current_date}, please visit apple.com/ipad to explore all the current functionality.",
            
            "accessories": f"Apple offers various iPad accessories including Apple Pencil, Magic Keyboard, and Smart Covers. For the complete {current_date} selection and compatibility information, visit apple.com/ipad/accessories.",
            
            "setup": f"For help setting up your iPad with the latest {current_date} instructions, visit Apple's setup guide at support.apple.com/ipad or use the built-in Setup Assistant on your device.",
            
            "updates": f"For information about the latest iPadOS updates and features as of {current_date}, check Settings > General > Software Update on your iPad or visit apple.com/ipados.",
            
            "general": f"For comprehensive information about iPads including the latest {current_date} specifications, pricing, and features, please visit Apple's official iPad page at apple.com/ipad."
        }
        
        base_response = fallback_responses.get(query_type, fallback_responses["general"])
        return f"I apologize, but I'm having trouble accessing the latest search results right now. {base_response}"
