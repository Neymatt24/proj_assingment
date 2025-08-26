# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import os
from datetime import datetime

# Import our custom modules
from chatbot.ipad_agent import iPadChatbotAgent
from utils.logger import setup_logger

# Initialize FastAPI app
app = FastAPI(
    title="iPad Chatbot API",
    description="Comprehensive iPad information chatbot using LangGraph and ChatGroq",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logger
logger = setup_logger("ipad_chatbot")

# Initialize the chatbot agent
chatbot_agent = None

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"

class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    query_type: str = ""
    timestamp: str = ""

@app.on_event("startup")
async def startup_event():
    """Initialize the chatbot agent on startup"""
    global chatbot_agent
    try:
        chatbot_agent = iPadChatbotAgent()
        await chatbot_agent.initialize()
        logger.info("iPad Chatbot Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize chatbot agent: {str(e)}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "iPad Chatbot API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_ready": chatbot_agent is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Main chat endpoint"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="Chatbot agent not initialized")
    
    try:
        logger.info(f"Received message from user {message.user_id}: {message.message}")
        
        # Process the message through LangGraph workflow
        result = await chatbot_agent.process_query(
            query=message.message,
            user_id=message.user_id
        )
        
        response = ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            query_type=result.get("query_type", "general"),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Generated response for user {message.user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/ipad/models")
async def get_ipad_models():
    """Get current iPad models information"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="Chatbot agent not initialized")
    
    try:
        models = await chatbot_agent.get_current_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching iPad models: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch iPad models")

@app.get("/ipad/pricing")
async def get_pricing_info():
    """Get current iPad pricing information"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="Chatbot agent not initialized")
    
    try:
        pricing = await chatbot_agent.get_pricing_info()
        return {"pricing": pricing}
    except Exception as e:
        logger.error(f"Error fetching pricing info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch pricing information")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)