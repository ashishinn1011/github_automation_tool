"""
Configuration management for the GitHub Automation Tool.
Handles environment variables, tool configurations, and system settings.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import json

# Try to import yaml, but make it optional
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    class Config:
        env_prefix = "SERVER_"

class GitHubConfig(BaseModel):
    """GitHub API configuration."""
    username: str = Field(default="")
    token: str = Field(default="")
    api_url: str = Field(default="https://api.github.com")
    timeout: int = Field(default=30)
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        # Don't validate during initialization, only warn
        if not v:
            print("Warning: GitHub token is not set. Please configure it using /auth/setup endpoint.")
        return v
    
    class Config:
        env_prefix = "GITHUB_"

class ToolConfig(BaseModel):
    """Tool execution configuration."""
    max_chain_length: int = Field(default=10)
    execution_timeout: int = Field(default=300)
    enable_parallel_execution: bool = Field(default=True)
    auto_execute_suggestions: bool = Field(default=False)
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    requests_per_minute: int = Field(default=60)
    
    # Caching
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=300)
    
    class Config:
        env_prefix = "TOOL_"

class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_auth: bool = Field(default=False)
    jwt_secret: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    token_expire_minutes: int = Field(default=60)
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"])
    cors_credentials: bool = Field(default=True)
    
    @field_validator("cors_origins", mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or ["*"]
    
    class Config:
        env_prefix = "SECURITY_"

class AIConfig(BaseModel):
    """AI agent configuration."""
    enable_ai_agent: bool = Field(default=True)
    ai_model: str = Field(default="gpt-4")
    ai_temperature: float = Field(default=0.7)
    ai_max_tokens: int = Field(default=2000)
    
    # Intent classification
    use_ml_classifier: bool = Field(default=False)
    classifier_model_path: str = Field(default="")
    
    class Config:
        env_prefix = "AI_"

class AppConfig:
    """Main application configuration."""
    
    def __init__(self):
        # Load configurations from environment
        self._load_from_env()
        
        # Initialize with defaults
        self.tool_metadata = {}
        self.workflows = {}
        
        # Defer file loading until explicitly called
        self._config_loaded = False
        
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Create config objects with environment variables
        self.server = ServerConfig(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            workers=int(os.getenv("WORKERS", "1")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
        
        self.github = GitHubConfig(
            username=os.getenv("GITHUB_USERNAME", ""),
            token=os.getenv("GITHUB_TOKEN", ""),
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            timeout=int(os.getenv("GITHUB_TIMEOUT", "30"))
        )
        
        self.tools = ToolConfig(
            max_chain_length=int(os.getenv("MAX_CHAIN_LENGTH", "10")),
            execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "300")),
            enable_parallel_execution=os.getenv("ENABLE_PARALLEL", "true").lower() == "true",
            auto_execute_suggestions=os.getenv("AUTO_EXECUTE", "false").lower() == "true",
            rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            requests_per_minute=int(os.getenv("REQUESTS_PER_MINUTE", "60")),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("CACHE_TTL", "300"))
        )
        
        self.security = SecurityConfig(
            enable_auth=os.getenv("ENABLE_AUTH", "false").lower() == "true",
            jwt_secret=os.getenv("JWT_SECRET", ""),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            token_expire_minutes=int(os.getenv("TOKEN_EXPIRE_MINUTES", "60")),
            cors_origins=SecurityConfig.parse_cors_origins(os.getenv("CORS_ORIGINS", "*")),
            cors_credentials=os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
        )
        
        self.ai = AIConfig(
            enable_ai_agent=os.getenv("ENABLE_AI_AGENT", "true").lower() == "true",
            ai_model=os.getenv("AI_MODEL", "gpt-4"),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", "2000")),
            use_ml_classifier=os.getenv("USE_ML_CLASSIFIER", "false").lower() == "true",
            classifier_model_path=os.getenv("CLASSIFIER_MODEL_PATH", "")
        )
        
    def load_config_files(self):
        """Load configuration files (call this explicitly when needed)."""
        if self._config_loaded:
            return
            
        try:
            self._load_tool_metadata()
            self._load_workflow_definitions()
            self._config_loaded = True
        except Exception as e:
            print(f"Warning: Could not load config files: {e}")
            # Use defaults
            self.tool_metadata = self._get_default_tool_metadata()
            self.workflows = self._get_default_workflows()
        
    def _load_tool_metadata(self):
        """Load tool metadata from configuration files."""
        try:
            config_dir = Path("config")
            if not config_dir.exists():
                config_dir.mkdir(exist_ok=True)
                
            metadata_file = config_dir / "tool_metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    self.tool_metadata = json.load(f)
            else:
                # Create default metadata
                self.tool_metadata = self._get_default_tool_metadata()
                with open(metadata_file, "w") as f:
                    json.dump(self.tool_metadata, f, indent=2)
        except Exception as e:
            print(f"Error loading tool metadata: {e}")
            self.tool_metadata = self._get_default_tool_metadata()
                
    def _load_workflow_definitions(self):
        """Load workflow definitions."""
        try:
            config_dir = Path("config")
            workflow_file = config_dir / "workflows.json"  # Use JSON instead of YAML
            
            if workflow_file.exists():
                with open(workflow_file) as f:
                    self.workflows = json.load(f)
            else:
                # Create default workflows
                self.workflows = self._get_default_workflows()
                with open(workflow_file, "w") as f:
                    json.dump(self.workflows, f, indent=2)
        except Exception as e:
            print(f"Error loading workflows: {e}")
            self.workflows = self._get_default_workflows()
                
    def _get_default_tool_metadata(self) -> Dict[str, Any]:
        """Get default tool metadata."""
        return {
            "tools": {
                "create_repository": {
                    "display_name": "Create Repository",
                    "category": "Repository Management",
                    "risk_level": "low",
                    "requires_confirmation": False,
                    "estimated_duration": 5
                },
                "push_changes": {
                    "display_name": "Push Changes",
                    "category": "Git Operations",
                    "risk_level": "medium",
                    "requires_confirmation": True,
                    "estimated_duration": 10
                },
                "merge_branches": {
                    "display_name": "Merge Branches",
                    "category": "Git Operations",
                    "risk_level": "high",
                    "requires_confirmation": True,
                    "estimated_duration": 15
                }
            }
        }
        
    def _get_default_workflows(self) -> Dict[str, Any]:
        """Get default workflow definitions."""
        return {
            "workflows": {
                "quick_start": {
                    "display_name": "Quick Start Repository",
                    "description": "Create and set up a new repository",
                    "steps": [
                        "create_repository",
                        "initialize_repository",
                        "generate_gitignore",
                        "add_readme",
                        "initial_commit",
                        "push_to_remote"
                    ]
                },
                "feature_branch": {
                    "display_name": "Feature Branch Workflow",
                    "description": "Create a feature branch and PR",
                    "steps": [
                        "create_branch",
                        "switch_branch",
                        "add_changes",
                        "commit_changes",
                        "push_branch",
                        "create_pull_request"
                    ]
                }
            }
        }
        
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Only validate critical errors
        if self.security.enable_auth and not self.security.jwt_secret:
            errors.append("JWT secret required when auth is enabled")
            
        if self.ai.use_ml_classifier and not self.ai.classifier_model_path:
            errors.append("Classifier model path required when ML classifier is enabled")
            
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
            
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "server": self.server.model_dump(),
            "github": {k: v for k, v in self.github.model_dump().items() if k != "token"},
            "tools": self.tools.model_dump(),
            "security": {k: v for k, v in self.security.model_dump().items() if k != "jwt_secret"},
            "ai": self.ai.model_dump()
        }

# Singleton instance
_config_instance = None

def get_config() -> AppConfig:
    """Get application configuration."""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance

def reload_config():
    """Reload configuration from files."""
    global _config_instance
    _config_instance = AppConfig()
    return _config_instance

def update_config(section: str, key: str, value: Any):
    """Update configuration value."""
    config = get_config()
    if hasattr(config, section):
        section_config = getattr(config, section)
        if hasattr(section_config, key):
            setattr(section_config, key, value)
            return True
    return False

# Environment-specific configurations
def get_environment() -> str:
    """Get current environment."""
    return os.getenv("ENVIRONMENT", "development")

def is_production() -> bool:
    """Check if running in production."""
    return get_environment() == "production"

def is_development() -> bool:
    """Check if running in development."""
    return get_environment() == "development"

# Feature flags
class FeatureFlags:
    """Feature flags for gradual rollout."""
    
    def __init__(self):
        self.flags = {
            "auto_chain_execution": os.getenv("FF_AUTO_CHAIN", "false").lower() == "true",
            "parallel_execution": os.getenv("FF_PARALLEL", "true").lower() == "true",
            "ai_suggestions": os.getenv("FF_AI_SUGGESTIONS", "true").lower() == "true",
            "advanced_workflows": os.getenv("FF_WORKFLOWS", "false").lower() == "true"
        }
        
    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.flags.get(feature, False)
        
    def enable(self, feature: str):
        """Enable a feature."""
        self.flags[feature] = True
        
    def disable(self, feature: str):
        """Disable a feature."""
        self.flags[feature] = False

# Feature flags instance
feature_flags = FeatureFlags()