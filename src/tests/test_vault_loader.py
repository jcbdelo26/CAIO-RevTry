from __future__ import annotations

from pathlib import Path

from utils import vault_loader


def test_vault_dir_prefers_configured_env_path(monkeypatch, tmp_path):
    configured = tmp_path / "custom-vault"
    configured.mkdir(parents=True)

    monkeypatch.setenv("VAULT_DIR", str(configured))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(vault_loader, "_project_root", lambda: tmp_path / "repo")

    assert vault_loader._vault_dir() == configured


def test_vault_dir_falls_back_to_cwd_revtry_vault(monkeypatch, tmp_path):
    fallback = tmp_path / "revtry" / "vault"
    fallback.mkdir(parents=True)

    monkeypatch.delenv("VAULT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(vault_loader, "_project_root", lambda: tmp_path / "repo")

    assert vault_loader._vault_dir() == fallback


def test_vault_dir_falls_back_to_project_root_revtry_vault(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    fallback = repo_root / "revtry" / "vault"
    fallback.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    monkeypatch.delenv("VAULT_DIR", raising=False)
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(vault_loader, "_project_root", lambda: repo_root)

    assert vault_loader._vault_dir() == fallback
