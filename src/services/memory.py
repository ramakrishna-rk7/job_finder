"""Context memory - Remember user preferences over time."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..config.settings import ensure_data_dir, BASE_DIR


MEMORY_FILE = BASE_DIR / "data" / "user_context.json"
MAX_HISTORY_DAYS = 30
MAX_SEARCH_HISTORY = 20


class UserContext:
    """User context stored in memory."""
    
    def __init__(
        self,
        user_id: str,
        preferred_roles: List[str] = None,
        preferred_skills: List[str] = None,
        preferred_location: Optional[str] = None,
        preferred_remote: bool = False,
        preferred_experience: str = "fresher",
        recent_searches: List[Dict[str, Any]] = None,
        last_updated: Optional[str] = None
    ):
        self.user_id = user_id
        self.preferred_roles = preferred_roles or []
        self.preferred_skills = preferred_skills or []
        self.preferred_location = preferred_location
        self.preferred_remote = preferred_remote
        self.preferred_experience = preferred_experience
        self.recent_searches = recent_searches or []
        self.last_updated = last_updated or datetime.now().isoformat()
    
    def add_search(self, query: str, keywords: List[str], location: Optional[str]):
        """Add search to history."""
        self.recent_searches.append({
            "query": query,
            "keywords": keywords,
            "location": location,
            "timestamp": datetime.now().isoformat()
        })
        
        self.recent_searches = self.recent_searches[-MAX_SEARCH_HISTORY:]
        self.last_updated = datetime.now().isoformat()
    
    def update_role(self, role: str):
        """Update preferred role."""
        if role not in self.preferred_roles:
            self.preferred_roles.append(role)
        self.preferred_roles = self.preferred_roles[-5:]
        self.last_updated = datetime.now().isoformat()
    
    def update_skills(self, skills: List[str]):
        """Update preferred skills."""
        for skill in skills:
            if skill not in self.preferred_skills:
                self.preferred_skills.append(skill)
        self.preferred_skills = self.preferred_skills[-10:]
        self.last_updated = datetime.now().isoformat()
    
    def update_location(self, location: str):
        """Update preferred location."""
        self.preferred_location = location
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "user_id": self.user_id,
            "preferred_roles": self.preferred_roles,
            "preferred_skills": self.preferred_skills,
            "preferred_location": self.preferred_location,
            "preferred_remote": self.preferred_remote,
            "preferred_experience": self.preferred_experience,
            "recent_searches": self.recent_searches,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserContext":
        """Create from dict."""
        return cls(
            user_id=data.get("user_id", ""),
            preferred_roles=data.get("preferred_roles", []),
            preferred_skills=data.get("preferred_skills", []),
            preferred_location=data.get("preferred_location"),
            preferred_remote=data.get("preferred_remote", False),
            preferred_experience=data.get("preferred_experience", "fresher"),
            recent_searches=data.get("recent_searches", []),
            last_updated=data.get("last_updated")
        )


class UserContextStore:
    """Store user context with 30-day retention."""
    
    def __init__(self):
        self.contexts: Dict[str, UserContext] = {}
        self._load()
    
    def _load(self):
        """Load contexts from file."""
        if not MEMORY_FILE.exists():
            return
        
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            for user_id, ctx_data in data.items():
                ctx = UserContext.from_dict(ctx_data)
                if self._is_valid(ctx):
                    self.contexts[user_id] = ctx
        except (json.JSONDecodeError, KeyError):
            pass
    
    def _save(self):
        """Save contexts to file."""
        ensure_data_dir()
        data = {user_id: ctx.to_dict() for user_id, ctx in self.contexts.items()}
        MEMORY_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _is_valid(self, ctx: UserContext) -> bool:
        """Check if context is still valid."""
        if not ctx.last_updated:
            return True
        
        try:
            last_time = datetime.fromisoformat(ctx.last_updated)
            age = datetime.now() - last_time
            return age.days < MAX_HISTORY_DAYS
        except ValueError:
            return True
    
    def get(self, user_id: str) -> Optional[UserContext]:
        """Get user context."""
        return self.contexts.get(user_id)
    
    def get_or_create(self, user_id: str) -> UserContext:
        """Get or create user context."""
        if user_id not in self.contexts:
            self.contexts[user_id] = UserContext(user_id=user_id)
        return self.contexts[user_id]
    
    def save(self, user_id: str, context: UserContext):
        """Save user context."""
        self.contexts[user_id] = context
        self._save()
    
    def delete(self, user_id: str):
        """Delete user context."""
        if user_id in self.contexts:
            del self.contexts[user_id]
            self._save()
    
    def update_from_search(
        self,
        user_id: str,
        query: str,
        keywords: List[str],
        location: Optional[str]
    ):
        """Update context from search."""
        ctx = self.get_or_create(user_id)
        ctx.add_search(query, keywords, location)
        
        for kw in keywords:
            if len(kw) > 2:
                ctx.update_role(kw)
        
        self._save()
    
    def get_preferred_skills(self, user_id: str) -> List[str]:
        """Get user's preferred skills."""
        ctx = self.get(user_id)
        return ctx.preferred_skills if ctx else []
    
    def get_preferred_location(self, user_id: str) -> Optional[str]:
        """Get user's preferred location."""
        ctx = self.get(user_id)
        return ctx.preferred_location if ctx else None
    
    def get_recent_searches(self, user_id: str) -> List[str]:
        """Get recent searches."""
        ctx = self.get(user_id)
        if not ctx:
            return []
        return [s["query"] for s in ctx.recent_searches[-5:]]
    
    def cleanup_old(self):
        """Remove old contexts."""
        original_count = len(self.contexts)
        self.contexts = {
            user_id: ctx
            for user_id, ctx in self.contexts.items()
            if self._is_valid(ctx)
        }
        
        if len(self.contexts) < original_count:
            self._save()


_context_store = None


def get_context_store() -> UserContextStore:
    """Get global context store."""
    global _context_store
    if _context_store is None:
        _context_store = UserContextStore()
    return _context_store


def load_user_context(user_id: str) -> Optional[UserContext]:
    """Load user context."""
    return get_context_store().get(user_id)


def save_user_context(user_id: str, context: UserContext):
    """Save user context."""
    get_context_store().save(user_id, context)


def update_context_from_search(
    user_id: str,
    query: str,
    keywords: List[str],
    location: Optional[str]
):
    """Update context from search."""
    get_context_store().update_from_search(user_id, query, keywords, location)


def get_user_preferred_skills(user_id: str) -> List[str]:
    """Get user's preferred skills."""
    return get_context_store().get_preferred_skills(user_id)


def get_user_preferred_location(user_id: str) -> Optional[str]:
    """Get user's preferred location."""
    return get_context_store().get_preferred_location(user_id)


if __name__ == "__main__":
    store = get_context_store()
    
    store.update_from_search("test_user", "Python developer", ["Python", "Django"], "India")
    
    ctx = store.get("test_user")
    if ctx:
        print(f"Roles: {ctx.preferred_roles}")
        print(f"Skills: {ctx.preferred_skills}")
        print(f"Recent: {store.get_recent_searches('test_user')}")