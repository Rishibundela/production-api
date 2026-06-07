"""
Agent for handling requests and interacting with the system. This module defines the Agent class, which is responsible for processing incoming requests, managing interactions with the cache and monitoring systems, and orchestrating the overall flow of data through the application. The Agent class serves as the central point for coordinating various components of the system, ensuring that requests are handled efficiently and that relevant metrics are collected for monitoring purposes.
"""

from typing import Optional
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langsmith import traceable
from app.utils import extract_text

from app.config import get_settings

class AgentState(TypedDict):
    """
    State for the production agent
    Uses Annotated with add_messages reducer for message accumulation.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    error: Optional[str]
    retry_count: int
    model_used: str


class ProductionAgent:
    """
    Production LangGraph agent with:
    - Retry on failure (model fallback)
    - Graceful error handling
    - LangSmith tracing
    """

    def __init__(self):
        settings = get_settings()

        self.primary_llm = ChatGoogleGenerativeAI(
            model=settings.PRIMARY_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            timeout=30,
            max_retries=0
        )

        self.fallback_llm = ChatGoogleGenerativeAI(
            model=settings.FALLBACK_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            timeout=30,
            max_retries=0
        )
        self.max_retries = settings.MAX_RETRIES
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Builds the state graph for the agent."""

        def process_message(state: AgentState) -> dict:
            """Processes the incoming message using the primary LLM, with fallback on failure."""
            try:
                # Try primary model
                response = self.primary_llm.invoke(state['messages'])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": 'primary',
                }

            except Exception as e:
                
                return {
                    "error": str(e),
                    "retry_count": state['retry_count'] + 1,
                    "model_used": '',
                }
            
        def try_fallback(state: AgentState) -> dict:
            """Tries the fallback model if retries are available."""
            # if state['retry_count'] < self.max_retries:
            try:
                response = self.fallback_llm.invoke(state['messages'])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": 'fallback',
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "retry_count": state['retry_count'] + 1,
                    "model_used": '',
                }
        
        def handle_failure(state: AgentState) -> dict:
            """Handles failure after exhausting retries."""
            return {
                "messages": [
                    AIMessage(content=(
                        "Sorry, I'm having trouble processing your request right now. Please try again later."
                    ))
                ],
                "model_used": 'error_handler',
            }
        
        def route_after_processing(state: AgentState) -> str:
            """Determines the next step after processing the message."""
            if state.get("error") is None:
                return "done"
            elif state.get("retry_count", 0) < self.max_retries:
                return "fallback"
            else:
                return "error" 
        
        def route_after_fallback(state: AgentState) -> str:
            """Determines the next step after trying the fallback model."""
            if state.get("error") is None:
                return "done"
            else:
                return "error"
            
        
        # Build the state graph
        graph = StateGraph(AgentState)

        graph.add_node("process", process_message)
        graph.add_node("fallback", try_fallback)
        graph.add_node("error", handle_failure)

        graph.add_edge(START, "process")
        graph.add_conditional_edges(
            "process",
            route_after_processing,
            {
                "done": END,
                "fallback": "fallback",
                "error": "error",
            }
        )
        graph.add_conditional_edges(
            "fallback",
            route_after_fallback,
            {
                "done": END,
                "error": "error",
            }
        )

        graph.add_edge("error", END)

        return graph.compile()
    
    @traceable(name="production_agent_invoke")
    def invoke(self, message: str) -> dict:
        """
        Invokes the agent with the given messages.
        Return: {"response": str, "model_used": str, "error": Optional[str]}
        """
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "error": None,
            "retry_count": 0,
            "model_used": '',
        }
        result = self.graph.invoke(initial_state)

        if result.get("messages"):
            response_text = extract_text(result["messages"][-1])
        else:
            response_text = "No response generated"
        return {
            "response": response_text,
            "model_used": result.get("model_used", "unknown"),
            "error": result.get("error"),
        }