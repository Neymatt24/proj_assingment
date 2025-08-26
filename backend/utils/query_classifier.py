from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, Any
import logging

logger = logging.getLogger("query_classifier")

class QueryClassifier:
    """Classify iPad-related queries into different categories"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        
        self.categories = {
            "specifications": "Technical specs, features, hardware details",
            "pricing": "Price, cost, payment options, deals",
            "comparison": "Compare models, differences, which to choose",
            "availability": "Stock, release dates, where to buy",
            "troubleshooting": "Problems, fixes, support, how-to",
            "features": "Software features, capabilities, what it can do",
            "accessories": "Apple Pencil, keyboards, cases, compatible accessories",
            "general": "General questions about iPad"
        }
    
    async def classify(self, query: str) -> str:
        """Classify the query into one of the predefined categories"""
        system_prompt = f"""
        You are a query classifier for iPad-related questions. Classify the following query into one of these categories:
        
        {self._format_categories()}
        
        Return only the category name, nothing else.
        
        Examples:
        - "What's the price of iPad Pro?" -> pricing
        - "iPad Air vs iPad Pro differences" -> comparison
        - "iPad won't turn on" -> troubleshooting
        - "iPad Pro specifications" -> specifications
        - "Is iPad Pro available?" -> availability
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            category = response.content.strip().lower()
            
            # Validate category
            if category in self.categories:
                return category
            else:
                return "general"
                
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return "general"
    
    def _format_categories(self) -> str:
        """Format categories for prompt"""
        formatted = []
        for category, description in self.categories.items():
            formatted.append(f"- {category}: {description}")
        return "\n".join(formatted)
