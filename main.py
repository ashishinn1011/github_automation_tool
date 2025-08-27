#!/usr/bin/env python3
import click
import os
import sys
import logging
import git
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import git operations
from git_operations import (
    init_local_repo, add_and_commit, push_changes, create_branch,
    ensure_main_branch, merge_branch, generate_gitignore, download_github_gitignore,
    list_directory_contents, read_file_contents, add_file_with_content, 
    add_multiple_files, format_response
)

# Import GitHub API operations
from github_api import create_github_repo

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('git_cli')

def set_github_credentials():
    """Prompt for and save GitHub credentials."""
    username = input("GitHub Username: ")
    token = input("GitHub API Token: ")
    
    # Set environment variables
    os.environ["GITHUB_USERNAME"] = username
    os.environ["GITHUB_TOKEN"] = token
    
    # Save to .env file
    env_path = Path(".env")
    with open(env_path, "w") as f:
        f.write(f"GITHUB_USERNAME={username}\n")
        f.write(f"GITHUB_TOKEN={token}\n")
    
    logger.info("GitHub credentials saved to .env file")

def ensure_github_credentials():
    """Ensure GitHub credentials are available, prompt if needed."""
    if not os.getenv("GITHUB_USERNAME") or not os.getenv("GITHUB_TOKEN"):
        logger.info("GitHub credentials not found. Please enter your GitHub username and API token.")
        set_github_credentials()
    return os.getenv("GITHUB_USERNAME"), os.getenv("GITHUB_TOKEN")

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Git & GitHub Automation CLI Tool."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Ensure credentials are set before any command runs
    ctx.obj = {}
    ctx.obj['github_username'], ctx.obj['github_token'] = ensure_github_credentials()

@cli.command()
@click.argument("repo_name")
@click.option("--private", is_flag=True, help="Create a private repository")
@click.option("--description", help="Repository description")
@click.option("--readme/--no-readme", default=True, help="Initialize with README")
@click.option("--gitignore", help="Add .gitignore template (auto if not specified)")
@click.pass_context
def create(ctx, repo_name, private, description, readme, gitignore):
    """Create a new GitHub repository and initialize it locally."""
    try:
        # Get GitHub credentials from context
        github_username = ctx.obj['github_username']
        github_token = ctx.obj['github_token']
        
        # Make sure the token is available to github_api.py
        os.environ["GITHUB_USERNAME"] = github_username
        os.environ["GITHUB_TOKEN"] = github_token

        repo_path = f"./{repo_name}"
        
        # Create GitHub repository
        github_repo = create_github_repo(repo_name, private, description)
        logger.info(f"GitHub repository created: {github_repo['html_url']}")
        
        # Create local directory
        os.makedirs(repo_path, exist_ok=True)
        
        # Initialize Git repository
        repo = init_local_repo(repo_path)
        
        # Set origin URL
        origin_url = f"https://github.com/{github_username}/{repo_name}.git"
        
        # Manage 'origin' remote
        if "origin" in [remote.name for remote in repo.remotes]:
            origin_remote = repo.remotes["origin"]
            repo.delete_remote(origin_remote)
            logger.info(f"Updating 'origin' to {origin_url}")
        repo.create_remote("origin", url=origin_url)
        logger.info(f"Remote 'origin' added with URL: {origin_url}")
        
        # Ensure main branch exists
        ensure_main_branch(repo_path)
        
        # Add README if needed
        if readme:
            with open(os.path.join(repo_path, "README.md"), "w") as f:
                f.write(f"# {repo_name}\n\n{description or 'A new project'}")
            logger.info("README.md created")
        
        # Add .gitignore if needed
        if gitignore:
            download_github_gitignore(repo_path, gitignore)
        else:
            generate_gitignore(repo_path)
        
        # Commit and push initial files
        add_and_commit(repo_path, "Initial commit")
        push_changes(repo_path, "origin", "main")
        
        logger.info(f"Repository '{repo_name}' created & pushed successfully!")
        logger.info(f"GitHub URL: {github_repo['html_url']}")
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise click.ClickException(str(e))
    except git.GitCommandError as e:
        logger.error(f"Git command error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.argument("file_name")
@click.argument("content")
@click.option("--commit", is_flag=True, help="Commit the file after creation")
@click.option("--message", "-m", help="Commit message (default: Add {file_name})")
def add_file(repo_path, file_name, content, commit, message):
    """Create a file with the specified content."""
    try:
        result = add_file_with_content(repo_path, file_name, content)
        click.echo(result)
        
        if commit:
            commit_msg = message or f"Add {file_name}"
            add_and_commit(repo_path, commit_msg)
            click.echo(f"Changes committed with message: '{commit_msg}'")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.option("--gitignore", is_flag=True, help="Generate .gitignore file")
def init(repo_path, gitignore):
    """Initialize a local Git repository and ensure 'main' branch exists."""
    try:
        init_local_repo(repo_path)
        ensure_main_branch(repo_path)
        
        if gitignore:
            generate_gitignore(repo_path)
            
        logger.info(f"Git initialized at {repo_path} with 'main' branch ensured.")
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.argument("branch_name")
def branch(repo_path, branch_name):
    """Create a new branch and check it out."""
    try:
        create_branch(repo_path, branch_name)
        logger.info(f"Branch '{branch_name}' created in {repo_path}")
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.option("--message", "-m", required=True, help="Commit message")
@click.option("--push", is_flag=True, help="Push changes after commit")
def commit(repo_path, message, push):
    """Add and commit changes."""
    try:
        result = add_and_commit(repo_path, message)
        
        if result and push:
            # Get current branch
            repo = git.Repo(repo_path)
            current_branch = repo.active_branch.name
            push_changes(repo_path, "origin", current_branch)
            logger.info(f"Changes pushed to origin/{current_branch}")
            
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.option("--remote", default="origin", help="Remote name")
@click.option("--branch", help="Branch to push (default: current branch)")
def push(repo_path, remote, branch):
    """Push commits to a remote repository."""
    try:
        push_changes(repo_path, remote, branch)
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.argument("source_branch")
@click.argument("target_branch", default="main")
@click.option("--push", is_flag=True, help="Push target branch after merge")
def merge(repo_path, source_branch, target_branch, push):
    """Merge a branch into the target branch (default: main)."""
    try:
        result = merge_branch(repo_path, source_branch, target_branch)
        
        if result and push:
            push_changes(repo_path, "origin", target_branch)
            logger.info(f"Merged changes pushed to origin/{target_branch}")
            
    except Exception as e:
        logger.error(f"Error merging branches: {e}")
        raise click.ClickException(str(e))

@cli.command(name="gitignore")
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--type", "project_type", help="Specify project type (auto-detect if not specified)")
@click.option("--from-github", is_flag=True, help="Download template from GitHub")
def generate_gitignore_cmd(repo_path, project_type, from_github):
    """Generate a .gitignore file for the repository."""
    try:
        if from_github:
            download_github_gitignore(repo_path, project_type)
        else:
            generate_gitignore(repo_path)
            
    except Exception as e:
        logger.error(f"Error generating .gitignore: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
def status(repo_path):
    """Show the status of the repository."""
    try:
        repo = git.Repo(repo_path)
        status = repo.git.status()
        click.echo(status)
    except Exception as e:
        logger.error(f"Error getting repository status: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
def current_branch(repo_path):
    """Show the current branch of the repository."""
    try:
        repo = git.Repo(repo_path)
        branch = repo.active_branch.name
        click.echo(f"Current branch: {branch}")
    except Exception as e:
        logger.error(f"Error getting current branch: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.option("--all", is_flag=True, help="Show all branches including remote")
def branches(repo_path, all):
    """List all branches in the repository."""
    try:
        repo = git.Repo(repo_path)
        
        if all:
            # Show local and remote branches
            click.echo("Local branches:")
            for branch in repo.heads:
                click.echo(f"  {'* ' if branch.name == repo.active_branch.name else '  '}{branch.name}")
                
            click.echo("\nRemote branches:")
            for ref in repo.remote().refs:
                # Skip HEAD reference
                if ref.name == 'origin/HEAD':
                    continue
                click.echo(f"  {ref.name}")
        else:
            # Show only local branches
            for branch in repo.heads:
                click.echo(f"{'* ' if branch.name == repo.active_branch.name else '  '}{branch.name}")
                
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("repo_path")
@click.argument("branch_name")
def checkout(repo_path, branch_name):
    """Checkout a branch."""
    try:
        repo = git.Repo(repo_path)
        
        # Check if branch exists
        if branch_name not in [head.name for head in repo.heads]:
            # Check if it's a remote branch
            remote_branch = f"origin/{branch_name}"
            if remote_branch in [ref.name for ref in repo.remote().refs]:
                # Create local branch from remote
                repo.git.checkout("-b", branch_name, remote_branch)
                logger.info(f"Created local branch '{branch_name}' from {remote_branch}")
            else:
                raise click.ClickException(f"Branch '{branch_name}' not found")
        else:
            # Checkout existing branch
            repo.git.checkout(branch_name)
            logger.info(f"Switched to branch '{branch_name}'")
            
    except git.GitCommandError as e:
        logger.error(f"Git error: {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Error checking out branch: {e}")
        raise click.ClickException(str(e))

@cli.command(name="list")
@click.argument("repo_path")
def list_contents(repo_path):
    """List the contents of a directory."""
    try:
        contents = list_directory_contents(repo_path)
        click.echo(f"Contents of '{repo_path}':")
        for item in contents:
            click.echo(f"  - {item}")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))

@cli.command(name="read")
@click.argument("repo_path")
@click.argument("file_name")
def read_file(repo_path, file_name):
    """Read the contents of a file."""
    try:
        contents = read_file_contents(repo_path, file_name)
        click.echo(f"Contents of '{file_name}':\n{contents}")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--files', '-f', multiple=True, help="File paths and contents in format 'path:content'")
@click.option('--input-file', '-i', type=click.Path(exists=True), help="Text file containing file paths and contents")
def add_files(repo_path, files, input_file):
    """Add multiple files to a repository at once.
    
    Examples:
    
    # Add files directly via command line
    git-automation add-files /path/to/repo -f "src/main.py:print('Hello')" -f "README.md:# My Project"
    
    # Add files from input file
    git-automation add-files /path/to/repo -i files.txt
    """
    try:
        files_list = []
        
        # Process direct file inputs
        for file_input in files:
            if ':' not in file_input:
                logger.error(f"Invalid file format: {file_input}. Use 'path:content'")
                continue
            path, content = file_input.split(':', 1)
            files_list.append({"path": path.strip(), "content": content.strip()})
        
        # Process input file if provided
        if input_file:
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        path, content = line.split(':', 1)
                        files_list.append({"path": path.strip(), "content": content.strip()})
                    elif line:
                        logger.warning(f"Skipping malformed line in input file: {line}")
        
        if not files_list:
            logger.error("No valid files provided to add")
            return
        
        logger.info(f"Adding {len(files_list)} files to repository at {repo_path}")
        result = add_multiple_files(repo_path, files_list)
        
        if result.get("success", False):
            logger.info(f"Successfully added {len(result['created_files'])} files")
            for file_path in result['created_files']:
                logger.debug(f"Created: {file_path}")
        else:
            logger.error(f"Completed with errors: {result.get('message', 'Unknown error')}")
            for error in result.get('errors', []):
                logger.error(error)
            
    except Exception as e:
        logger.error(f"Error adding files: {e}")
        raise click.ClickException(str(e))

@cli.command()
def configure():
    """Configure GitHub credentials."""
    set_github_credentials()
    click.echo("GitHub credentials configured successfully!")

@cli.command()
def version():
    """Show version information."""
    click.echo("Git & GitHub Automation CLI v1.0.0")

if __name__ == "__main__":
    # Ensure GitHub credentials are available
    if not os.getenv("GITHUB_USERNAME") or not os.getenv("GITHUB_TOKEN"):
        print("GitHub credentials not found. Please enter your GitHub username and API token.")
        set_github_credentials()
    
    # Run the CLI
    cli()