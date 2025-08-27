from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
from tool_contracts import ToolType

class IntentCategory(Enum):
    """Categories of user intents."""
    REPOSITORY_MANAGEMENT = "repository_management"
    BRANCH_OPERATIONS = "branch_operations"
    FILE_OPERATIONS = "file_operations"
    COMMIT_OPERATIONS = "commit_operations"
    GITHUB_API_OPERATIONS = "github_api_operations"
    CONFIGURATION = "configuration"
    QUERY = "query"

class ToolIntent(BaseModel):
    """Represents a tool intent with its configuration."""
    intent_name: str
    category: IntentCategory
    description: str
    endpoint: str
    method: str
    tool_type: ToolType
    parameters: List[Dict[str, Any]]
    requires_auth: bool = True
    suggested_next_tools: Optional[List[Dict[str, Any]]] = None
    examples: List[str] = []

# Define all intents for the GitHub automation tool
INTENT_CLASSIFICATIONS = {
    # Repository Management
    "create_repository": ToolIntent(
        intent_name="create_repository",
        category=IntentCategory.REPOSITORY_MANAGEMENT,
        description="Create a new GitHub repository both locally and remotely",
        endpoint="/github/create-repo",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_name", "type": "string", "required": True},
            {"name": "private", "type": "boolean", "default": True},
            {"name": "description", "type": "string", "required": False}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.CREATOR,
                "toolNameHint": "initialize_repository",
                "reason": "Initialize the repository locally after creation"
            },
            {
                "toolType": ToolType.CREATOR,
                "toolNameHint": "add_gitignore",
                "reason": "Add a .gitignore file to the repository"
            }
        ],
        examples=[
            "Create a new repository called my-project",
            "Make a private GitHub repo named test-app",
            "Set up a new public repository for documentation"
        ]
    ),
    
    "initialize_repository": ToolIntent(
        intent_name="initialize_repository",
        category=IntentCategory.REPOSITORY_MANAGEMENT,
        description="Initialize a local Git repository",
        endpoint="/repos/init",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.CREATOR,
                "toolNameHint": "create_branch",
                "reason": "Create initial branches for development"
            }
        ],
        examples=[
            "Initialize git in the current directory",
            "Set up git tracking for my project",
            "Create a local git repository"
        ]
    ),
    
    "clone_repository": ToolIntent(
        intent_name="clone_repository",
        category=IntentCategory.REPOSITORY_MANAGEMENT,
        description="Clone a repository from GitHub",
        endpoint="/repos/clone",
        method="POST",
        tool_type=ToolType.RETRIEVER,
        parameters=[
            {"name": "repo_url", "type": "string", "required": True},
            {"name": "local_path", "type": "string", "required": True}
        ],
        requires_auth=False,
        suggested_next_tools=[
            {
                "toolType": ToolType.ANALYZER,
                "toolNameHint": "list_branches",
                "reason": "View available branches in the cloned repository"
            }
        ],
        examples=[
            "Clone the repository from https://github.com/user/repo",
            "Download a copy of the project repository",
            "Get the code from GitHub"
        ]
    ),
    
    # Branch Operations
    "create_branch": ToolIntent(
        intent_name="create_branch",
        category=IntentCategory.BRANCH_OPERATIONS,
        description="Create a new branch in the repository",
        endpoint="/repos/create-branch",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "branch_name", "type": "string", "required": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.MODIFIER,
                "toolNameHint": "add_files",
                "reason": "Add files to the new branch"
            }
        ],
        examples=[
            "Create a feature branch called feature/new-login",
            "Make a new branch for bug fixes",
            "Create development branch"
        ]
    ),
    
    "list_branches": ToolIntent(
        intent_name="list_branches",
        category=IntentCategory.BRANCH_OPERATIONS,
        description="List all branches in a repository",
        endpoint="/github/list-branches/{repo_name}",
        method="GET",
        tool_type=ToolType.RETRIEVER,
        parameters=[
            {"name": "repo_name", "type": "string", "required": True}
        ],
        examples=[
            "Show all branches in my repository",
            "List available branches",
            "What branches exist in the project?"
        ]
    ),
    
    "merge_branches": ToolIntent(
        intent_name="merge_branches",
        category=IntentCategory.BRANCH_OPERATIONS,
        description="Merge one branch into another",
        endpoint="/repos/merge",
        method="POST",
        tool_type=ToolType.MODIFIER,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "source_branch", "type": "string", "required": True},
            {"name": "target_branch", "type": "string", "default": "main"}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "push_changes",
                "reason": "Push the merged changes to remote"
            }
        ],
        examples=[
            "Merge feature branch into main",
            "Combine development branch with master",
            "Integrate changes from bugfix branch"
        ]
    ),
    
    # File Operations
    "add_file": ToolIntent(
        intent_name="add_file",
        category=IntentCategory.FILE_OPERATIONS,
        description="Add a single file to the repository",
        endpoint="/repos/add-file",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "file_name", "type": "string", "required": True},
            {"name": "content", "type": "string", "required": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "commit_changes",
                "reason": "Commit the added file"
            }
        ],
        examples=[
            "Add README.md file to the repository",
            "Create a new Python script",
            "Add configuration file"
        ]
    ),
    
    "add_multiple_files": ToolIntent(
        intent_name="add_multiple_files",
        category=IntentCategory.FILE_OPERATIONS,
        description="Add multiple files to the repository at once",
        endpoint="/repos/add-files",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "files", "type": "array", "required": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "commit_changes",
                "reason": "Commit all added files"
            }
        ],
        examples=[
            "Add multiple source files to the project",
            "Upload batch of configuration files",
            "Add all documentation files"
        ]
    ),
    
    "list_files": ToolIntent(
        intent_name="list_files",
        category=IntentCategory.FILE_OPERATIONS,
        description="List files in a directory",
        endpoint="/repos/list-files/{repo_path}",
        method="GET",
        tool_type=ToolType.RETRIEVER,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True}
        ],
        examples=[
            "Show all files in the repository",
            "List directory contents",
            "What files are in the project?"
        ]
    ),
    
    "read_file": ToolIntent(
        intent_name="read_file",
        category=IntentCategory.FILE_OPERATIONS,
        description="Read the contents of a file",
        endpoint="/repos/read-file/{repo_path}/{file_name}",
        method="GET",
        tool_type=ToolType.RETRIEVER,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "file_name", "type": "string", "required": True}
        ],
        examples=[
            "Show the contents of README.md",
            "Read the configuration file",
            "Display the source code"
        ]
    ),
    
    # Commit Operations
    "commit_changes": ToolIntent(
        intent_name="commit_changes",
        category=IntentCategory.COMMIT_OPERATIONS,
        description="Stage and commit changes",
        endpoint="/repos/commit",
        method="POST",
        tool_type=ToolType.EXECUTOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "commit_message", "type": "string", "required": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "push_changes",
                "reason": "Push committed changes to remote"
            }
        ],
        examples=[
            "Commit changes with message 'Added new feature'",
            "Save current changes",
            "Create a commit for bug fixes"
        ]
    ),
    
    "push_changes": ToolIntent(
        intent_name="push_changes",
        category=IntentCategory.COMMIT_OPERATIONS,
        description="Push changes to remote repository",
        endpoint="/repos/push",
        method="POST",
        tool_type=ToolType.EXECUTOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "remote_name", "type": "string", "default": "origin"},
            {"name": "branch", "type": "string", "required": False}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.CREATOR,
                "toolNameHint": "create_pull_request",
                "reason": "Create a pull request for the pushed changes"
            }
        ],
        examples=[
            "Push changes to GitHub",
            "Upload commits to remote",
            "Sync with origin"
        ]
    ),
    
    "stage_all_changes": ToolIntent(
        intent_name="stage_all_changes",
        category=IntentCategory.COMMIT_OPERATIONS,
        description="Stage all changes for commit",
        endpoint="/repos/add-all",
        method="POST",
        tool_type=ToolType.MODIFIER,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "include_untracked", "type": "boolean", "default": True}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "commit_changes",
                "reason": "Commit the staged changes"
            }
        ],
        examples=[
            "Stage all modified files",
            "Add all changes for commit",
            "Prepare files for commit"
        ]
    ),
    
    # GitHub API Operations
    "create_issue": ToolIntent(
        intent_name="create_issue",
        category=IntentCategory.GITHUB_API_OPERATIONS,
        description="Create an issue on GitHub",
        endpoint="/github/create-issue",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_name", "type": "string", "required": True},
            {"name": "title", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": False},
            {"name": "labels", "type": "array", "required": False}
        ],
        examples=[
            "Create a bug report issue",
            "Open a new feature request",
            "Report a problem in the repository"
        ]
    ),
    
    "create_pull_request": ToolIntent(
        intent_name="create_pull_request",
        category=IntentCategory.GITHUB_API_OPERATIONS,
        description="Create a pull request",
        endpoint="/github/create-pr",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "branch_name", "type": "string", "required": True},
            {"name": "title", "type": "string", "required": False},
            {"name": "body", "type": "string", "required": False}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.RETRIEVER,
                "toolNameHint": "list_pull_requests",
                "reason": "View the created pull request"
            }
        ],
        examples=[
            "Create a PR for feature branch",
            "Open pull request for review",
            "Submit changes for merge"
        ]
    ),
    
    "list_repositories": ToolIntent(
        intent_name="list_repositories",
        category=IntentCategory.GITHUB_API_OPERATIONS,
        description="List user's GitHub repositories",
        endpoint="/github/list-repos",
        method="GET",
        tool_type=ToolType.RETRIEVER,
        parameters=[
            {"name": "page", "type": "integer", "default": 1},
            {"name": "per_page", "type": "integer", "default": 30}
        ],
        examples=[
            "Show my GitHub repositories",
            "List all my repos",
            "What repositories do I have?"
        ]
    ),
    
    # Configuration
    "setup_credentials": ToolIntent(
        intent_name="setup_credentials",
        category=IntentCategory.CONFIGURATION,
        description="Set up GitHub credentials",
        endpoint="/auth/setup",
        method="POST",
        tool_type=ToolType.MODIFIER,
        parameters=[
            {"name": "username", "type": "string", "required": True},
            {"name": "token", "type": "string", "required": True}
        ],
        requires_auth=False,
        examples=[
            "Configure GitHub access",
            "Set up authentication",
            "Add GitHub credentials"
        ]
    ),
    
    "generate_gitignore": ToolIntent(
        intent_name="generate_gitignore",
        category=IntentCategory.FILE_OPERATIONS,
        description="Generate a .gitignore file",
        endpoint="/repos/generate-gitignore",
        method="POST",
        tool_type=ToolType.CREATOR,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True},
            {"name": "project_type", "type": "string", "required": False}
        ],
        suggested_next_tools=[
            {
                "toolType": ToolType.EXECUTOR,
                "toolNameHint": "commit_changes",
                "reason": "Commit the generated .gitignore file"
            }
        ],
        examples=[
            "Create gitignore for Python project",
            "Add gitignore file",
            "Generate ignore file for Node.js"
        ]
    ),
    
    # Query Operations
    "check_status": ToolIntent(
        intent_name="check_status",
        category=IntentCategory.QUERY,
        description="Check repository status",
        endpoint="/repos/status/{repo_path}",
        method="GET",
        tool_type=ToolType.ANALYZER,
        parameters=[
            {"name": "repo_path", "type": "string", "required": True}
        ],
        examples=[
            "Show git status",
            "Check repository changes",
            "What's the current status?"
        ]
    )
}

class IntentClassifier:
    """Classifier to match user intents to tool configurations."""
    
    @staticmethod
    def classify_intent(user_query: str) -> Optional[ToolIntent]:
        """
        Classify user intent based on the query.
        This is a simple keyword-based classifier.
        In production, you might use NLP or ML models.
        """
        query_lower = user_query.lower()
        
        # Keywords mapping
        keyword_intent_map = {
            # Repository management
            ("create", "repository", "repo"): "create_repository",
            ("create", "github", "repo"): "create_repository",
            ("initialize", "git"): "initialize_repository",
            ("init", "repo"): "initialize_repository",
            ("clone", "repository"): "clone_repository",
            ("clone", "github"): "clone_repository",
            
            # Branch operations
            ("create", "branch"): "create_branch",
            ("new", "branch"): "create_branch",
            ("list", "branch"): "list_branches",
            ("show", "branch"): "list_branches",
            ("merge", "branch"): "merge_branches",
            ("merge", "into"): "merge_branches",
            
            # File operations
            ("add", "file"): "add_file",
            ("create", "file"): "add_file",
            ("add", "multiple", "files"): "add_multiple_files",
            ("add", "files"): "add_multiple_files",
            ("list", "files"): "list_files",
            ("show", "files"): "list_files",
            ("read", "file"): "read_file",
            ("show", "content"): "read_file",
            ("gitignore"): "generate_gitignore",
            
            # Commit operations
            ("commit", "change"): "commit_changes",
            ("commit", "message"): "commit_changes",
            ("push", "change"): "push_changes",
            ("push", "github"): "push_changes",
            ("stage", "all"): "stage_all_changes",
            ("add", "all"): "stage_all_changes",
            
            # GitHub API operations
            ("create", "issue"): "create_issue",
            ("open", "issue"): "create_issue",
            ("create", "pull", "request"): "create_pull_request",
            ("create", "pr"): "create_pull_request",
            ("list", "repo"): "list_repositories",
            ("show", "repo"): "list_repositories",
            
            # Configuration
            ("setup", "credential"): "setup_credentials",
            ("configure", "github"): "setup_credentials",
            ("set", "credential"): "setup_credentials",
            
            # Query
            ("status"): "check_status",
            ("git", "status"): "check_status"
        }
        
        # Find matching intent
        for keywords, intent_name in keyword_intent_map.items():
            if all(keyword in query_lower for keyword in keywords):
                return INTENT_CLASSIFICATIONS.get(intent_name)
        
        return None
    
    @staticmethod
    def get_intent_by_name(intent_name: str) -> Optional[ToolIntent]:
        """Get intent configuration by name."""
        return INTENT_CLASSIFICATIONS.get(intent_name)
    
    @staticmethod
    def get_intents_by_category(category: IntentCategory) -> List[ToolIntent]:
        """Get all intents in a specific category."""
        return [
            intent for intent in INTENT_CLASSIFICATIONS.values()
            if intent.category == category
        ]
    
    @staticmethod
    def get_all_intents() -> Dict[str, ToolIntent]:
        """Get all available intents."""
        return INTENT_CLASSIFICATIONS