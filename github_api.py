import os
import requests
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote
import git 
from fastapi import FastAPI, Request






# --- Create FastAPI app ---
app = FastAPI(
    title="Local Command Executor API",
    description="API for executing local or remote commands with rich metadata",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('github_api')

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

def get_headers() -> Dict[str, str]:
    """Get authorization headers for GitHub API requests."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def handle_api_response(response: requests.Response) -> Any:
    """Handle API response and raise appropriate exceptions."""
    if response.status_code >= 200 and response.status_code < 300:
        return response.json()
    
    try:
        error_data = response.json()
        error_message = error_data.get('message', 'Unknown error')
    except:
        error_message = response.text or 'Unknown error'
    
    if response.status_code == 401:
        raise ValueError("Unauthorized: Check your GitHub token")
    elif response.status_code == 404:
        raise ValueError("Not found: Repository or resource doesn't exist")
    elif response.status_code == 422:
        raise ValueError(f"Validation failed: {error_message}")
    else:
        raise ValueError(f"GitHub API error ({response.status_code}): {error_message}")

def create_github_repo(repo_name: str, private: bool = True, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new GitHub repository.
    
    Args:
        repo_name: Name of the repository
        private: Whether the repository should be private
        description: Repository description
        
    Returns:
        Repository information from GitHub API
    """
    try:
        logger.info(f"Creating GitHub repository: {repo_name}")
        
        url = f"{GITHUB_API_BASE}/user/repos"
        headers = get_headers()
        
        data = {
            "name": repo_name,
            "private": private,
            "auto_init": False  # We'll initialize locally
        }
        
        if description:
            data["description"] = description
        
        response = requests.post(url, json=data, headers=headers)
        repo_info = handle_api_response(response)
        
        logger.info(f"Repository created successfully: {repo_info['html_url']}")
        return repo_info
        
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        raise

def list_repositories(page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
    """
    List user's GitHub repositories.
    
    Args:
        page: Page number for pagination
        per_page: Number of repositories per page
        
    Returns:
        List of repository information
    """
    try:
        logger.info(f"Listing repositories (page: {page}, per_page: {per_page})")
        
        url = f"{GITHUB_API_BASE}/user/repos"
        headers = get_headers()
        
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        
        response = requests.get(url, headers=headers, params=params)
        repos = handle_api_response(response)
        
        logger.info(f"Retrieved {len(repos)} repositories")
        return repos
        
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise

def list_branches(repo_name: str) -> List[Dict[str, Any]]:
    """
    List branches in a repository.
    
    Args:
        repo_name: Name of the repository
        
    Returns:
        List of branch information
    """
    try:
        logger.info(f"Listing branches for repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/branches"
        headers = get_headers()
        
        response = requests.get(url, headers=headers)
        branches = handle_api_response(response)
        
        logger.info(f"Retrieved {len(branches)} branches")
        return branches
        
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        raise

def create_issue(repo_name: str, title: str, body: Optional[str] = None, labels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create an issue in a repository.
    
    Args:
        repo_name: Name of the repository
        title: Issue title
        body: Issue body/description
        labels: List of label names as strings
        
    Returns:
        Issue information from GitHub API
    """
    try:
        logger.info(f"Creating issue in repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/issues"
        headers = get_headers()
        
        data: Dict[str, Any] = {"title": title}
        
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        #fix for label dict handling
        response = requests.post(url, json=data, headers=headers)
        issue = handle_api_response(response)
        
        logger.info(f"Issue created successfully: {issue['html_url']}")
        return issue
        
    except Exception as e:
        logger.error(f"Error creating issue: {e}")
        raise

def create_pull_request(repo_name: str, head: str, base: str, title: str, body: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a pull request.
    
    Args:
        repo_name: Name of the repository
        head: The name of the branch where your changes are implemented
        base: The name of the branch you want the changes pulled into
        title: Pull request title
        body: Pull request body/description
        
    Returns:
        Pull request information from GitHub API
    """
    try:
        logger.info(f"Creating pull request for repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/pulls"
        headers = get_headers()
        
        data = {
            "title": title,
            "head": head,
            "base": base
        }
        
        if body:
            data["body"] = body
        
        response = requests.post(url, json=data, headers=headers)
        pr = handle_api_response(response)
        
        logger.info(f"Pull request created successfully: {pr['html_url']}")
        return pr
        
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise

def list_pull_requests(repo_name: str, state: str = "open") -> List[Dict[str, Any]]:
    """
    List pull requests in a repository.
    
    Args:
        repo_name: Name of the repository
        state: State of pull requests to retrieve (open, closed, all)
        
    Returns:
        List of pull request information
    """
    try:
        logger.info(f"Listing pull requests for repository: {repo_name} (state: {state})")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/pulls"
        headers = get_headers()
        
        params = {"state": state}
        
        response = requests.get(url, headers=headers, params=params)
        prs = handle_api_response(response)
        
        logger.info(f"Retrieved {len(prs)} pull requests")
        return prs
        
    except Exception as e:
        logger.error(f"Error listing pull requests: {e}")
        raise

def get_repository_info(repo_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a repository.
    
    Args:
        repo_name: Name of the repository
        
    Returns:
        Repository information from GitHub API
    """
    try:
        logger.info(f"Getting repository info: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}"
        headers = get_headers()
        
        response = requests.get(url, headers=headers)
        repo_info = handle_api_response(response)
        
        logger.info(f"Retrieved repository info for: {repo_info['full_name']}")
        return repo_info
        
    except Exception as e:
        logger.error(f"Error getting repository info: {e}")
        raise

def delete_repository(repo_name: str) -> bool:
    """
    Delete a repository (use with caution!).
    
    Args:
        repo_name: Name of the repository to delete
        
    Returns:
        True if deletion was successful
    """
    try:
        logger.warning(f"Deleting repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}"
        headers = get_headers()
        
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 204:
            logger.info(f"Repository {repo_name} deleted successfully")
            return True
        else:
            handle_api_response(response)
            return False
            
    except Exception as e:
        logger.error(f"Error deleting repository: {e}")
        raise

def update_repository(repo_name: str, **kwargs) -> Dict[str, Any]:
    """
    Update repository settings.
    
    Args:
        repo_name: Name of the repository
        **kwargs: Repository settings to update (e.g., description, private, has_issues)
        
    Returns:
        Updated repository information
    """
    try:
        logger.info(f"Updating repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}"
        headers = get_headers()
        
        # Only include provided parameters
        data = {k: v for k, v in kwargs.items() if v is not None}
        
        response = requests.patch(url, json=data, headers=headers)
        repo_info = handle_api_response(response)
        
        logger.info(f"Repository updated successfully: {repo_info['html_url']}")
        return repo_info
        
    except Exception as e:
        logger.error(f"Error updating repository: {e}")
        raise

def clone_repository(repo_url: str, local_path: str) -> Dict[str, Any]:
    """Clone a repository from URL to local path."""
    try:
        # Normalize the local path to be relative to current directory
        local_path = os.path.normpath(local_path)
        if os.path.exists(local_path):
            raise ValueError(f"Target path '{local_path}' already exists")

        # Parse the repo URL to ensure it's valid
        if not (repo_url.startswith('http://') or repo_url.startswith('https://')):
            if '/' in repo_url:  # Assume username/repo format
                username, repo = repo_url.split('/')
                repo_url = f"https://github.com/{username}/{repo}.git"
            else:
                raise ValueError("Invalid repository URL format")
            
        logger.info(f"Cloning from {repo_url} to {local_path}")
        repo = git.Repo.clone_from(
            url=repo_url,
            to_path=local_path
        )
        
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

def create_branch(repo_name: str, branch_name: str, from_branch: str = "main") -> Dict[str, Any]:
    """
    Create a new branch in a repository.
    
    Args:
        repo_name: Name of the repository
        branch_name: Name of the new branch to create
        from_branch: Name of the branch to create from (default: main)
        
    Returns:
        Branch information from GitHub API
    """
    try:
        logger.info(f"Creating branch '{branch_name}' in repository: {repo_name}")
        
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        # First, get the SHA of the branch we're creating from
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/git/refs/heads/{from_branch}"
        headers = get_headers()
        
        response = requests.get(url, headers=headers)
        ref_data = handle_api_response(response)
        sha = ref_data["object"]["sha"]
        
        # Create the new branch
        url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        response = requests.post(url, json=data, headers=headers)
        branch_info = handle_api_response(response)
        
        logger.info(f"Branch '{branch_name}' created successfully")
        return {
            "name": branch_name,
            "sha": branch_info["object"]["sha"],
            "url": branch_info["url"]
        }
        
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise

