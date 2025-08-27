"""
Tool Execution Engine for automated tool chaining.
This module handles the execution of tool chains based on ToolResult suggestions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
import uuid
from datetime import datetime

from tool_contracts import ToolResult, ToolType, SuggestedToolReference
from intent_classification import IntentClassifier, INTENT_CLASSIFICATIONS

logger = logging.getLogger('tool_execution_engine')

class ExecutionStrategy(Enum):
    """Strategies for executing tool chains."""
    SEQUENTIAL = "sequential"  # Execute tools one by one
    PARALLEL = "parallel"      # Execute independent tools in parallel
    CONDITIONAL = "conditional" # Execute based on conditions
    INTERACTIVE = "interactive" # Ask for confirmation before each tool

class ToolExecutionContext:
    """Context for tool execution."""
    
    def __init__(self, conversation_id: str, user_id: str, session_id: str):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.session_id = session_id
        self.execution_id = f"exec-{uuid.uuid4()}"
        self.start_time = datetime.utcnow()
        self.results: List[ToolResult] = []
        self.errors: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        
    def add_result(self, result: ToolResult):
        """Add a tool result to the context."""
        self.results.append(result)
        
    def add_error(self, error: Dict[str, Any]):
        """Add an error to the context."""
        self.errors.append(error)
        
    def get_last_result(self) -> Optional[ToolResult]:
        """Get the last tool result."""
        return self.results[-1] if self.results else None
        
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution."""
        return {
            "execution_id": self.execution_id,
            "conversation_id": self.conversation_id,
            "start_time": self.start_time.isoformat(),
            "duration": (datetime.utcnow() - self.start_time).total_seconds(),
            "total_tools_executed": len(self.results),
            "errors": len(self.errors),
            "successful": len(self.errors) == 0,
            "tool_chain": [r.toolName for r in self.results]
        }

class ToolExecutor:
    """Executes individual tools based on intent and parameters."""
    
    def __init__(self, api_client: Any):
        self.api_client = api_client
        self.intent_classifier = IntentClassifier()
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                          context: ToolExecutionContext) -> Optional[ToolResult]:
        """Execute a single tool."""
        try:
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            
            # Get intent configuration
            intent = self.intent_classifier.get_intent_by_name(tool_name)
            if not intent:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Prepare headers
            headers = {
                "X-Conversation-ID": context.conversation_id,
                "X-Message-ID": f"msg-{uuid.uuid4()}",
                "X-User-ID": context.user_id,
                "X-Session-ID": context.session_id
            }
            
            # Execute API call
            response = await self.api_client.request(
                method=intent.method,
                endpoint=intent.endpoint,
                data=parameters,
                headers=headers
            )
            
            if response.status_code == 200:
                result = ToolResult.model_validate(response.json())
                context.add_result(result)
                return result
            else:
                error = {
                    "tool": tool_name,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text
                }
                context.add_error(error)
                return None
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            context.add_error({
                "tool": tool_name,
                "error": str(e),
                "type": type(e).__name__
            })
            return None

class ToolChainExecutor:
    """Executes chains of tools based on suggestions."""
    
    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor
        self.max_chain_length = 10  # Prevent infinite loops
        
    async def execute_chain(self, initial_result: ToolResult, 
                          context: ToolExecutionContext,
                          strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
                          filter_func: Optional[Callable] = None) -> List[ToolResult]:
        """Execute a chain of tools based on suggestions."""
        results = [initial_result]
        context.add_result(initial_result)
        
        current_result = initial_result
        chain_length = 0
        
        while current_result and chain_length < self.max_chain_length:
            suggested_tools = current_result.metadata.suggestedTools
            
            if not suggested_tools:
                break
                
            # Filter suggestions if filter function provided
            if filter_func:
                suggested_tools = [t for t in suggested_tools if filter_func(t)]
                
            if not suggested_tools:
                break
                
            # Execute based on strategy
            if strategy == ExecutionStrategy.SEQUENTIAL:
                next_results = await self._execute_sequential(suggested_tools, context)
            elif strategy == ExecutionStrategy.PARALLEL:
                next_results = await self._execute_parallel(suggested_tools, context)
            elif strategy == ExecutionStrategy.CONDITIONAL:
                next_results = await self._execute_conditional(suggested_tools, context)
            else:
                next_results = []
                
            if not next_results:
                break
                
            results.extend(next_results)
            current_result = next_results[-1]  # Continue from last result
            chain_length += 1
            
        return results
        
    async def _execute_sequential(self, suggested_tools: List[SuggestedToolReference], 
                                context: ToolExecutionContext) -> List[ToolResult]:
        """Execute tools sequentially."""
        results = []
        
        for suggestion in suggested_tools:
            tool_name = suggestion.toolNameHint
            if not tool_name:
                continue
            parameters = suggestion.parameters or {}
            
            result = await self.tool_executor.execute_tool(tool_name, parameters, context)
            if result:
                results.append(result)
                
                # If this tool suggests stopping the chain
                if not result.metadata.requiresPostProcessing:
                    break
                    
        return results
        
    async def _execute_parallel(self, suggested_tools: List[SuggestedToolReference], 
                              context: ToolExecutionContext) -> List[ToolResult]:
        """Execute independent tools in parallel."""
        tasks = []
        
        for suggestion in suggested_tools:
            # Only parallelize tools that don't depend on each other
            if suggestion.toolType in [ToolType.RETRIEVER, ToolType.ANALYZER] and suggestion.toolNameHint:
                task = self.tool_executor.execute_tool(
                    suggestion.toolNameHint,
                    suggestion.parameters or {},
                    context
                )
                tasks.append(task)
                
        if tasks:
            results = await asyncio.gather(*tasks)
            return [r for r in results if r is not None]
        
        return []
        
    async def _execute_conditional(self, suggested_tools: List[SuggestedToolReference], 
                                 context: ToolExecutionContext) -> List[ToolResult]:
        """Execute tools based on conditions."""
        results = []
        
        for suggestion in suggested_tools:
            # Check conditions based on tool type and previous results
            should_execute = self._evaluate_condition(suggestion, context)
            
            if should_execute and suggestion.toolNameHint:
                result = await self.tool_executor.execute_tool(
                    suggestion.toolNameHint,
                    suggestion.parameters or {},
                    context
                )
                if result:
                    results.append(result)
                    
        return results
        
    def _evaluate_condition(self, suggestion: SuggestedToolReference, 
                          context: ToolExecutionContext) -> bool:
        """Evaluate whether a tool should be executed based on conditions."""
        # Example conditions
        last_result = context.get_last_result()
        
        if not last_result:
            return True
            
        # Don't execute MODIFIER tools if the last operation failed
        if suggestion.toolType == ToolType.MODIFIER and not last_result.metadata.requiresPostProcessing:
            return False
            
        # Always execute VALIDATOR tools
        if suggestion.toolType == ToolType.VALIDATOR:
            return True
            
        # Check for specific conditions in the suggestion reason
        if suggestion.reason and "if" in suggestion.reason.lower():
            # Simple condition parsing (in production, use proper parsing)
            return True  
            
        return True

class WorkflowEngine:
    """High-level workflow engine for complex operations."""
    
    def __init__(self, chain_executor: ToolChainExecutor):
        self.chain_executor = chain_executor
        self.workflows = self._define_workflows()
        
    def _define_workflows(self) -> Dict[str, List[Dict[str, Any]]]:
        """Define common workflows."""
        return {
            "create_and_setup_repo": [
                {"tool": "create_repository", "required": True},
                {"tool": "initialize_repository", "required": True},
                {"tool": "generate_gitignore", "required": False},
                {"tool": "add_file", "params": {"file_name": "README.md"}, "required": False},
                {"tool": "commit_changes", "required": True},
                {"tool": "push_changes", "required": True}
            ],
            "feature_development": [
                {"tool": "create_branch", "required": True},
                {"tool": "add_multiple_files", "required": True},
                {"tool": "commit_changes", "required": True},
                {"tool": "push_changes", "required": True},
                {"tool": "create_pull_request", "required": True}
            ],
            "code_review": [
                {"tool": "list_pull_requests", "required": True},
                {"tool": "review_changes", "required": True},
                {"tool": "add_comments", "required": False},
                {"tool": "approve_pr", "required": True},
                {"tool": "merge_branches", "required": True}
            ]
        }
        
    async def execute_workflow(self, workflow_name: str, initial_params: Dict[str, Any],
                             context: ToolExecutionContext) -> Dict[str, Any]:
        """Execute a predefined workflow."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")
            
        workflow = self.workflows[workflow_name]
        results = []
        params = initial_params.copy()
        
        for step in workflow:
            tool_name = step["tool"]
            required = step.get("required", True)
            step_params = {**params, **step.get("params", {})}
            
            # Execute tool
            result = await self.chain_executor.tool_executor.execute_tool(
                tool_name, step_params, context
            )
            
            if result:
                results.append(result)
                # Update params with output from this step
                if result.payload:
                    params.update(result.payload)
            elif required:
                # Required step failed
                return {
                    "workflow": workflow_name,
                    "status": "failed",
                    "failed_step": tool_name,
                    "completed_steps": [r.toolName for r in results],
                    "errors": context.errors
                }
                
        return {
            "workflow": workflow_name,
            "status": "completed",
            "steps_executed": len(results),
            "results": results,
            "summary": context.get_execution_summary()
        }

class ToolOrchestrator:
    """Main orchestrator for tool execution."""
    
    def __init__(self, api_client: Any):
        self.tool_executor = ToolExecutor(api_client)
        self.chain_executor = ToolChainExecutor(self.tool_executor)
        self.workflow_engine = WorkflowEngine(self.chain_executor)
        
    async def execute_request(self, user_request: str, user_id: str,
                            conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a user request end-to-end."""
        # Create execution context
        context = ToolExecutionContext(
            conversation_id=conversation_id or f"conv-{uuid.uuid4()}",
            user_id=user_id,
            session_id=f"session-{uuid.uuid4()}"
        )
        
        # Classify intent
        intent = IntentClassifier.classify_intent(user_request)
        if not intent:
            return {
                "status": "failed",
                "error": "Could not understand request",
                "suggestions": list(INTENT_CLASSIFICATIONS.keys())
            }
            
        # Extract parameters (simplified)
        parameters = self._extract_parameters(user_request, intent)
        
        # Execute initial tool
        initial_result = await self.tool_executor.execute_tool(
            intent.intent_name, parameters, context
        )
        
        if not initial_result:
            return {
                "status": "failed",
                "error": "Initial tool execution failed",
                "context": context.get_execution_summary()
            }
            
        # Execute tool chain if needed
        if initial_result.metadata.requiresPostProcessing:
            chain_results = await self.chain_executor.execute_chain(
                initial_result, context, ExecutionStrategy.SEQUENTIAL
            )
            
        last_result = context.get_last_result()
        return {
            "status": "completed",
            "initial_tool": initial_result.toolName,
            "chain_executed": len(context.results) > 1,
            "total_tools": len(context.results),
            "execution_summary": context.get_execution_summary(),
            "final_result": last_result.model_dump() if last_result else None
        }
        
    def _extract_parameters(self, user_request: str, intent: Any) -> Dict[str, Any]:
        """Extract parameters from user request."""
        # This is a placeholder - in production, use NLP
        return {}
        
    async def execute_workflow(self, workflow_name: str, params: Dict[str, Any],
                             user_id: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a predefined workflow."""
        context = ToolExecutionContext(
            conversation_id=conversation_id or f"conv-{uuid.uuid4()}",
            user_id=user_id,
            session_id=f"session-{uuid.uuid4()}"
        )
        
        return await self.workflow_engine.execute_workflow(workflow_name, params, context)