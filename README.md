
# GitHub Automation Tool - API Operations Guide

## Table of Contents
1. [Authentication](#authentication)
2. [Repository Management](#repository-management)
3. [File Operations](#file-operations)
4. [Git Operations](#git-operations)
5. [GitHub API Operations](#github-api-operations)
6. [Utility Operations](#utility-operations)

---

## Authentication

### 1. Setup GitHub Credentials
**Endpoint:** `POST /auth/setup`  
**Description:** Configure GitHub username and personal access token
```json
{
  "username": "your-github-username",
  "token": "ghp_your_personal_access_token"
}
```

### 2. Verify Credentials
**Endpoint:** `GET /auth/verify`  
**Description:** Check if credentials are properly configured
```
No payload required
```

---

## Repository Management

### 3. Create GitHub Repository
**Endpoint:** `POST /github/create-repo`  
**Description:** Create a new repository on GitHub
```json
{
  "repo_name": "my-awesome-project",
  "private": false,
  "description": "A fantastic new project"
}
```

### 4. Initialize Local Repository
**Endpoint:** `POST /repos/init`  
**Description:** Initialize a Git repository locally
```json
{
  "repo_path": "./my-local-repo"
}
```

### 5. Clone Repository
**Endpoint:** `POST /repos/clone`  
**Description:** Clone a GitHub repository to local machine
```json
{
  "repo_url": "https://github.com/username/repository.git",
  "local_path": "./cloned-repo"
}
```

---

## File Operations

### 6. Add Single File
**Endpoint:** `POST /repos/add-file`  
**Description:** Create a file with content in the repository
```json
{
  "repo_path": "./my-repo",
  "file_name": "src/main.py",
  "content": "print('Hello, World!')"
}
```

### 7. Add Multiple Files (Batch)
**Endpoint:** `POST /repos/add-files`  
**Description:** Add multiple files at once
```json
{
  "repo_path": "./my-repo",
  "files": [
    {
      "path": "src/utils.py",
      "content": "def helper_function():\n    return 'Helper'"
    },
    {
      "path": "README.md",
      "content": "# Project Title\n\nProject description here"
    }
  ]
}
```

### 8. Read File Contents
**Endpoint:** `GET /repos/read-file/{repo_path}/{file_name}`  
**Description:** Read the contents of a specific file
```
Example: GET /repos/read-file/my-repo/README.md
```

### 9. List Directory Contents
**Endpoint:** `GET /repos/list-files/{repo_path}`  
**Description:** List all files in a directory
```
Example: GET /repos/list-files/my-repo
```

---

## Git Operations

### 10. Create Local Branch
**Endpoint:** `POST /repos/create-branch`  
**Description:** Create and checkout a new branch locally
```json
{
  "repo_path": "./my-repo",
  "branch_name": "feature-new-component"
}
```

### 11. Create GitHub Branch
**Endpoint:** `POST /github/create-branch`  
**Description:** Create a branch directly on GitHub
```json
{
  "repo_name": "my-repo",
  "branch_name": "feature-branch",
  "from_branch": "main"
}
```

### 12. Stage All Changes
**Endpoint:** `POST /repos/add-all`  
**Description:** Stage all changes (like git add -A)
```json
{
  "repo_path": "./my-repo",
  "include_untracked": true
}
```

### 13. Commit Changes
**Endpoint:** `POST /repos/commit`  
**Description:** Commit staged changes with a message
```json
{
  "repo_path": "./my-repo",
  "commit_message": "feat: Add new authentication module"
}
```

### 14. Push to Remote
**Endpoint:** `POST /repos/push`  
**Description:** Push commits to GitHub
```json
{
  "repo_path": "./my-repo",
  "remote_name": "origin",
  "branch": "main"
}
```

### 15. Merge Branches
**Endpoint:** `POST /repos/merge`  
**Description:** Merge one branch into another locally
```json
{
  "repo_path": "./my-repo",
  "source_branch": "feature-branch",
  "target_branch": "main"
}
```

### 16. Check Repository Status
**Endpoint:** `GET /repos/status/{repo_path}`  
**Description:** Get git status of repository
```
Example: GET /repos/status/my-repo
```

---

## GitHub API Operations

### 17. List Repositories
**Endpoint:** `GET /github/list-repos`  
**Description:** List all your GitHub repositories
```
Query parameters:
- page: 1 (default)
- per_page: 30 (default, max 100)

Example: GET /github/list-repos?page=1&per_page=50
```

### 18. List Branches
**Endpoint:** `GET /github/list-branches/{repo_name}`  
**Description:** List all branches in a GitHub repository
```
Example: GET /github/list-branches/my-repo
```

### 19. Create Issue
**Endpoint:** `POST /github/create-issue`  
**Description:** Create an issue on GitHub
```json
{
  "repo_name": "my-repo",
  "title": "Bug: Application crashes on startup",
  "body": "## Description\nThe application fails to start when...\n\n## Steps to reproduce\n1. Run the application\n2. ...",
  "labels": ["bug", "high-priority"]
}
```

### 20. Create Pull Request
**Endpoint:** `POST /github/create-pr`  
**Description:** Create a pull request on GitHub
```json
{
  "repo_name": "my-repo",
  "head": "feature-branch",
  "base": "main",
  "title": "Add new feature X",
  "body": "## Summary\nThis PR adds feature X which allows users to...\n\n## Changes\n- Added new module\n- Updated documentation"
}
```

### 21. List Pull Requests
**Endpoint:** `GET /github/list-prs/{repo_name}`  
**Description:** List pull requests for a repository
```
Query parameters:
- state: "open" (default) | "closed" | "all"

Example: GET /github/list-prs/my-repo?state=all
```

---

## Utility Operations

### 22. Generate Gitignore
**Endpoint:** `POST /repos/generate-gitignore`  
**Description:** Generate a basic .gitignore file
```json
{
  "repo_path": "./my-repo",
  "project_type": "python"
}
```

### 23. Download GitHub Gitignore Template
**Endpoint:** `POST /repos/download-gitignore`  
**Description:** Download official GitHub gitignore template
```json
{
  "repo_path": "./my-repo",
  "project_type": "Python"
}
```

### 24. Detect Project Type
**Endpoint:** `GET /repos/detect-project-type/{repo_path}`  
**Description:** Auto-detect the project type
```
Example: GET /repos/detect-project-type/my-repo
```

### 25. Classify Intent
**Endpoint:** `POST /classify-intent`  
**Description:** Convert natural language to API action
```json
{
  "query": "create a new branch called feature-x"
}
```

### 26. List Available Intents
**Endpoint:** `GET /intents`  
**Description:** Get all available intent mappings
```
No payload required
```

---

## Complete Workflow Examples

### Example 1: Create New Project from Scratch
```bash
1. POST /auth/setup
   {"username": "john", "token": "ghp_xxxxx"}

2. POST /github/create-repo
   {"repo_name": "todo-app", "private": false, "description": "A simple todo application"}

3. POST /repos/clone
   {"repo_url": "https://github.com/john/todo-app.git", "local_path": "./todo-app"}

4. POST /repos/add-file
   {"repo_path": "./todo-app", "file_name": "app.py", "content": "from flask import Flask\napp = Flask(__name__)"}

5. POST /repos/download-gitignore
   {"repo_path": "./todo-app", "project_type": "Python"}

6. POST /repos/commit
   {"repo_path": "./todo-app", "commit_message": "Initial commit: Setup Flask app"}

7. POST /repos/push
   {"repo_path": "./todo-app", "remote_name": "origin", "branch": "main"}
```

### Example 2: Feature Development Workflow
```bash
1. POST /repos/clone
   {"repo_url": "https://github.com/john/existing-project.git", "local_path": "./existing-project"}

2. POST /repos/create-branch
   {"repo_path": "./existing-project", "branch_name": "feature-user-auth"}

3. POST /repos/add-file
   {"repo_path": "./existing-project", "file_name": "auth.py", "content": "import jwt\n# Authentication logic"}

4. POST /repos/commit
   {"repo_path": "./existing-project", "commit_message": "feat: Add JWT authentication"}

5. POST /repos/push
   {"repo_path": "./existing-project", "remote_name": "origin", "branch": "feature-user-auth"}

6. POST /github/create-pr
   {"repo_name": "existing-project", "head": "feature-user-auth", "base": "main", "title": "Add user authentication"}
```

### Example 3: Batch File Operations
```bash
1. POST /repos/add-files
{
  "repo_path": "./my-webapp",
  "files": [
    {"path": "index.html", "content": "<!DOCTYPE html><html><head><title>My App</title></head><body><h1>Hello!</h1></body></html>"},
    {"path": "style.css", "content": "body { font-family: Arial; margin: 0; padding: 20px; }"},
    {"path": "script.js", "content": "console.log('App loaded');"},
    {"path": "README.md", "content": "# My Web App\n\nA simple web application"}
  ]
}

2. POST /repos/add-all
   {"repo_path": "./my-webapp", "include_untracked": true}

3. POST /repos/commit
   {"repo_path": "./my-webapp", "commit_message": "Add web app files"}

4. POST /repos/push
   {"repo_path": "./my-webapp", "remote_name": "origin", "branch": "main"}
```

---

## Important Notes

1. **Authentication Required**: Most GitHub operations require credentials to be set up first using `/auth/setup`

2. **Local vs GitHub Operations**:
   - `/repos/*` endpoints work with local Git repositories
   - `/github/*` endpoints interact directly with GitHub's API

3. **Workflow Order**: Always follow the pattern:
   - Create/Clone → Modify → Stage → Commit → Push

4. **Error Handling**: 
   - 401: Credentials not set or invalid
   - 404: Repository/Resource not found
   - 422: Invalid request payload
   - 500: Server error (check logs)

5. **File Paths**: Use relative paths starting with `./` for local operations

6. **Branch Names**: Must be valid Git branch names (no spaces, special characters limited)

---

## Common Error Solutions

| Error | Solution |
|-------|----------|
| 403 on push | Ensure GitHub token has repo permissions |
| "Branch already exists" | Use a different branch name or checkout existing |
| "No changes to commit" | Make sure files were modified after last commit |
| "Repository not found" | Check repo name and that you have access |

---

*Generated by GitHub Automation Tool v1.0.0*
