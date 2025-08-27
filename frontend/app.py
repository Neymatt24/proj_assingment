# frontend/app.py
import streamlit as st
import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import uuid

# Configure page
st.set_page_config(
    page_title="iPad Assistant",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Minimal CSS for clean look
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stChatMessage {
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .stChatMessage[data-testid="chatMessage-user"] {
        background-color: #f0f2f6;
        border-left: 3px solid #007AFF;
    }
    
    .stChatMessage[data-testid="chatMessage-assistant"] {
        background-color: #ffffff;
        border-left: 3px solid #34C759;
        border: 1px solid #e1e5e9;
    }
    
    .session-info {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #666;
    }
    
    .query-type {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        background: #007AFF;
        color: white;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

class iPadAssistant:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if "session_id" not in st.session_state:
            st.session_state.session_id = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "api_connected" not in st.session_state:
            st.session_state.api_connected = False
        if "current_session_info" not in st.session_state:
            st.session_state.current_session_info = None
    
    def check_api_connection(self) -> bool:
        """Check if backend API is accessible"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=3)
            st.session_state.api_connected = response.status_code == 200
            return st.session_state.api_connected
        except:
            st.session_state.api_connected = False
            return False
    
    def create_new_session(self) -> Optional[str]:
        """Create a new conversation session"""
        try:
            response = requests.post(f"{self.api_base_url}/session/create", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data["session_id"]
        except Exception as e:
            st.error(f"Failed to create session: {e}")
        return None
    
    def load_session_history(self, session_id: str) -> bool:
        """Load conversation history from backend"""
        try:
            response = requests.get(f"{self.api_base_url}/session/{session_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                st.session_state.messages = []
                
                for msg in data["messages"]:
                    st.session_state.messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "query_type": msg.get("query_type"),
                        "sources": msg.get("sources", [])
                    })
                
                st.session_state.current_session_info = {
                    "created_at": data["created_at"],
                    "message_count": data["message_count"]
                }
                return True
        except Exception as e:
            st.error(f"Failed to load session: {e}")
        return False
    
    def send_message(self, message: str) -> Dict:
        """Send message to backend"""
        try:
            payload = {
                "message": message,
                "session_id": st.session_state.session_id
            }
            
            response = requests.post(
                f"{self.api_base_url}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Update session_id if it was created
                if not st.session_state.session_id:
                    st.session_state.session_id = data["session_id"]
                return data
            else:
                return {
                    "response": f"Error: {response.status_code}. Please try again.",
                    "sources": [],
                    "query_type": "error",
                    "session_id": st.session_state.session_id
                }
        except Exception as e:
            return {
                "response": f"Connection error: {str(e)}. Is the backend running?",
                "sources": [],
                "query_type": "error",
                "session_id": st.session_state.session_id
            }
    
    def get_active_sessions(self) -> List[Dict]:
        """Get list of active sessions"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions", timeout=5)
            if response.status_code == 200:
                return response.json()["sessions"]
        except:
            pass
        return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            response = requests.delete(f"{self.api_base_url}/session/{session_id}", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def render_header(self):
        """Render minimal header"""
        st.title("🍎 iPad Assistant")
        st.caption("Ask anything about Apple iPads")
        
        # API Status indicator
        if self.check_api_connection():
            st.success("✅ Connected", icon="🟢")
        else:
            st.error("❌ Backend offline - Start the FastAPI server", icon="🔴")
            st.stop()
    
    def render_session_manager(self):
        """Render session management section"""
        st.subheader("💬 Session Management")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Current session info
            if st.session_state.session_id:
                session_info = st.session_state.current_session_info
                if session_info:
                    created = datetime.fromisoformat(session_info["created_at"]).strftime("%H:%M")
                    st.markdown(f"""
                    <div class="session-info">
                        <strong>Active Session:</strong> {st.session_state.session_id[:8]}...<br>
                        <strong>Started:</strong> {created} | <strong>Messages:</strong> {len(st.session_state.messages)}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="session-info">
                        <strong>Session:</strong> {st.session_state.session_id[:8]}... (New session)
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No active session")
        
        with col2:
            if st.button("🆕 New Session", help="Start a new conversation"):
                new_session_id = self.create_new_session()
                if new_session_id:
                    st.session_state.session_id = new_session_id
                    st.session_state.messages = []
                    st.session_state.current_session_info = None
                    st.rerun()
        
        with col3:
            if st.button("🗑️ Clear Chat", help="Clear current conversation"):
                st.session_state.messages = []
                if st.session_state.session_id:
                    self.delete_session(st.session_state.session_id)
                    st.session_state.session_id = None
                st.session_state.current_session_info = None
                st.rerun()
    
    def render_session_list(self):
        """Render expandable session list"""
        sessions = self.get_active_sessions()
        
        if sessions:
            with st.expander(f"📋 Active Sessions ({len(sessions)})", expanded=False):
                for session in sessions:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        session_id_short = session["session_id"][:8]
                        created_time = datetime.fromisoformat(session["created_at"]).strftime("%m/%d %H:%M")
                        st.text(f"{session_id_short}... | {created_time} | {session['message_count']} msgs")
                    
                    with col2:
                        if st.button("Load", key=f"load_{session['session_id']}", help="Load this session"):
                            if self.load_session_history(session["session_id"]):
                                st.session_state.session_id = session["session_id"]
                                st.rerun()
                    
                    with col3:
                        if st.button("🗑️", key=f"delete_{session['session_id']}", help="Delete session"):
                            if self.delete_session(session["session_id"]):
                                if st.session_state.session_id == session["session_id"]:
                                    st.session_state.session_id = None
                                    st.session_state.messages = []
                                st.rerun()
    
    def render_chat_interface(self):
        """Render main chat interface"""
        st.subheader("💭 Chat")
        
        # Chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant" and message.get("query_type"):
                    st.markdown(f'<div class="query-type">{message["query_type"].upper()}</div>', 
                               unsafe_allow_html=True)
                
                st.write(message["content"])
                
                # Show sources for assistant messages
                if message["role"] == "assistant" and message.get("sources"):
                    sources = [s for s in message["sources"] if s and s.startswith('http')][:3]
                    if sources:
                        st.caption("🔗 Sources:")
                        for i, source in enumerate(sources, 1):
                            domain = source.split('/')[2] if len(source.split('/')) > 2 else source
                            st.caption(f"{i}. [{domain}]({source})")
        
        # Chat input
        if prompt := st.chat_input("Ask about iPads..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get assistant response
            with st.chat_message("assistant"):
                with st.spinner("🔍 Searching for latest information..."):
                    response_data = self.send_message(prompt)
                
                # Display query type badge
                query_type = response_data.get("query_type", "general")
                st.markdown(f'<div class="query-type">{query_type.upper()}</div>', 
                           unsafe_allow_html=True)
                
                # Display response
                st.write(response_data["response"])
                
                # Display sources
                sources = [s for s in response_data.get("sources", []) if s and s.startswith('http')][:3]
                if sources:
                    st.caption("🔗 Sources:")
                    for i, source in enumerate(sources, 1):
                        domain = source.split('/')[2] if len(source.split('/')) > 2 else source
                        st.caption(f"{i}. [{domain}]({source})")
                
                # Add assistant message to session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_data["response"],
                    "query_type": query_type,
                    "sources": response_data.get("sources", [])
                })
                
                # Update session info
                if not st.session_state.current_session_info:
                    st.session_state.current_session_info = {
                        "created_at": datetime.now().isoformat(),
                        "message_count": len(st.session_state.messages)
                    }
    
    def render_quick_examples(self):
        """Render quick example buttons"""
        st.subheader("💡 Quick Examples")
        
        examples = [
            "What's the difference between iPad Pro and iPad Air?",
            "iPad Pro M2 current price",
            "iPad won't charge troubleshooting",
            "Latest iPad models 2024",
            "iPad Air specifications",
            "Apple Pencil compatibility"
        ]
        
        # Display examples in 2 columns
        col1, col2 = st.columns(2)
        
        for i, example in enumerate(examples):
            col = col1 if i % 2 == 0 else col2
            
            with col:
                if st.button(example, key=f"example_{i}", help="Click to ask this question"):
                    # Add user message
                    st.session_state.messages.append({"role": "user", "content": example})
                    
                    # Get response
                    response_data = self.send_message(example)
                    
                    # Add assistant message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_data["response"],
                        "query_type": response_data.get("query_type", "general"),
                        "sources": response_data.get("sources", [])
                    })
                    
                    st.rerun()
    
    def run(self):
        """Main application runner"""
        self.render_header()
        
        # Show session management
        self.render_session_manager()
        
        # Show session list
        self.render_session_list()
        
        # Main chat interface
        if st.session_state.messages:
            self.render_chat_interface()
        else:
            # Show welcome message and examples
            st.info("👋 Welcome! Ask me anything about Apple iPads. I'll search for the latest information to help you.")
            self.render_quick_examples()
        
        # Always show chat input at bottom
        if not st.session_state.messages:
            st.subheader("💭 Start Chatting")
            if prompt := st.chat_input("Ask about iPads..."):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Get response
                with st.spinner("🔍 Searching for latest information..."):
                    response_data = self.send_message(prompt)
                
                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_data["response"],
                    "query_type": response_data.get("query_type", "general"),
                    "sources": response_data.get("sources", [])
                })
                
                st.rerun()

# Run the app
if __name__ == "__main__":
    app = iPadAssistant()
    app.run()
