import os
import git
import requests
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('git_operations')

def format_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    """Format a standard response."""
    response = {
        "success": success,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

def init_local_repo(repo_path: str) -> git.Repo:
    """Initialize a local Git repository."""
    try:
        repo = git.Repo.init(repo_path)
        logger.info(f"Initialized Git repository at {repo_path}")
        return repo
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise

def create_branch(repo_path: str, branch_name: str) -> str:
    """Create a new branch in the LOCAL repository and check it out."""
    try:
        repo = git.Repo(repo_path)
        
        # Create and checkout the new branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        
        logger.info(f"Created and checked out branch '{branch_name}' in {repo_path}")
        return f"Branch '{branch_name}' created and checked out successfully"
        
    except git.GitCommandError as e:
        if "already exists" in str(e):
            logger.error(f"Branch '{branch_name}' already exists")
            raise ValueError(f"Branch '{branch_name}' already exists")
        else:
            logger.error(f"Git error creating branch: {e}")
            raise
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise

def ensure_main_branch(repo_path: str) -> None:
    """Ensure the repository has a 'main' branch."""
    try:
        repo = git.Repo(repo_path)
        
        # Check if repo has any commits
        try:
            repo.head.commit
        except ValueError:
            # No commits yet, create initial commit
            readme_path = os.path.join(repo_path, "README.md")
            if not os.path.exists(readme_path):
                with open(readme_path, "w") as f:
                    f.write("# New Repository\n")
            
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            
        # Ensure we're on main branch
        if "main" not in [head.name for head in repo.heads]:
            if "master" in [head.name for head in repo.heads]:
                # Rename master to main
                master = repo.heads["master"]
                repo.head.reference = master
                repo.head.reset(index=True, working_tree=True)
                master.rename("main")
            else:
                # Create main branch
                main = repo.create_head("main")
                repo.head.reference = main
        else:
            # Checkout main if it exists
            repo.heads["main"].checkout()
            
        logger.info(f"Ensured 'main' branch exists in {repo_path}")
        
    except Exception as e:
        logger.error(f"Error ensuring main branch: {e}")
        raise

def add_and_commit(repo_path: str, commit_message: str) -> bool:
    """Add all changes and commit."""
    try:
        repo = git.Repo(repo_path)
        
        # Check if there are changes to commit
        if not repo.is_dirty() and not repo.untracked_files:
            logger.info("No changes to commit")
            return False
        
        # Add all changes
        repo.git.add("-A")
        
        # Commit
        repo.index.commit(commit_message)
        logger.info(f"Committed changes with message: {commit_message}")
        return True
        
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        raise

def push_changes(repo_path: str, remote_name: str = "origin", branch: Optional[str] = None) -> bool:
    """Push changes to remote repository."""
    try:
        repo = git.Repo(repo_path)
        
        # Get current branch if not specified
        if not branch:
            branch = repo.active_branch.name
            
        # Push to remote
        origin = repo.remotes[remote_name]
        origin.push(branch)
        
        logger.info(f"Pushed changes to {remote_name}/{branch}")
        return True
        
    except git.GitCommandError as e:
        logger.error(f"Git push error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise

def merge_branch(repo_path: str, source_branch: str, target_branch: str = "main") -> bool:
    """Merge source branch into target branch."""
    try:
        repo = git.Repo(repo_path)
        
        # Save current branch
        current_branch = repo.active_branch.name
        
        # Checkout target branch
        repo.heads[target_branch].checkout()
        
        # Merge source branch
        repo.git.merge(source_branch)
        
        logger.info(f"Merged {source_branch} into {target_branch}")
        return True
        
    except git.GitCommandError as e:
        if "conflict" in str(e).lower():
            logger.error(f"Merge conflict between {source_branch} and {target_branch}")
            # Abort merge and restore original branch
            repo.git.merge("--abort")
            repo.heads[current_branch].checkout()
            return False
        else:
            logger.error(f"Git merge error: {e}")
            raise
    except Exception as e:
        logger.error(f"Error merging branches: {e}")
        raise

def repo_status(repo_path: str) -> str:
    """Get repository status."""
    try:
        repo = git.Repo(repo_path)
        return repo.git.status()
    except Exception as e:
        logger.error(f"Error getting repository status: {e}")
        raise

def generate_gitignore(repo_path: str) -> str:
    """Generate a basic .gitignore file."""
    try:
        gitignore_path = os.path.join(repo_path, ".gitignore")
        
        # Detect project type
        project_types = detect_project_type(repo_path)
        
        # Generate appropriate .gitignore content
        content = generate_gitignore_content(project_types)
        
        with open(gitignore_path, "w") as f:
            f.write(content)
            
        logger.info(f"Generated .gitignore at {gitignore_path}")
        return gitignore_path
        
    except Exception as e:
        logger.error(f"Error generating .gitignore: {e}")
        raise

def download_github_gitignore(repo_path: str, project_type: Optional[str] = None) -> str:
    """Download a .gitignore template from GitHub."""
    try:
        if not project_type:
            # Auto-detect project type
            detected_types = detect_project_type(repo_path)
            project_type = detected_types[0] if detected_types else "general"
            
        # Map common project types to GitHub template names
        template_map = {
            "python": "Python",
            "node": "Node",
            "react": "Node",
            "java": "Java",
            "csharp": "VisualStudio",
            "cpp": "C++",
            "go": "Go",
            "rust": "Rust",
            "ruby": "Ruby",
            "php": "Laravel",
            "general": "Global/macOS"
        }
        
        template_name = template_map.get(project_type.lower(), "Python")
        
        # Download from GitHub
        url = f"https://raw.githubusercontent.com/github/gitignore/main/{template_name}.gitignore"
        response = requests.get(url)
        
        if response.status_code == 200:
            gitignore_path = os.path.join(repo_path, ".gitignore")
            with open(gitignore_path, "w") as f:
                f.write(response.text)
            logger.info(f"Downloaded {template_name} .gitignore template")
            return gitignore_path
        else:
            logger.warning(f"Could not download template, generating basic .gitignore")
            return generate_gitignore(repo_path)
            
    except Exception as e:
        logger.error(f"Error downloading .gitignore: {e}")
        return generate_gitignore(repo_path)

def detect_project_type(repo_path: str) -> List[str]:
    """Detect the project type based on files in the repository."""
    project_types = []
    
    try:
        files = os.listdir(repo_path)
        
        # Python
        if any(f in files for f in ["requirements.txt", "setup.py", "Pipfile", "pyproject.toml"]):
            project_types.append("python")
            
        # Node.js
        if "package.json" in files:
            project_types.append("node")
            # Check for React
            if os.path.exists(os.path.join(repo_path, "package.json")):
                with open(os.path.join(repo_path, "package.json"), "r") as f:
                    content = f.read()
                    if "react" in content:
                        project_types.append("react")
                        
        # Java
        if "pom.xml" in files or "build.gradle" in files:
            project_types.append("java")
            
        # C#
        if any(f.endswith(".csproj") or f.endswith(".sln") for f in files):
            project_types.append("csharp")
            
        # Go
        if "go.mod" in files:
            project_types.append("go")
            
        # Rust
        if "Cargo.toml" in files:
            project_types.append("rust")
            
        # Ruby
        if "Gemfile" in files:
            project_types.append("ruby")
            
        # PHP
        if "composer.json" in files:
            project_types.append("php")
            
        if not project_types:
            project_types.append("general")
            
        return project_types
        
    except Exception as e:
        logger.error(f"Error detecting project type: {e}")
        return ["general"]

def generate_gitignore_content(project_types: List[str]) -> str:
    """Generate .gitignore content based on project types."""
    content = []
    
    # Common patterns
    content.append("# General")
    content.extend([
        ".DS_Store",
        "*.log",
        "*.tmp",
        "*.temp",
        ".env",
        ".env.*",
        "!.env.example",
        ""
    ])
    
    # Python
    if "python" in project_types:
        content.append("# Python")
        content.extend([
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "venv/",
            "env/",
            "ENV/",
            ".venv/",
            "pip-log.txt",
            "pip-delete-this-directory.txt",
            ".pytest_cache/",
            ".coverage",
            "*.egg-info/",
            "dist/",
            "build/",
            ""
        ])
        
    # Node.js
    if "node" in project_types or "react" in project_types:
        content.append("# Node.js")
        content.extend([
            "node_modules/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            ".npm",
            ".yarn-integrity",
            ""
        ])
        
    # Java
    if "java" in project_types:
        content.append("# Java")
        content.extend([
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "target/",
            ".classpath",
            ".project",
            ".settings/",
            ""
        ])
        
    # IDE
    content.append("# IDEs")
    content.extend([
        ".vscode/",
        ".idea/",
        "*.iml",
        "*.sublime-*",
        ""
    ])
    
    return "\n".join(content)

def list_directory_contents(repo_path: str) -> List[str]:
    """List the contents of a directory."""
    try:
        return os.listdir(repo_path)
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}")
        raise

def read_file_contents(repo_path: str, file_name: str) -> str:
    """Read the contents of a file."""
    try:
        file_path = os.path.join(repo_path, file_name)
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise

def add_file_with_content(repo_path: str, file_name: str, content: str) -> str:
    """Create a file with specified content."""
    try:
        file_path = os.path.join(repo_path, file_name)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w") as f:
            f.write(content)
            
        logger.info(f"Created file: {file_path}")
        return f"File '{file_name}' created successfully"
        
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise

def add_multiple_files(repo_path: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
    """Add multiple files to the repository."""
    created_files = []
    errors = []
    
    for file_info in files:
        try:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not file_path:
                errors.append("File path is required")
                continue
                
            result = add_file_with_content(repo_path, file_path, content)
            created_files.append(file_path)
            
        except Exception as e:
            errors.append(f"Error creating {file_path}: {str(e)}")
            
    return {
        "success": len(errors) == 0,
        "created_files": created_files,
        "errors": errors,
        "message": f"Created {len(created_files)} files" if len(errors) == 0 else f"Created {len(created_files)} files with {len(errors)} errors"
    }

def add_all_changes(repo_path: str, include_untracked: bool = True) -> Dict[str, Any]:
    """Stage all changes in the repository."""
    try:
        repo = git.Repo(repo_path)
        
        # Get current status
        changed_files = []
        
        # Modified and deleted files
        for item in repo.index.diff(None):
            changed_files.append({
                "file_path": item.a_path,
                "status": "modified" if item.change_type == "M" else "deleted"
            })
            
        # Untracked files
        if include_untracked:
            for file_path in repo.untracked_files:
                changed_files.append({
                    "file_path": file_path,
                    "status": "new"
                })
                
        # Stage changes
        if include_untracked:
            repo.git.add("-A")  # Stage all changes including untracked
        else:
            repo.git.add(".")   # Stage only tracked files
            
        return {
            "success": True,
            "staged_files": changed_files,
            "message": f"Staged {len(changed_files)} files"
        }
        
    except Exception as e:
        logger.error(f"Error staging changes: {e}")
        raise

def clone_repository(repo_url: str, local_path: str) -> Dict[str, Any]:
    """Clone a repository from URL to local path."""
    try:
        # Normalize the local path
        local_path = os.path.normpath(local_path)
        if os.path.exists(local_path):
            raise ValueError(f"Target path '{local_path}' already exists")
            
        logger.info(f"Cloning from {repo_url} to {local_path}")
        repo = git.Repo.clone_from(repo_url, local_path)
        
        logger.info(f"Repository cloned successfully to {local_path}")
        
        return {
            "success": True,
            "message": f"Cloned to {local_path}",
            "branch": repo.active_branch.name
        }
        
    except git.GitCommandError as e:
        logger.error(f"Git clone error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise

# Remove or comment out any GitHub API related functions that might be here
# They should be in github_api.py instead