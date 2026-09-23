"""Declared deployment secrets come from the gateway's frozen launch environment."""

from agent import secret_scope
from gateway.config import GatewayConfig
from gateway.run import GatewayRunner, _profile_runtime_scope
from tui_gateway import launch_profile_policy


def test_declared_secret_uses_launch_snapshot_for_every_profile(tmp_path, monkeypatch):
    launch_home = tmp_path / "launch"
    launch_home.mkdir()
    secondary_home = tmp_path / "profiles" / "secondary"
    secondary_home.mkdir(parents=True)
    override_home = tmp_path / "profiles" / "override"
    override_home.mkdir()
    (override_home / ".env").write_text("OLLAMA_API_KEY=profile-key\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(launch_home))
    monkeypatch.setenv("OLLAMA_API_KEY", "launch-provider-key")
    monkeypatch.setenv("API_SERVER_KEY", "launch-peer-key")
    monkeypatch.delenv("LATE_ONLY_KEY", raising=False)
    monkeypatch.setattr(launch_profile_policy, "_snapshot", None)
    monkeypatch.setattr(secret_scope, "_MULTIPLEX_ACTIVE", False)
    secret_scope.set_deployment_secret_names(())

    GatewayRunner(GatewayConfig(
        multiplex_profiles=True,
        deployment_secret_env=["OLLAMA_API_KEY", "API_SERVER_KEY", "LATE_ONLY_KEY"],
    ))

    # A later process-env mutation must not become a new deployment credential.
    monkeypatch.setenv("OLLAMA_API_KEY", "late-provider-key")
    monkeypatch.setenv("API_SERVER_KEY", "late-peer-key")
    monkeypatch.setenv("LATE_ONLY_KEY", "late-only-key")
    monkeypatch.setenv("UNDECLARED_PROVIDER_KEY", "late-undeclared-key")

    with _profile_runtime_scope(secondary_home):
        assert secret_scope.get_secret("OLLAMA_API_KEY") == "launch-provider-key"
        assert secret_scope.get_secret("API_SERVER_KEY") == "launch-peer-key"
        assert secret_scope.get_secret("LATE_ONLY_KEY") is None
        assert secret_scope.get_secret("UNDECLARED_PROVIDER_KEY") is None
    with _profile_runtime_scope(override_home):
        assert secret_scope.get_secret("OLLAMA_API_KEY") == "profile-key"
        assert secret_scope.get_secret("API_SERVER_KEY") == "launch-peer-key"
    assert launch_profile_policy.launch_secret_scope(launch_home)["OLLAMA_API_KEY"] == "launch-provider-key"

    secret_scope.set_deployment_secret_names(())
