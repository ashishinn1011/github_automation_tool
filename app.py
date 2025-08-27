from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import git
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load .env from same directory as app.py
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

# Import local git operations
from git_operations import (
    init_local_repo, create_branch as create_local_branch, add_and_commit, 
    push_changes, merge_branch, repo_status, generate_gitignore, 
    download_github_gitignore, list_directory_contents, read_file_contents, 
    format_response, detect_project_type, add_file_with_content, 
    add_multiple_files, add_all_changes, clone_repository, ensure_main_branch
)

# Import GitHub API operations with clear naming
from github_api import (
    create_github_repo, list_repositories, list_branches, create_issue,
    list_pull_requests, create_pull_request as create_github_pr,
    create_branch as create_github_branch
)

from tool_contracts import ToolResult, ToolType, build_tool_result
from intent_classification import IntentClassifier, IntentCategory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fastapi_server')

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Automation API",
    description="REST API for automating Git and GitHub operations",
    version="1.0.0"
)

config = get_config()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models - Updated to handle both local and GitHub operations
class RepoCreate(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")
    private: bool = Field(True, description="Whether the repository is private")
    description: Optional[str] = Field(None, description="Repository description")

class LocalBranchCreate(BaseModel):
    repo_path: str = Field(..., description="Path to the local repository")
    branch_name: str = Field(..., description="Name of the branch to create")

class GitHubBranchCreate(BaseModel):
    repo_name: str = Field(..., description="Name of the GitHub repository")
    branch_name: str = Field(..., description="Name of the branch to create")
    from_branch: str = Field("main", description="Branch to create from")

class CommitRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    commit_message: str = Field(..., description="Commit message")

class PushRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    remote_name: str = Field("origin", description="Remote name")
    branch: Optional[str] = Field(None, description="Branch name")

class FileRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    file_name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")

class MergeRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field("main", description="Target branch name")

class GitHubPRRequest(BaseModel):
    repo_name: str = Field(..., description="GitHub repository name")
    head: str = Field(..., description="Branch with changes")
    base: str = Field("main", description="Target branch")
    title: str = Field(..., description="PR title")
    body: Optional[str] = Field(None, description="PR description")

class GitignoreRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    project_type: Optional[str] = Field(None, description="Project type")

class IssueRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue description")
    labels: Optional[List[str]] = Field(None, description="Issue labels")

class Credentials(BaseModel):
    username: str
    token: str

class RepoInitRequest(BaseModel):
    repo_path: str = Field(..., description="Path to initialize the repository")

class FileContent(BaseModel):
    path: str = Field(..., json_schema_extra={"description": "Relative path of the file", "example": "src/main.py"})
    content: str = Field(..., json_schema_extra={"description": "File content", "example": "print('Hello')"})

class BatchFileRequest(BaseModel):
    repo_path: str = Field(..., json_schema_extra={"description": "Path to the repository", "example": "./bundle"})
    files: List[FileContent] = Field(..., description="List of files to add")

class CloneRequest(BaseModel):
    repo_url: str = Field(..., json_schema_extra={"description": "URL of the repository", "example": "https://github.com/username/repo.git"})
    local_path: str = Field(..., json_schema_extra={"description": "Path to clone the repository", "example": "./cloned-repo"})

class AddAllRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    include_untracked: bool = Field(
        True, 
        description="Whether to include untracked files (git add -A when True, git add . when False)"
    )

# Helper function to check credentials
def check_credentials():
    """Check if GitHub credentials are set."""
    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    
    if not username or not token:
        logger.error("GitHub credentials not set. Please use the /auth/setup endpoint first.")
        raise HTTPException(
            status_code=401, 
            detail="GitHub credentials not set. Please use the /auth/setup endpoint first."
        )
    return username, token

# Helper function to get request IDs from headers
def get_request_ids(
    conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
    message_id: Optional[str] = Header(None, alias="X-Message-ID"),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, str]:
    """Extract request IDs from headers."""
    return {
        "conversation_id": conversation_id or "",
        "message_id": message_id or "",
        "user_id": user_id or "",
        "session_id": session_id or ""
    }

# Root endpoint
@app.get("/")
async def root():
    return format_response(True, "GitHub Automation API is running")

@app.get("/intents", summary="Get all available intents")
async def get_all_intents():
    """Get all available intents and their configurations."""
    intents = IntentClassifier.get_all_intents()
    return {
        "success": True,
        "intents": {
            name: {
                "category": intent.category.value,
                "description": intent.description,
                "endpoint": intent.endpoint,
                "method": intent.method,
                "parameters": intent.parameters,
                "examples": intent.examples
            }
            for name, intent in intents.items()
        }
    }

@app.post("/classify-intent", summary="Classify user intent")
async def classify_intent(query: Dict[str, str]):
    """Classify user intent from natural language query."""
    user_query = query.get("query", "")
    intent = IntentClassifier.classify_intent(user_query)
    
    if intent:
        return {
            "success": True,
            "intent": intent.intent_name,
            "category": intent.category.value,
            "endpoint": intent.endpoint,
            "method": intent.method,
            "parameters": intent.parameters
        }
    else:
        return {
            "success": False,
            "message": "Could not classify intent",
            "suggestions": list(IntentClassifier.get_all_intents().keys())
        }

@app.post("/auth/setup", summary="Set up GitHub credentials")
async def setup_credentials(credentials: Credentials, ids: Dict = Depends(get_request_ids)):
    try:
        # Set for current process
        os.environ["GITHUB_USERNAME"] = credentials.username
        os.environ["GITHUB_TOKEN"] = credentials.token
        
        # Write to .env file
        with open(env_path, "w") as f:
            f.write(f"GITHUB_USERNAME={credentials.username}\n")
            f.write(f"GITHUB_TOKEN={credentials.token}\n")
        
        return build_tool_result(
            tool_name="setup_credentials",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={"env_path": str(env_path), "username": credentials.username},
            intent="Set up GitHub credentials",
            description="GitHub credentials saved successfully",
            data_type="application/json",
            requires_post_processing=False
        )
    except Exception as e:
        logger.error(f"Error setting up credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/verify", summary="Verify credentials")
async def verify_credentials(conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                           message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                           user_id: Optional[str] = Header(None, alias="X-User-ID"),
                           session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    username = os.getenv("GITHUB_USERNAME", "")
    token_exists = bool(os.getenv("GITHUB_TOKEN", ""))
    
    logger.info(f"Verifying credentials: Username exists: {bool(username)}, Token exists: {token_exists}")
    
    return build_tool_result(
        tool_name="verify_credentials",
        conversation_id=conversation_id or "",
        message_id=message_id or "",
        user_id=user_id or "",
        session_id=session_id or "",
        payload={
            "username": username,
            "token_exists": token_exists,
            "configured": bool(username) and token_exists
        },
        intent="Verify credentials",
        description="Credentials verification complete",
        data_type="application/json",
        requires_post_processing=not (bool(username) and token_exists),
        suggestedTools=[
            {
                "toolType": ToolType.MODIFIER,
                "toolNameHint": "setup_credentials",
                "reason": "Set up GitHub credentials to use the API",
                "parameters": {}
            }
        ] if not (bool(username) and token_exists) else []
    )

@app.post("/repos/init", summary="Initialize a local Git repository")
async def initialize_repo(request: RepoInitRequest, ids: Dict = Depends(get_request_ids)):
    try:
        repo = init_local_repo(request.repo_path)
        ensure_main_branch(request.repo_path)
        
        return build_tool_result(
            tool_name="initialize_repository",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={"repo_path": request.repo_path, "branch": "main"},
            intent="Initialize repository",
            description=f"Repository initialized at {request.repo_path}",
            data_type="application/json",
            requires_post_processing=False,
            suggestedTools=[
                {
                    "toolType": ToolType.CREATOR,
                    "toolNameHint": "create_branch",
                    "reason": "Create branches for development",
                    "parameters": {"repo_path": request.repo_path}
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# FIXED: Separate endpoints for local and GitHub branch creation
@app.post("/repos/create-branch", summary="Create a new local branch")
async def create_new_local_branch(request: LocalBranchCreate, ids: Dict = Depends(get_request_ids)):
    try:
        result = create_local_branch(request.repo_path, request.branch_name)
        
        return build_tool_result(
            tool_name="create_local_branch",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={"branch_name": request.branch_name, "message": result},
            intent="Create local branch",
            description=f"Created branch '{request.branch_name}' in local repository",
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.MODIFIER,
                    "toolNameHint": "add_files",
                    "reason": "Add files to the new branch",
                    "parameters": {"repo_path": request.repo_path}
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error creating local branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/github/create-branch", summary="Create a new GitHub branch")
async def create_new_github_branch(request: GitHubBranchCreate, ids: Dict = Depends(get_request_ids)):
    try:
        check_credentials()
        result = create_github_branch(request.repo_name, request.branch_name, request.from_branch)
        
        return build_tool_result(
            tool_name="create_github_branch",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload=result,
            intent="Create GitHub branch",
            description=f"Created branch '{request.branch_name}' on GitHub",
            data_type="application/json",
            requires_post_processing=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating GitHub branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File operations remain the same as they're local operations
@app.post("/repos/add-file", summary="Add a file with content to repository")
async def add_file(request: FileRequest, ids: Dict = Depends(get_request_ids)):
    try:
        result = add_file_with_content(
            request.repo_path,
            request.file_name,
            request.content
        )
        
        return build_tool_result(
            tool_name="add_file",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "file_name": request.file_name,
                "file_path": f"{request.repo_path}/{request.file_name}",
                "content_length": len(request.content)
            },
            intent="Add file",
            description=result,
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "commit_changes",
                    "reason": "Commit the added file",
                    "parameters": {
                        "repo_path": request.repo_path,
                        "commit_message": f"Add {request.file_name}"
                    }
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/add-all", summary="Stage all changes (git add -A or git add .)")
async def add_all_changes_endpoint(request: AddAllRequest, ids: Dict = Depends(get_request_ids)):
    try:
        result = add_all_changes(request.repo_path, request.include_untracked)
        
        return build_tool_result(
            tool_name="stage_all_changes",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload=result,
            intent="Stage all changes",
            description=result["message"],
            data_type="application/json",
            requires_post_processing=True,
            content_summary={
                "fields": ["file_path", "status"],
                "recordCount": len(result["staged_files"])
            },
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "commit_changes",
                    "reason": "Commit the staged changes",
                    "parameters": {"repo_path": request.repo_path}
                }
            ] if result["staged_files"] else []
        )
    except Exception as e:
        logger.error(f"Error adding changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/commit", summary="Stage and commit changes")
async def commit_changes(request: CommitRequest, ids: Dict = Depends(get_request_ids)):
    try:
        result = add_and_commit(request.repo_path, request.commit_message)
        
        return build_tool_result(
            tool_name="commit_changes",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "committed": result,
                "commit_message": request.commit_message
            },
            intent="Commit changes",
            description=f"Changes committed with message: {request.commit_message}" if result else "No changes to commit",
            data_type="application/json",
            requires_post_processing=result,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "push_changes",
                    "reason": "Push committed changes to remote",
                    "parameters": {"repo_path": request.repo_path}
                }
            ] if result else []
        )
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/push", summary="Push changes to remote")
async def push_to_remote(request: PushRequest, ids: Dict = Depends(get_request_ids)):
    try:
        success = push_changes(request.repo_path, request.remote_name, request.branch)
        
        return build_tool_result(
            tool_name="push_changes",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "pushed": success,
                "remote": request.remote_name,
                "branch": request.branch or "current"
            },
            intent="Push changes",
            description="Pushed changes successfully" if success else "Push failed",
            data_type="application/json",
            requires_post_processing=success,
            suggestedTools=[
                {
                    "toolType": ToolType.CREATOR,
                    "toolNameHint": "create_pull_request",
                    "reason": "Create a pull request for the pushed changes",
                    "parameters": {
                        "repo_path": request.repo_path,
                        "branch_name": request.branch
                    }
                }
            ] if success and request.branch and request.branch != "main" else []
        )
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/merge", summary="Merge branches locally")
async def merge(request: MergeRequest, ids: Dict = Depends(get_request_ids)):
    try:
        result = merge_branch(request.repo_path, request.source_branch, request.target_branch)
        
        return build_tool_result(
            tool_name="merge_branches",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "merged": result,
                "source_branch": request.source_branch,
                "target_branch": request.target_branch
            },
            intent="Merge branches",
            description=f"Merged {request.source_branch} into {request.target_branch} successfully" if result else "Merge failed due to conflicts",
            data_type="application/json",
            requires_post_processing=result,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "push_changes",
                    "reason": "Push the merged changes",
                    "parameters": {
                        "repo_path": request.repo_path,
                        "branch": request.target_branch
                    }
                }
            ] if result else []
        )
    except Exception as e:
        logger.error(f"Error merging branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/clone", summary="Clone a repository")
async def clone_repo(request: CloneRequest, ids: Dict = Depends(get_request_ids)):
    try:
        result = clone_repository(request.repo_url, request.local_path)
        
        return build_tool_result(
            tool_name="clone_repository",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "repo_url": request.repo_url,
                "local_path": request.local_path,
                "branch": result["branch"]
            },
            intent="Clone repository",
            description=f"Cloned repository to {request.local_path}",
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.ANALYZER,
                    "toolNameHint": "list_branches",
                    "reason": "View available branches in the cloned repository",
                    "parameters": {"repo_path": request.local_path}
                },
                {
                    "toolType": ToolType.RETRIEVER,
                    "toolNameHint": "list_files",
                    "reason": "Explore the repository contents",
                    "parameters": {"repo_path": request.local_path}
                }
            ]
        )
    except git.GitCommandError as e:
        raise HTTPException(status_code=400, detail=f"Clone failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/status/{repo_path:path}", summary="Get repository status")
async def get_status(repo_path: str, 
                    conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                    message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                    user_id: Optional[str] = Header(None, alias="X-User-ID"),
                    session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        status = repo_status(repo_path)
        
        # Parse status to extract useful information
        lines = status.split('\n')
        has_changes = any('modified:' in line or 'new file:' in line for line in lines)
        
        return build_tool_result(
            tool_name="check_status",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"status": status, "has_changes": has_changes},
            intent="Check repository status",
            description="Repository status retrieved",
            data_type="text/plain",
            requires_post_processing=has_changes,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "commit_changes",
                    "reason": "Commit the uncommitted changes",
                    "parameters": {"repo_path": repo_path}
                }
            ] if has_changes else []
        )
    except Exception as e:
        logger.error(f"Error getting repository status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/generate-gitignore", summary="Generate gitignore file")
async def generate(request: GitignoreRequest, ids: Dict = Depends(get_request_ids)):
    try:
        path = generate_gitignore(request.repo_path)
        
        return build_tool_result(
            tool_name="generate_gitignore",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={"gitignore_path": path},
            intent="Generate gitignore",
            description=f"Gitignore file generated at {path}",
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "commit_changes",
                    "reason": "Commit the generated .gitignore file",
                    "parameters": {
                        "repo_path": request.repo_path,
                        "commit_message": "Add .gitignore"
                    }
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error generating gitignore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/download-gitignore", summary="Download GitHub gitignore template")
async def download_gitignore_endpoint(request: GitignoreRequest, ids: Dict = Depends(get_request_ids)):
    try:
        path = download_github_gitignore(request.repo_path, request.project_type)
        
        return build_tool_result(
            tool_name="download_gitignore",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload={
                "gitignore_path": path,
                "project_type": request.project_type or "auto-detected"
            },
            intent="Download gitignore template",
            description=f"GitHub gitignore template downloaded to {path}",
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "commit_changes",
                    "reason": "Commit the downloaded .gitignore file",
                    "parameters": {
                        "repo_path": request.repo_path,
                        "commit_message": f"Add GitHub {request.project_type or 'auto-detected'} .gitignore"
                    }
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error downloading gitignore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/detect-project-type/{repo_path:path}", summary="Detect project type")
async def detect_type(repo_path: str,
                     conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                     message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                     user_id: Optional[str] = Header(None, alias="X-User-ID"),
                     session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        project_types = detect_project_type(repo_path)
        
        return build_tool_result(
            tool_name="detect_project_type",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"project_types": project_types},
            intent="Detect project type",
            description=f"Detected project types: {', '.join(project_types)}",
            data_type="application/json",
            requires_post_processing=True,
            suggestedTools=[
                {
                    "toolType": ToolType.CREATOR,
                    "toolNameHint": "generate_gitignore",
                    "reason": f"Generate appropriate .gitignore for {project_types[0]} project",
                    "parameters": {
                        "repo_path": repo_path,
                        "project_type": project_types[0]
                    }
                }
            ] if project_types and project_types[0] != "general" else []
        )
    except Exception as e:
        logger.error(f"Error detecting project type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/list-files/{repo_path:path}", summary="List directory contents")
async def list_files(repo_path: str,
                    conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                    message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                    user_id: Optional[str] = Header(None, alias="X-User-ID"),
                    session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        contents = list_directory_contents(repo_path)
        
        return build_tool_result(
            tool_name="list_files",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"contents": contents},
            intent="List directory contents",
            description=f"Found {len(contents)} items in {repo_path}",
            data_type="application/json",
            requires_post_processing=False,
            content_summary={
                "fields": ["filename"],
                "recordCount": len(contents)
            }
        )
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/read-file/{repo_path:path}/{file_name:path}", summary="Read file contents")
async def read_file(repo_path: str, file_name: str,
                   conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                   message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                   user_id: Optional[str] = Header(None, alias="X-User-ID"),
                   session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        contents = read_file_contents(repo_path, file_name)
        
        return build_tool_result(
            tool_name="read_file",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={
                "file_name": file_name,
                "contents": contents,
                "size": len(contents)
            },
            intent="Read file contents",
            description=f"Read {file_name} ({len(contents)} bytes)",
            data_type="text/plain",
            requires_post_processing=False
        )
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/list-repos", summary="List GitHub repositories")
async def list_repos(page: int = 1, per_page: int = 30,
                    conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                    message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                    user_id: Optional[str] = Header(None, alias="X-User-ID"),
                    session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        check_credentials()
        
        repos = list_repositories(page, per_page)
        
        return build_tool_result(
            tool_name="list_repositories",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"repositories": repos},
            intent="List repositories",
            description=f"Retrieved {len(repos)} repositories",
            data_type="application/json",
            requires_post_processing=False,
            content_summary={
                "fields": ["name", "description", "private", "html_url"],
                "recordCount": len(repos)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/list-branches/{repo_name}", summary="List branches in a repository")
async def list_repo_branches(repo_name: str,
                            conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                            message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                            user_id: Optional[str] = Header(None, alias="X-User-ID"),
                            session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        check_credentials()
        
        branches = list_branches(repo_name)
        
        return build_tool_result(
            tool_name="list_branches",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"branches": branches},
            intent="List branches",
            description=f"Retrieved {len(branches)} branches for {repo_name}",
            data_type="application/json",
            requires_post_processing=False,
            content_summary={
                "fields": ["name", "commit"],
                "recordCount": len(branches)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/github/create-issue", summary="Create an issue")
async def create_github_issue(request: IssueRequest, ids: Dict = Depends(get_request_ids)):
    try:
        check_credentials()
        
        issue = create_issue(request.repo_name, request.title, request.body, request.labels)
        
        return build_tool_result(
            tool_name="create_issue",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload=issue,
            intent="Create issue",
            description=f"Issue #{issue['number']} created in {request.repo_name}",
            data_type="application/json",
            requires_post_processing=False,
            suggestedTools=[
                {
                    "toolType": ToolType.RETRIEVER,
                    "toolNameHint": "view_issue",
                    "reason": "View the created issue",
                    "parameters": {
                        "repo_name": request.repo_name,
                        "issue_number": issue['number']
                    },
                    "outputLabel": f"Issue #{issue['number']}"
                }
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# FIXED: Using proper GitHub API for PR creation
@app.post("/github/create-pr", summary="Create a pull request")
async def create_github_pr_endpoint(request: GitHubPRRequest, ids: Dict = Depends(get_request_ids)):
    try:
        check_credentials()
        
        pr_info = create_github_pr(
            repo_name=request.repo_name,
            head=request.head,
            base=request.base,
            title=request.title,
            body=request.body
        )
        
        return build_tool_result(
            tool_name="create_pull_request",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload=pr_info,
            intent="Create pull request",
            description=f"Pull request #{pr_info['number']} created",
            data_type="application/json",
            requires_post_processing=False,
            suggestedTools=[
                {
                    "toolType": ToolType.RETRIEVER,
                    "toolNameHint": "view_pull_request",
                    "reason": "View the created pull request",
                    "parameters": {
                        "pr_url": pr_info['html_url']
                    },
                    "outputLabel": f"PR #{pr_info['number']}"
                }
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/list-prs/{repo_name}", summary="List pull requests")
async def list_prs(repo_name: str, state: str = "open",
                  conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
                  message_id: Optional[str] = Header(None, alias="X-Message-ID"),
                  user_id: Optional[str] = Header(None, alias="X-User-ID"),
                  session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    try:
        check_credentials()
        
        prs = list_pull_requests(repo_name, state)
        
        return build_tool_result(
            tool_name="list_pull_requests",
            conversation_id=conversation_id or "",
            message_id=message_id or "",
            user_id=user_id or "",
            session_id=session_id or "",
            payload={"pull_requests": prs},
            intent="List pull requests",
            description=f"Retrieved {len(prs)} {state} pull requests for {repo_name}",
            data_type="application/json",
            requires_post_processing=False,
            content_summary={
                "fields": ["number", "title", "state", "user", "created_at"],
                "recordCount": len(prs)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# FIXED: Create GitHub repository endpoint
@app.post("/github/create-repo", summary="Create a GitHub repository")
async def create_github_repository(request: RepoCreate, ids: Dict = Depends(get_request_ids)):
    try:
        check_credentials()
        
        repo_info = create_github_repo(
            repo_name=request.repo_name,
            private=request.private,
            description=request.description
        )
        
        return build_tool_result(
            tool_name="create_github_repository",
            conversation_id=ids["conversation_id"],
            message_id=ids["message_id"],
            user_id=ids["user_id"],
            session_id=ids["session_id"],
            payload=repo_info,
            intent="Create GitHub repository",
            description=f"Repository '{request.repo_name}' created on GitHub",
            data_type="application/json",
            requires_post_processing=False,
            suggestedTools=[
                {
                    "toolType": ToolType.EXECUTOR,
                    "toolNameHint": "clone_repository",
                    "reason": "Clone the repository locally",
                    "parameters": {
                        "repo_url": repo_info['clone_url'],
                        "local_path": f"./{request.repo_name}"
                    }
                }
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating GitHub repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or default to 7309
    port = int(os.getenv("PORT", os.getenv("FASTAPI_PORT", "7309")))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)