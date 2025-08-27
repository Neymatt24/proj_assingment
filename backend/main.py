# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import logging
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from chatbot.ipad_agent import iPadChatbotAgent
from utils.logger import setup_logger

# Setup logging
logger = setup_logger("fastapi_main")

# Global agent instance
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global agent
    try:
        # Check if GROQ_API_KEY is loaded
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            logger.error("GROQ_API_KEY not found in environment variables")
            logger.error("Please check your .env file and ensure it's in the correct location")
            agent = None
        else:
            logger.info(f"GROQ_API_KEY found: {groq_key[:10]}...")  # Show first 10 chars for verification
            agent = iPadChatbotAgent()
            await agent.initialize()
            logger.info("iPad Chatbot Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        agent = None
    
    yield
    
    # Shutdown
    if agent and hasattr(agent, 'web_search') and agent.web_search:
        await agent.web_search.close()
    logger.info("Shutting down...")

app = FastAPI(
    title="iPad Chatbot API",
    description="A comprehensive iPad assistant API using ChatGroq and LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatMessage(BaseModel):
    message: str
    user_id: str = "anonymous"

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    query_type: str
    metadata: Dict[str, Any] = {}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    agent_status = "healthy" if agent else "not_initialized"
    groq_key_status = "present" if os.getenv("GROQ_API_KEY") else "missing"
    
    return {
        "status": "healthy",
        "agent_status": agent_status,
        "groq_key_status": groq_key_status,
        "message": "iPad Chatbot API is running"
    }

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Main chat endpoint for iPad queries"""
    if not agent:
        raise HTTPException(
            status_code=503, 
            detail="Agent not initialized. Please check server logs and ensure GROQ_API_KEY is set."
        )
    
    try:
        result = await agent.process_query(message.message, message.user_id)
        
        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            query_type=result["query_type"],
            metadata=result["metadata"]
        )
    
    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

# iPad models endpoint
@app.get("/ipad/models")
async def get_ipad_models():
    """Get current iPad models"""
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    try:
        models = await agent.get_current_models()
        return {"models": models}
    
    except Exception as e:
        logger.error(f"Failed to get iPad models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get models: {str(e)}"
        )

# iPad pricing endpoint
@app.get("/ipad/pricing")
async def get_ipad_pricing():
    """Get current iPad pricing"""
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    try:
        pricing = await agent.get_pricing_info()
        return {"pricing": pricing}
    
    except Exception as e:
        logger.error(f"Failed to get iPad pricing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pricing: {str(e)}"
        )

# Query classification endpoint
@app.post("/classify")
async def classify_query(message: ChatMessage):
    """Classify the type of iPad query"""
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    try:
        query_type = await agent.query_classifier.classify(message.message)
        return {"query_type": query_type}
    
    except Exception as e:
        logger.error(f"Query classification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
