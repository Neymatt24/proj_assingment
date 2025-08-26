from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, List, Any
import json
import logging

logger = logging.getLogger("response_generator")

class ResponseGenerator:
    """Generate comprehensive responses using ChatGroq"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
    
    async def generate(self, query: str, query_type: str, processed_info: Dict, sources: List[str]) -> str:
        """Generate a comprehensive response based on the query and gathered information"""
        
        system_prompt = f"""
        You are an expert iPad assistant that provides accurate, helpful, and comprehensive answers about Apple iPads.
        
        Your role:
        - Provide detailed, accurate information about iPads
        - Use the search results and processed information to answer queries
        - Be specific with model names, prices, and technical specifications when available
        - Always mention if information might be outdated and suggest checking Apple's official website
        - Format responses clearly with proper structure
        
        Query Type: {query_type}
        
        Guidelines for different query types:
        - Specifications: Include technical details, dimensions, performance metrics
        - Pricing: Mention specific prices, storage options, and where to buy
        - Comparison: Create clear comparisons with pros/cons
        - Troubleshooting: Provide step-by-step solutions
        - Availability: Include release dates, stock status
        - Features: Explain capabilities and use cases
        
        Format your response in a user-friendly way with:
        1. Direct answer to the question
        2. Supporting details and context
        3. Additional relevant information
        4. Suggestions for next steps if applicable
        """
        
        # Prepare context from processed information
        context = self._prepare_context(processed_info, sources)
        
        human_prompt = f"""
        User Query: {query}
        
        Context from web search:
        {context}
        
        Please provide a comprehensive answer to the user's question about iPads.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            return self._format_response(response.content, sources)
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return self._generate_fallback_response(query, query_type)
    
    def _prepare_context(self, processed_info: Dict, sources: List[str]) -> str:
        """Prepare context from processed information"""
        context_parts = []
        
        if processed_info.get("key_facts"):
            context_parts.append(f"Key Facts: {', '.join(processed_info['key_facts'])}")
        
        if processed_info.get("specifications"):
            specs = processed_info["specifications"]
            context_parts.append(f"Specifications: {json.dumps(specs, indent=2)}")
        
        if processed_info.get("pricing"):
            pricing = processed_info["pricing"]
            context_parts.append(f"Pricing Information: {json.dumps(pricing, indent=2)}")
        
        if processed_info.get("features"):
            context_parts.append(f"Features: {', '.join(processed_info['features'])}")
        
        if processed_info.get("troubleshooting"):
            context_parts.append(f"Troubleshooting Info: {', '.join(processed_info['troubleshooting'])}")
        
        if processed_info.get("comparisons"):
            context_parts.append(f"Comparison Data: {', '.join(processed_info['comparisons'])}")
        
        return "\n\n".join(context_parts) if context_parts else "No specific context available."
    
    def _format_response(self, response: str, sources: List[str]) -> str:
        """Format the response with sources if available"""
        formatted_response = response.strip()
        
        # Add sources at the end if available
        if sources:
            valid_sources = [src for src in sources if src and src.startswith('http')]
            if valid_sources:
                formatted_response += "\n\n📚 **Sources:**"
                for i, source in enumerate(valid_sources[:3], 1):  # Limit to 3 sources
                    formatted_response += f"\n{i}. {source}"
        
        return formatted_response
    
    def _generate_fallback_response(self, query: str, query_type: str) -> str:
        """Generate a fallback response when main generation fails"""
        fallback_responses = {
            "specifications": "I'd be happy to help you with iPad specifications. For the most accurate and up-to-date technical specifications, I recommend checking Apple's official website at apple.com/ipad or visiting an Apple Store.",
            
            "pricing": "For current iPad pricing information, please visit Apple's official website at apple.com/shop/buy-ipad or contact your local Apple Store, as prices may vary by region and are subject to change.",
            
            "comparison": "To compare different iPad models, I recommend using Apple's comparison tool at apple.com/ipad/compare where you can see detailed side-by-side comparisons of features, specifications, and pricing.",
            
            "troubleshooting": "For troubleshooting your iPad, please visit Apple Support at support.apple.com/ipad or contact Apple Support directly for personalized assistance with your specific issue.",
            
            "availability": "For current iPad availability and stock information, please check Apple's website at apple.com/ipad or contact your local Apple Store for real-time inventory updates.",
            
            "features": "iPad offers many powerful features. For detailed information about iPad capabilities and features, please visit apple.com/ipad to explore all the latest functionality.",
            
            "accessories": "Apple offers various iPad accessories including Apple Pencil, Magic Keyboard, and Smart Covers. Visit apple.com/ipad/accessories for the complete selection.",
            
            "general": "For comprehensive information about iPads, including specifications, pricing, and features, please visit Apple's official iPad page at apple.com/ipad."
        }
        
        base_response = fallback_responses.get(query_type, fallback_responses["general"])
        return f"I apologize, but I'm having trouble accessing the latest information right now. {base_response}"