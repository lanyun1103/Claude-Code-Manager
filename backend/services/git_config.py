"""Helpers for merging project-level and global git configuration."""


def merge_git_config(project_config: dict, global_config: dict) -> dict:
    """Merge project-level git config with global fallback.

    Identity layer (git_author_name + git_author_email):
      Both name AND email must be present on the project to use project-level identity.
      If either is missing, fall back to the global config entirely.

    Credential layer (git_credential_type + key/token):
      If the project has a credential_type set, use all project-level credential fields.
      Otherwise fall back to the global credential config.
    """
    result: dict = {}

    # Identity: all-or-nothing
    if project_config.get("git_author_name") and project_config.get("git_author_email"):
        result["git_author_name"] = project_config["git_author_name"]
        result["git_author_email"] = project_config["git_author_email"]
    else:
        result["git_author_name"] = global_config.get("git_author_name")
        result["git_author_email"] = global_config.get("git_author_email")

    # Credential: per-layer fallback
    if project_config.get("git_credential_type"):
        result["git_credential_type"] = project_config["git_credential_type"]
        result["git_ssh_key_path"] = project_config.get("git_ssh_key_path")
        result["git_https_username"] = project_config.get("git_https_username")
        result["git_https_token"] = project_config.get("git_https_token")
    else:
        result["git_credential_type"] = global_config.get("git_credential_type")
        result["git_ssh_key_path"] = global_config.get("git_ssh_key_path")
        result["git_https_username"] = global_config.get("git_https_username")
        result["git_https_token"] = global_config.get("git_https_token")

    return result


def settings_to_dict(settings_obj) -> dict:
    """Convert a GlobalSettings ORM object (or None) to a plain dict."""
    if settings_obj is None:
        return {}
    return {
        "git_author_name": settings_obj.git_author_name,
        "git_author_email": settings_obj.git_author_email,
        "git_credential_type": settings_obj.git_credential_type,
        "git_ssh_key_path": settings_obj.git_ssh_key_path,
        "git_https_username": settings_obj.git_https_username,
        "git_https_token": settings_obj.git_https_token,
    }
