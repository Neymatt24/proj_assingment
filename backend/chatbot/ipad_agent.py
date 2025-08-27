# backend/chatbot/ipad_agent.py
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from typing import TypedDict, Annotated, List, Dict, Any, Literal
import operator
import asyncio
import re
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.web_search import WebSearchTool
from utils.query_classifier import QueryClassifier
from utils.response_generator import ResponseGenerator
from utils.logger import setup_logger

logger = setup_logger("ipad_agent")

class AgentState(TypedDict):
    query: str
    user_id: str
    query_type: str
    search_results: List[Dict]
    processed_info: Dict
    response: str
    sources: List[str]
    error: str
    metadata: Dict

class iPadChatbotAgent:
    def __init__(self):
        self.llm = None
        self.web_search = None
        self.query_classifier = None
        self.response_generator = None
        self.workflow = None
        
    async def initialize(self):
        """Initialize all components"""
        try:
            # Check for required environment variables
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("GROQ_API_KEY environment variable is required")
                logger.error("Please ensure your .env file contains: GROQ_API_KEY=your_key_here")
                raise ValueError("GROQ_API_KEY environment variable is required")
            
            logger.info(f"Found GROQ_API_KEY: {groq_api_key[:10]}...")
            
            # Initialize ChatGroq LLM
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                api_key=groq_api_key
            )
            
            # Test the LLM connection
            test_result = await self.llm.ainvoke([{"role": "user", "content": "Hello"}])
            logger.info("LLM connection test successful")
            
            # Initialize tools
            self.web_search = WebSearchTool()
            self.query_classifier = QueryClassifier(self.llm)
            self.response_generator = ResponseGenerator(self.llm)
            
            # Build the workflow graph
            self._build_workflow()
            
            logger.info("iPad Chatbot Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    def _build_workflow(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify_query", self._classify_query)
        workflow.add_node("search_web", self._search_web)
        workflow.add_node("process_information", self._process_information)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define the flow - updated for newer LangGraph
        workflow.add_edge(START, "classify_query")
        workflow.add_edge("classify_query", "search_web")
        workflow.add_edge("search_web", "process_information")
        workflow.add_edge("process_information", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "classify_query",
            self._should_handle_error,
            {
                "continue": "search_web",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "search_web",
            self._should_handle_error,
            {
                "continue": "process_information",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "process_information",
            self._should_handle_error,
            {
                "continue": "generate_response",
                "error": "handle_error"
            }
        )
        
        self.workflow = workflow.compile()
    
    async def _classify_query(self, state: AgentState) -> AgentState:
        """Classify the type of iPad query"""
        try:
            query_type = await self.query_classifier.classify(state["query"])
            state["query_type"] = query_type
            state["metadata"] = {"classification_time": datetime.now().isoformat()}
            logger.info(f"Query classified as: {query_type}")
            return state
        except Exception as e:
            state["error"] = f"Classification error: {str(e)}"
            logger.error(f"Classification error: {str(e)}")
            return state
    
    async def _search_web(self, state: AgentState) -> AgentState:
        """Search for relevant iPad information"""
        try:
            search_queries = self._generate_search_queries(state["query"], state["query_type"])
            search_results = []
            
            for query in search_queries:
                results = await self.web_search.search(query)
                search_results.extend(results)
            
            state["search_results"] = search_results
            logger.info(f"Found {len(search_results)} search results")
            return state
            
        except Exception as e:
            state["error"] = f"Search error: {str(e)}"
            logger.error(f"Search error: {str(e)}")
            return state
    
    async def _process_information(self, state: AgentState) -> AgentState:
        """Process and filter the search results"""
        try:
            processed_info = await self._extract_relevant_info(
                state["search_results"], 
                state["query"], 
                state["query_type"]
            )
            
            state["processed_info"] = processed_info
            state["sources"] = [result.get("url", "") for result in state["search_results"][:5]]
            
            return state
            
        except Exception as e:
            state["error"] = f"Processing error: {str(e)}"
            logger.error(f"Processing error: {str(e)}")
            return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """Generate the final response using ChatGroq"""
        try:
            response = await self.response_generator.generate(
                query=state["query"],
                query_type=state["query_type"],
                processed_info=state["processed_info"],
                sources=state["sources"]
            )
            
            state["response"] = response
            logger.info("Response generated successfully")
            return state
            
        except Exception as e:
            state["error"] = f"Response generation error: {str(e)}"
            logger.error(f"Response generation error: {str(e)}")
            return state
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """Handle errors gracefully"""
        error_msg = state.get("error", "Unknown error occurred")
        state["response"] = f"I apologize, but I encountered an issue: {error_msg}. Please try rephrasing your question about iPads."
        logger.error(f"Error handled: {error_msg}")
        return state
    
    def _should_handle_error(self, state: AgentState) -> Literal["continue", "error"]:
        """Determine if we should handle an error"""
        return "error" if state.get("error") else "continue"
    
    def _generate_search_queries(self, query: str, query_type: str) -> List[str]:
        """Generate targeted search queries based on query type"""
        base_query = f"Apple iPad {query}"
        
        search_queries = [base_query]
        
        if query_type == "specifications":
            search_queries.extend([
                f"Apple iPad {query} specs technical specifications",
                f"iPad {query} features processor display"
            ])
        elif query_type == "pricing":
            search_queries.extend([
                f"Apple iPad {query} price cost",
                f"iPad {query} pricing Apple Store"
            ])
        elif query_type == "comparison":
            search_queries.extend([
                f"Apple iPad {query} comparison vs",
                f"iPad {query} differences compare"
            ])
        elif query_type == "troubleshooting":
            search_queries.extend([
                f"iPad {query} troubleshooting fix problem",
                f"iPad {query} support help"
            ])
        elif query_type == "availability":
            search_queries.extend([
                f"Apple iPad {query} availability in stock",
                f"iPad {query} release date available"
            ])
        
        return search_queries[:3]  # Limit to 3 queries to avoid rate limits
    
    async def _extract_relevant_info(self, search_results: List[Dict], query: str, query_type: str) -> Dict:
        """Extract and organize relevant information from search results"""
        relevant_info = {
            "key_facts": [],
            "specifications": {},
            "pricing": {},
            "features": [],
            "troubleshooting": [],
            "comparisons": []
        }
        
        for result in search_results[:10]:  # Process top 10 results
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            
            # Extract key information based on query type
            if "price" in content or "cost" in content or "$" in content:
                price_info = self._extract_pricing(result)
                if price_info:
                    relevant_info["pricing"].update(price_info)
            
            if any(spec in content for spec in ["processor", "display", "storage", "ram", "battery"]):
                spec_info = self._extract_specifications(result)
                if spec_info:
                    relevant_info["specifications"].update(spec_info)
        
        return relevant_info
    
    def _extract_pricing(self, result: Dict) -> Dict:
        """Extract pricing information from search result"""
        content = result.get("content", "")
        pricing = {}
        
        # Look for price patterns like $299, $599, etc.
        price_pattern = r'\$(\d{1,4}(?:,\d{3})*)'
        prices = re.findall(price_pattern, content)
        
        if prices:
            pricing["prices_found"] = [f"${price}" for price in prices]
            pricing["source"] = result.get("title", "")
        
        return pricing
    
    def _extract_specifications(self, result: Dict) -> Dict:
        """Extract specifications from search result"""
        content = result.get("content", "")
        specs = {}
        
        # Extract common specifications
        if "display" in content.lower():
            specs["display_info"] = "Display information found"
        if "processor" in content.lower() or "chip" in content.lower():
            specs["processor_info"] = "Processor information found"
        
        return specs
    
    async def process_query(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """Main method to process user queries"""
        initial_state = {
            "query": query,
            "user_id": user_id,
            "query_type": "",
            "search_results": [],
            "processed_info": {},
            "response": "",
            "sources": [],
            "error": "",
            "metadata": {}
        }
        
        try:
            # Use invoke instead of ainvoke for newer versions
            final_state = await self.workflow.ainvoke(initial_state)
            
            return {
                "response": final_state["response"],
                "sources": final_state["sources"],
                "query_type": final_state["query_type"],
                "metadata": final_state["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "response": "I apologize, but I'm having trouble processing your request right now. Please try again.",
                "sources": [],
                "query_type": "error",
                "metadata": {"error": str(e)}
            }
    
    async def get_current_models(self) -> List[Dict]:
        """Get current iPad models"""
        search_results = await self.web_search.search("Apple iPad current models 2024 2025")
        return self._extract_model_info(search_results)
    
    async def get_pricing_info(self) -> Dict:
        """Get current pricing information"""
        search_results = await self.web_search.search("Apple iPad pricing cost Apple Store")
        return self._extract_pricing_info(search_results)
    
    def _extract_model_info(self, search_results: List[Dict]) -> List[Dict]:
        """Extract model information from search results"""
        models = []
        for result in search_results[:5]:
            if "ipad" in result.get("title", "").lower():
                models.append({
                    "title": result.get("title", ""),
                    "summary": result.get("content", "")[:200] + "...",
                    "url": result.get("url", "")
                })
        return models
    
    def _extract_pricing_info(self, search_results: List[Dict]) -> Dict:
        """Extract pricing information from search results"""
        pricing_info = {"sources": []}
        for result in search_results[:3]:
            pricing_info["sources"].append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("content", "")[:150] + "..."
            })
        return pricing_info
