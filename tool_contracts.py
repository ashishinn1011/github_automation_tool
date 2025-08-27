from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json
import uuid

class ToolType(Enum):
    """Tool types for the agentic system."""
    CREATOR = 0
    ANALYZER = 1
    MODIFIER = 2
    RETRIEVER = 3
    VALIDATOR = 4
    EXECUTOR = 5
    REPORTER = 6

class ToolExecutionStatus(Enum):
    """Status of tool execution."""
    Processing = "Processing"
    Complete = "Complete"
    Failed = "Failed"

class UserContextInfo(BaseModel):
    """User context information."""
    userId: str = Field(default="", description="User ID")
    sessionId: str = Field(default="", description="Session ID")

class ContentSummary(BaseModel):
    """Summary of content in the payload."""
    fields: List[str] = Field(default_factory=list, description="List of fields in the content")
    recordCount: int = Field(default=0, description="Number of records")

class SuggestedToolReference(BaseModel):
    """Reference to a suggested tool for follow-up processing."""
    toolType: ToolType = Field(..., description="Type of the tool")
    toolNameHint: Optional[str] = Field(None, description="Hint for the tool name")
    reason: Optional[str] = Field(None, description="Reason for suggesting this tool")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters to pass to the tool")
    outputLabel: Optional[str] = Field(None, description="Label for the output")

class ToolMetadata(BaseModel):
    """Metadata about the tool execution."""
    dataType: str = Field(default="application/json", description="Type of data")
    dataSize: int = Field(default=0, description="Size of the data")
    intent: str = Field(..., description="Intent of the tool execution")
    description: str = Field(..., description="Description of what was done")
    accessibility: str = Field(default="public", description="Accessibility level")
    requiresPostProcessing: bool = Field(default=False, description="Whether post-processing is required")
    suggestedTools: List[SuggestedToolReference] = Field(default_factory=list, description="Suggested follow-up tools")
    contentSummary: Optional[ContentSummary] = Field(None, description="Summary of the content")
    confidence: float = Field(default=1.0, description="Confidence level")

class ToolResult(BaseModel):
    """Result of a tool execution."""
    toolResultId: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for this result")
    toolName: str = Field(..., description="Name of the tool")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of execution")
    conversationId: Optional[str] = Field(default=None, description="Conversation ID")
    conversationMessageId: Optional[str] = Field(default=None, description="Message ID in the conversation")
    userContext: Optional[UserContextInfo] = Field(default=None, description="User context")
    metadata: ToolMetadata = Field(..., description="Metadata about the execution")
    payload: Any = Field(..., description="The actual result payload")
    stepIndex: int = Field(default=0, description="Step index in a multi-step process")
    parentToolResultId: Optional[str] = Field(None, description="Parent tool result ID if this is a sub-step")

    @property
    def status(self) -> ToolExecutionStatus:
        """Get the execution status."""
        return ToolExecutionStatus.Processing if self.metadata.requiresPostProcessing else ToolExecutionStatus.Complete

    def to_json(self, indent: bool = False) -> str:
        """Convert to JSON string."""
        return self.model_dump_json(indent=2 if indent else None, exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> 'ToolResult':
        """Create from JSON string."""
        return cls.model_validate_json(json_str)

    def set_user_context(self, user_id: str, session_id: str, conversation_id: str, message_id: str):
        """Set user context information."""
        self.userContext.userId = user_id
        self.userContext.sessionId = session_id
        self.conversationId = conversation_id
        self.conversationMessageId = message_id

    def to_llm_context_summary(self) -> str:
        """Create a summary for LLM context."""
        summary = {
            "toolName": self.toolName,
            "dataType": self.metadata.dataType,
            "intent": self.metadata.intent,
            "description": self.metadata.description,
            "fields": self.metadata.contentSummary.fields if self.metadata.contentSummary else [],
            "records": self.metadata.contentSummary.recordCount if self.metadata.contentSummary else 0,
            "suggestedTools": [t.toolType.name for t in self.metadata.suggestedTools]
        }
        return json.dumps(summary, separators=(',', ':'))

def build_tool_result(
    tool_name: str,
    payload: Any,
    intent: str,
    description: str,
    conversation_id: str = "",
    message_id: str = "",
    user_id: str = "",
    session_id: str = "",
    source: str = "api",
    data_type: str = "application/json",
    requires_post_processing: bool = False,
    suggestedTools: Optional[List[Dict[str, Any]]] = None,
    content_summary: Optional[Dict[str, Any]] = None,
    parent_tool_result_id: Optional[str] = None,
    step_index: int = 0
) -> ToolResult:
    """Helper function to build a ToolResult object."""
    
    # Convert suggested tools if provided
    suggested_tool_refs = []
    if suggestedTools:
        for tool in suggestedTools:
            suggested_tool_refs.append(SuggestedToolReference(
                toolType=tool.get("toolType", ToolType.ANALYZER),
                toolNameHint=tool.get("toolNameHint"),
                reason=tool.get("reason"),
                parameters=tool.get("parameters"),
                outputLabel=tool.get("outputLabel")
            ))
    
    # Create content summary if provided
    content_summary_obj = None
    if content_summary:
        content_summary_obj = ContentSummary(
            fields=content_summary.get("fields", []),
            recordCount=content_summary.get("recordCount", 0)
        )
    
    # Calculate data size
    data_size = len(json.dumps(payload)) if payload else 0
    
    # Create metadata
    metadata = ToolMetadata(
        dataType=data_type,
        dataSize=data_size,
        intent=intent,
        description=description,
        accessibility="public",
        requiresPostProcessing=requires_post_processing,
        suggestedTools=suggested_tool_refs,
        contentSummary=content_summary_obj,
        confidence=1.0
    )
    
    # Create user context
    user_context = UserContextInfo(
        userId=user_id,
        sessionId=session_id
    )
    
    # Create and return ToolResult
    return ToolResult(
        toolName=tool_name,
        conversationId=conversation_id,
        conversationMessageId=message_id,
        userContext=user_context,
        metadata=metadata,
        payload=payload,
        stepIndex=step_index,
        parentToolResultId=parent_tool_result_id
    )