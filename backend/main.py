# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import logging
from contextlib import asynccontextmanager
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

from chatbot.ipad_agent import iPadChatbotAgent
from utils.logger import setup_logger

# Setup logging
logger = setup_logger("fastapi_main")

# Global agent instance and session storage
agent = None
user_sessions = {}  # Store conversation history by session_id

# Session cleanup interval (24 hours)
SESSION_TIMEOUT = timedelta(hours=24)

class ConversationSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata = {}
    
    def add_message(self, role: str, content: str, query_type: str = None, sources: List[str] = None):
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "sources": sources or []
        }
        self.messages.append(message)
        self.last_activity = datetime.now()
        return message
    
    def get_conversation_context(self, last_n_messages: int = 6) -> str:
        """Get conversation context for the LLM"""
        if not self.messages:
            return ""
        
        context_messages = self.messages[-last_n_messages:] if len(self.messages) > last_n_messages else self.messages
        context = []
        
        for msg in context_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            context.append(f"{role}: {msg['content']}")
        
        return "\n".join(context)
    
    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > SESSION_TIMEOUT

def cleanup_expired_sessions():
    """Remove expired sessions"""
    global user_sessions
    expired_sessions = [sid for sid, session in user_sessions.items() if session.is_expired()]
    for sid in expired_sessions:
        del user_sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")

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
            logger.info(f"GROQ_API_KEY found: {groq_key[:10]}...")
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
    title="iPad Chatbot API with Session Management",
    description="A comprehensive iPad assistant API using ChatGroq and LangGraph with conversation history",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    query_type: str
    session_id: str
    metadata: Dict[str, Any] = {}

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    message_count: int
    metadata: Dict[str, Any] = {}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cleanup_expired_sessions()
    
    agent_status = "healthy" if agent else "not_initialized"
    groq_key_status = "present" if os.getenv("GROQ_API_KEY") else "missing"
    
    return {
        "status": "healthy",
        "agent_status": agent_status,
        "groq_key_status": groq_key_status,
        "active_sessions": len(user_sessions),
        "message": "iPad Chatbot API with session management is running"
    }

# Session management endpoints
@app.post("/session/create")
async def create_session():
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = ConversationSession(session_id)
    
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "message": "New session created successfully"
    }

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information and conversation history"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = user_sessions[session_id]
    return {
        "session_id": session_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "messages": session.messages,
        "message_count": len(session.messages)
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del user_sessions[session_id]
    return {"message": f"Session {session_id} deleted successfully"}

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    cleanup_expired_sessions()
    
    sessions = []
    for sid, session in user_sessions.items():
        sessions.append({
            "session_id": sid,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": len(session.messages)
        })
    
    return {"sessions": sessions, "total_count": len(sessions)}

# Enhanced chat endpoint with session support
@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Main chat endpoint for iPad queries with session support"""
    if not agent:
        raise HTTPException(
            status_code=503, 
            detail="Agent not initialized. Please check server logs and ensure GROQ_API_KEY is set."
        )
    
    # Handle session
    session_id = message.session_id
    if not session_id or session_id not in user_sessions:
        # Create new session if none exists
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = ConversationSession(session_id)
        logger.info(f"Created new session: {session_id}")
    
    session = user_sessions[session_id]
    
    try:
        # Add user message to session
        session.add_message("user", message.message)
        
        # Get conversation context
        conversation_context = session.get_conversation_context()
        
        # Process query with context
        result = await agent.process_query_with_context(
            query=message.message,
            conversation_context=conversation_context,
            user_id=session_id
        )
        
        # Add assistant response to session
        session.add_message(
            "assistant", 
            result["response"],
            query_type=result.get("query_type"),
            sources=result.get("sources", [])
        )
        
        return ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            query_type=result.get("query_type", "general"),
            session_id=session_id,
            metadata=result.get("metadata", {})
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
    """Get current iPad models with real search"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Force real search for current models
        search_results = await agent.web_search.search_real_time("Apple iPad models 2024 2025 current lineup specifications")
        
        models = []
        for result in search_results[:5]:
            models.append({
                "title": result.get("title", ""),
                "summary": result.get("content", "")[:300] + "...",
                "url": result.get("url", ""),
                "source": result.get("source", "web")
            })
        
        return {"models": models, "search_performed": True}
    
    except Exception as e:
        logger.error(f"Failed to get iPad models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

# iPad pricing endpoint with real search
@app.get("/ipad/pricing")
async def get_ipad_pricing():
    """Get current iPad pricing with real search"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Force real search for pricing
        search_results = await agent.web_search.search_real_time("Apple iPad pricing cost 2024 2025 Apple Store current prices")
        
        pricing_sources = []
        for result in search_results[:5]:
            pricing_sources.append({
                "title": result.get("title", ""),
                "snippet": result.get("content", "")[:250] + "...",
                "url": result.get("url", ""),
                "source": result.get("source", "web")
            })
        
        return {"pricing": {"sources": pricing_sources}, "search_performed": True}
    
    except Exception as e:
        logger.error(f"Failed to get iPad pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get pricing: {str(e)}")

# Enhanced query classification with context
@app.post("/classify")
async def classify_query(message: ChatMessage):
    """Classify the type of iPad query with context"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Get conversation context if session exists
        conversation_context = ""
        if message.session_id and message.session_id in user_sessions:
            conversation_context = user_sessions[message.session_id].get_conversation_context()
        
        query_type = await agent.query_classifier.classify_with_context(
            message.message, 
            conversation_context
        )
        
        return {
            "query_type": query_type,
            "has_context": bool(conversation_context),
            "session_id": message.session_id
        }
    
    except Exception as e:
        logger.error(f"Query classification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
