# frontend/app.py
import streamlit as st
import requests
import json
import time
from typing import Dict, List
from datetime import datetime
import uuid

# Configure page
st.set_page_config(
    page_title="iPad Assistant",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #007AFF, #5856D6);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #007AFF;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #007AFF;
    }
    
    .bot-message {
        background-color: #ffffff;
        border-left-color: #34C759;
        border: 1px solid #e1e5e9;
    }
    
    .source-link {
        font-size: 0.8rem;
        color: #007AFF;
        text-decoration: none;
    }
    
    .query-type-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        background-color: #007AFF;
        color: white;
        border-radius: 15px;
        font-size: 0.7rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-section {
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class iPadChatbotUI:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"  # FastAPI backend URL
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
        if "api_status" not in st.session_state:
            st.session_state.api_status = None
    
    def check_api_status(self):
        """Check if the backend API is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                st.session_state.api_status = "healthy"
                return True
        except requests.exceptions.RequestException:
            st.session_state.api_status = "offline"
            return False
        return False
    
    def send_message(self, message: str) -> Dict:
        """Send message to the backend API"""
        try:
            payload = {
                "message": message,
                "user_id": st.session_state.user_id
            }
            
            response = requests.post(
                f"{self.api_base_url}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "response": f"Sorry, I encountered an error (Status: {response.status_code}). Please try again.",
                    "sources": [],
                    "query_type": "error"
                }
        except requests.exceptions.RequestException as e:
            return {
                "response": f"Sorry, I couldn't connect to the server. Please check if the backend is running. Error: {str(e)}",
                "sources": [],
                "query_type": "error"
            }
    
    def render_header(self):
        """Render the main header"""
        st.markdown("""
        <div class="main-header">
            <h1>🍎 iPad Assistant</h1>
            <p>Your comprehensive guide to Apple iPads - Ask anything!</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with additional information"""
        with st.sidebar:
            st.header("📱 iPad Assistant")
            
            # API Status
            if self.check_api_status():
                st.success("✅ Connected to backend")
            else:
                st.error("❌ Backend offline")
                st.info("Make sure to start the FastAPI backend server first!")
            
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.subheader("🎯 What can I help with?")
            
            query_examples = {
                "📊 Specifications": [
                    "iPad Pro M2 specifications",
                    "iPad Air display size",
                    "iPad mini processor details"
                ],
                "💰 Pricing": [
                    "iPad Pro 12.9 inch price",
                    "Cheapest iPad model cost",
                    "iPad Air pricing options"
                ],
                "⚖️ Comparisons": [
                    "iPad Pro vs iPad Air differences",
                    "iPad mini vs regular iPad",
                    "Which iPad should I buy?"
                ],
                "🔧 Troubleshooting": [
                    "iPad won't charge",
                    "iPad screen not responding",
                    "How to reset iPad"
                ],
                "✨ Features": [
                    "iPad Pro Apple Pencil features",
                    "iPadOS 17 new features",
                    "iPad multitasking capabilities"
                ]
            }
            
            for category, examples in query_examples.items():
                st.markdown(f"**{category}**")
                for example in examples:
                    if st.button(example, key=f"example_{example}"):
                        st.session_state.example_query = example
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Quick Actions
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.subheader("🚀 Quick Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🆕 Current Models", help="Get latest iPad models"):
                    st.session_state.quick_action = "current_models"
            
            with col2:
                if st.button("💵 Pricing Info", help="Get pricing information"):
                    st.session_state.quick_action = "pricing_info"
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Statistics
            if st.session_state.messages:
                st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
                st.subheader("📈 Session Stats")
                st.metric("Total Messages", len(st.session_state.messages))
                
                # Query types count
                query_types = [msg.get("query_type", "unknown") for msg in st.session_state.messages if msg.get("type") == "assistant"]
                if query_types:
                    from collections import Counter
                    type_counts = Counter(query_types)
                    st.write("Query Types:")
                    for qtype, count in type_counts.most_common():
                        st.write(f"• {qtype.title()}: {count}")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    def render_message(self, message: Dict, is_user: bool = True):
        """Render a single message"""
        if is_user:
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🧑‍💻 You:</strong><br>
                {message['content']}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Query type badge
            query_type = message.get('query_type', 'general')
            
            st.markdown(f"""
            <div class="chat-message bot-message">
                <div class="query-type-badge">{query_type.upper()}</div>
                <strong>🤖 iPad Assistant:</strong><br>
                {message['content']}
            </div>
            """, unsafe_allow_html=True)
            
            # Show sources if available
            sources = message.get('sources', [])
            if sources:
                st.markdown("**📚 Sources:**")
                for i, source in enumerate(sources[:3], 1):
                    if source and source.startswith('http'):
                        st.markdown(f"{i}. [{source}]({source})")
    
    def handle_quick_actions(self):
        """Handle quick action buttons"""
        if hasattr(st.session_state, 'quick_action'):
            action = st.session_state.quick_action
            
            if action == "current_models":
                try:
                    response = requests.get(f"{self.api_base_url}/ipad/models", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        models_info = "Here are the current iPad models:\n\n"
                        for model in data.get("models", []):
                            models_info += f"• **{model.get('title', 'Unknown Model')}**\n"
                            models_info += f"  {model.get('summary', 'No description available')}\n\n"
                        
                        # Add to chat
                        st.session_state.messages.append({
                            "type": "assistant",
                            "content": models_info,
                            "sources": [m.get('url', '') for m in data.get("models", [])],
                            "query_type": "specifications",
                            "timestamp": datetime.now().isoformat()
                        })
                except:
                    st.error("Failed to fetch current models")
            
            elif action == "pricing_info":
                try:
                    response = requests.get(f"{self.api_base_url}/ipad/pricing", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        pricing_info = "Here's the current iPad pricing information:\n\n"
                        for source in data.get("pricing", {}).get("sources", []):
                            pricing_info += f"• **{source.get('title', 'Pricing Info')}**\n"
                            pricing_info += f"  {source.get('snippet', 'No details available')}\n\n"
                        
                        # Add to chat
                        st.session_state.messages.append({
                            "type": "assistant",
                            "content": pricing_info,
                            "sources": [s.get('url', '') for s in data.get("pricing", {}).get("sources", [])],
                            "query_type": "pricing",
                            "timestamp": datetime.now().isoformat()
                        })
                except:
                    st.error("Failed to fetch pricing information")
            
            # Clear the action
            del st.session_state.quick_action
            st.rerun()
    
    def handle_example_query(self):
        """Handle example query selection"""
        if hasattr(st.session_state, 'example_query'):
            query = st.session_state.example_query
            
            # Add user message
            st.session_state.messages.append({
                "type": "user",
                "content": query,
                "timestamp": datetime.now().isoformat()
            })
            
            # Get bot response
            with st.spinner("🤔 Thinking..."):
                response = self.send_message(query)
            
            # Add bot message
            st.session_state.messages.append({
                "type": "assistant",
                "content": response["response"],
                "sources": response.get("sources", []),
                "query_type": response.get("query_type", "general"),
                "timestamp": datetime.now().isoformat()
            })
            
            # Clear the example query
            del st.session_state.example_query
            st.rerun()
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Handle quick actions
        self.handle_quick_actions()
        
        # Handle example queries
        self.handle_example_query()
        
        # Chat history
        if st.session_state.messages:
            st.subheader("💬 Chat History")
            
            for message in st.session_state.messages:
                self.render_message(message, is_user=(message["type"] == "user"))
        else:
            st.info("👋 Welcome! Ask me anything about Apple iPads. Try the example questions in the sidebar or type your own question below.")
        
        # Chat input
        st.subheader("✍️ Ask your question")
        
        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_input(
                    "Your question about iPads:",
                    placeholder="e.g., What's the difference between iPad Pro and iPad Air?",
                    label_visibility="collapsed"
                )
            
            with col2:
                submit_button = st.form_submit_button("Send 🚀")
            
            if submit_button and user_input:
                # Add user message
                st.session_state.messages.append({
                    "type": "user",
                    "content": user_input,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Show thinking spinner
                with st.spinner("🤔 Searching for the latest information..."):
                    response = self.send_message(user_input)
                
                # Add assistant message
                st.session_state.messages.append({
                    "type": "assistant",
                    "content": response["response"],
                    "sources": response.get("sources", []),
                    "query_type": response.get("query_type", "general"),
                    "timestamp": datetime.now().isoformat()
                })
                
                st.rerun()
        
        # Clear chat button
        if st.session_state.messages:
            if st.button("🗑️ Clear Chat History", type="secondary"):
                st.session_state.messages = []
                st.rerun()
    
    def run(self):
        """Main application entry point"""
        self.render_header()
        self.render_sidebar()
        self.render_chat_interface()

# Main execution
if __name__ == "__main__":
    app = iPadChatbotUI()
    app.run()