# backend/utils/query_classifier.py
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, Any
import logging

logger = logging.getLogger("query_classifier")

class QueryClassifier:
    """Enhanced classifier for iPad-related queries with conversation context"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        
        self.categories = {
            "specifications": "Technical specs, features, hardware details, processor, display, storage",
            "pricing": "Price, cost, payment options, deals, discounts, availability for purchase",
            "comparison": "Compare models, differences, which to choose, versus, vs",
            "availability": "Stock, release dates, where to buy, when available",
            "troubleshooting": "Problems, fixes, support, how-to, not working, issues",
            "features": "Software features, capabilities, what it can do, apps, functionality",
            "accessories": "Apple Pencil, keyboards, cases, compatible accessories, add-ons",
            "setup": "Initial setup, configuration, getting started, installation",
            "updates": "Software updates, iPadOS, new versions, upgrade",
            "general": "General questions about iPad, basic information"
        }
    
    async def classify(self, query: str) -> str:
        """Classify the query into one of the predefined categories"""
        return await self.classify_with_context(query, "")
    
    async def classify_with_context(self, query: str, conversation_context: str = "") -> str:
        """Classify the query with conversation context"""
        
        context_prompt = ""
        if conversation_context.strip():
            context_prompt = f"""
            Previous conversation context:
            {conversation_context}
            
            Use this context to better understand the current query. If the user is continuing a previous topic, consider that in your classification.
            """
        
        system_prompt = f"""
        You are a query classifier for iPad-related questions. Classify the following query into one of these categories:
        
        {self._format_categories()}
        
        {context_prompt}
        
        Return only the category name in lowercase, nothing else.
        
        Classification examples:
        - "What's the price of iPad Pro?" -> pricing
        - "iPad Air vs iPad Pro differences" -> comparison
        - "My iPad won't turn on" -> troubleshooting
        - "iPad Pro M2 specifications" -> specifications
        - "Is the new iPad available?" -> availability
        - "What can iPad do?" -> features
        - "How to set up my new iPad?" -> setup
        - "Apple Pencil for iPad" -> accessories
        - "iPadOS 17 features" -> updates
        
        Focus on the main intent of the query.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query to classify: {query}")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            category = response.content.strip().lower()
            
            # Validate category
            if category in self.categories:
                logger.info(f"Query '{query}' classified as: {category}")
                return category
            else:
                logger.warning(f"Unknown category '{category}', defaulting to 'general'")
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
    
    def get_category_description(self, category: str) -> str:
        """Get description for a category"""
        return self.categories.get(category, "General iPad information")
