# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import logging

# Configure logging
logger = logging.getLogger("github_automation.auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class User:
    def __init__(self, username, email=None, roles=None):
        self.username = username
        self.email = email
        self.roles = roles or []
        
    def has_role(self, role):
        return role in self.roles

async def get_user(token: Optional[str] = Depends(oauth2_scheme)):
    """Get current user from token without Keycloak integration."""
    if not token:
        return None

    # For demonstration, assume token is valid.
    # Replace this with your actual token verification logic.
    if token == "admin":
        username = "admin"
        roles = ["admin"]
    else:
        username = token  # Use token as username for simplicity.
        roles = []
    
    return User(username=username, roles=roles)

def auth_required(roles=None):
    """
    Dependency that requires authentication and optionally specific roles.
    If roles is None, any authenticated user is allowed.
    """
    async def dependency(user = Depends(get_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check if user has any of the required roles.
        if roles:
            if not any(role in user.roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role(s) missing: {', '.join(roles)}"
                )
        
        return user
    
    return dependency
