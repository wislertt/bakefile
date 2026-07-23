from dataclasses import dataclass

import pytest
from typer.testing import CliRunner

from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import FetchFn, NullFetchFn
from bakelib.utils.secret import SECRET_GROUP, SecretUtils

runner = CliRunner()

NAMESPACE = "test-secret"
KEY_1 = "test-key-1"
KEY_2 = "test-key-2"


class _SecretUtils(SecretUtils[str | None]):
    """Test subclass with declared keys and custom namespace."""

    def get_secret_namespace(self) -> str:
        return NAMESPACE

    def get_secret_fetch_fns(self) -> tuple[FetchFn[str | None], ...]:
        return (NullFetchFn[str | None](KEY_1), NullFetchFn[str | None](KEY_2))


class TestSecretUtilsInit:
    def test_creates_secret_group(self) -> None:
        bakebook = SecretUtils()
        assert SECRET_GROUP in bakebook._command_groups

    def test_get_group_kwargs_returns_secret_config(self) -> None:
        bakebook = SecretUtils()
        group_kwargs = bakebook.get_group_kwargs()
        assert SECRET_GROUP in group_kwargs
        assert group_kwargs[SECRET_GROUP].help == "Manage cached secrets"

    def test_group_help_shows_in_cli(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["--help"])
        assert "secret" in result.output
        assert "Manage cached secrets" in result.output

    def test_vault_namespace_defaults_to_bakebook(self) -> None:
        bakebook = SecretUtils()
        assert bakebook.vault().namespace == "bakebook"

    def test_vault_registers_declared_keys(self) -> None:
        bakebook = _SecretUtils()
        assert KEY_1 in bakebook.vault()
        assert KEY_2 in bakebook.vault()

    def test_vault_is_lazy(self) -> None:
        bakebook = _SecretUtils()
        v1 = bakebook.vault()
        v2 = bakebook.vault()
        assert v1 is v2


class TestSecretList:
    def test_list_shows_no_secrets_message(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["secret", "list"])
        assert result.exit_code == 0
        assert "No tracked secrets" in result.stdout

    def test_list_shows_tracked_secrets(self) -> None:
        bakebook = _SecretUtils()
        result = runner.invoke(bakebook._app, ["secret", "list"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert f"Tracked secrets (namespace: {NAMESPACE}):" in stdout
        assert KEY_1 in stdout
        assert KEY_2 in stdout
        assert "not cached" in stdout

    def test_list_shows_cached_status_after_set(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "my-value")

        result = runner.invoke(bakebook._app, ["secret", "list"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "cached" in stdout


class TestSecretGet:
    def test_get_returns_value(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "my-secret-value")

        result = runner.invoke(bakebook._app, ["secret", "get", KEY_1])
        assert result.exit_code == 0
        assert "my-secret-value" in result.stdout

    def test_get_errors_when_not_found(self) -> None:
        class FreshSecretUtils(_SecretUtils):
            def get_secret_namespace(self) -> str:
                return "test-secret-get-errors"

        bakebook = FreshSecretUtils()
        result = runner.invoke(bakebook._app, ["secret", "get", KEY_1])
        assert result.exit_code == 1

    def test_get_raises_for_undeclared_key(self) -> None:
        bakebook = SecretUtils()
        with pytest.raises(KeyError, match="not registered"):
            bakebook.get_secret(KEY_1)

    def test_get_untracked_key_exits_cleanly(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["secret", "get", "unknown-key"])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "not tracked" in output
        assert "Traceback" not in output


class TestSecretSet:
    def test_set_stores_value(self) -> None:
        bakebook = _SecretUtils()
        result = runner.invoke(bakebook._app, ["secret", "set", KEY_1, "my-value"])
        assert result.exit_code == 0
        assert bakebook.get_secret(KEY_1) == "my-value"

    def test_set_raises_for_undeclared_key(self) -> None:
        bakebook = SecretUtils()
        with pytest.raises(KeyError, match="not registered"):
            bakebook.set_secret(KEY_1, "value")

    def test_set_untracked_key_exits_cleanly(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["secret", "set", "unknown-key", "v"])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "not tracked" in output
        assert "Traceback" not in output


class TestSecretDel:
    def test_del_removes_single_key(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "value-to-delete")

        result = runner.invoke(bakebook._app, ["secret", "del", KEY_1])
        assert result.exit_code == 0
        assert bakebook.get_secret(KEY_1) is None

    def test_del_no_args_deletes_all(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "value-1")
        bakebook.set_secret(KEY_2, "value-2")

        result = runner.invoke(bakebook._app, ["secret", "del"])
        assert result.exit_code == 0
        assert bakebook.get_secret(KEY_1) is None
        assert bakebook.get_secret(KEY_2) is None

    def test_del_untracked_key_exits_cleanly(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["secret", "del", "unknown-key"])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "not tracked" in output
        assert "Traceback" not in output


class TestSecretDelVsRefresh:
    def test_del_vs_refresh_behavior(self) -> None:
        @dataclass(frozen=True)
        class FetchedKey(FetchFn[str | None]):
            def __call__(self) -> str | None:
                return f"fetched-{self.key}"

        class SecretsWithFetchFn(_SecretUtils):
            def get_secret_fetch_fns(self) -> tuple[FetchedKey, ...]:
                return (FetchedKey(KEY_1), FetchedKey(KEY_2))

        bakebook = SecretsWithFetchFn()
        bakebook.set_secret(KEY_1, "original-value")

        bakebook.del_secret(KEY_1)
        assert not bakebook.vault().has_value(KEY_1)

        bakebook.set_secret(KEY_2, "original-value")
        bakebook.refresh_secret(KEY_2)
        assert bakebook.vault().get_cache(KEY_2).get() == f"fetched-{KEY_2}"


class TestSecretRefresh:
    def test_refresh_clears_single_key(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "value-to-refresh")

        result = runner.invoke(bakebook._app, ["secret", "refresh", KEY_1])
        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()
        assert bakebook.vault().has_value(KEY_1)
        assert bakebook.get_secret(KEY_1) is None  # null_fetch_fn returns None

    def test_refresh_no_args_refreshes_all(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "value-1")
        bakebook.set_secret(KEY_2, "value-2")

        result = runner.invoke(bakebook._app, ["secret", "refresh"])
        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()
        assert bakebook.vault().has_value(KEY_1)
        assert bakebook.vault().has_value(KEY_2)

    def test_refresh_untracked_key_exits_cleanly(self) -> None:
        result = runner.invoke(SecretUtils()._app, ["secret", "refresh", "unknown-key"])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "not tracked" in output
        assert "Traceback" not in output


class TestCatchRefresh:
    def test_catch_refresh_as_decorator(self) -> None:
        call_count = 0

        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "cached-token")
        cache = bakebook.vault().get_cache(KEY_1)

        @cache.catch_refresh
        def api_call(should_fail_first: bool = False) -> str:
            nonlocal call_count
            call_count += 1
            token = cache.get()
            if should_fail_first and call_count == 1:
                raise cache.RefreshNeededError("Token expired")
            return f"success-{token}"

        result = api_call(should_fail_first=True)
        assert call_count == 2
        assert "success-" in result

    def test_catch_refresh_no_error(self) -> None:
        call_count = 0

        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "my-token")
        cache = bakebook.vault().get_cache(KEY_1)

        @cache.catch_refresh
        def api_call() -> str:
            nonlocal call_count
            call_count += 1
            return f"success-{cache.get()}"

        result = api_call()
        assert result == "success-my-token"
        assert call_count == 1

    def test_catch_refresh_deletes_cache_on_error(self) -> None:
        bakebook = _SecretUtils()
        bakebook.set_secret(KEY_1, "cached-token")
        cache = bakebook.vault().get_cache(KEY_1)

        @cache.catch_refresh
        def api_call() -> str:
            raise cache.RefreshNeededError("Token expired")

        with pytest.raises(cache.RefreshNeededError):
            api_call()

        assert not cache.has_value()

    def test_catch_refresh_in_subclass_method(self) -> None:
        class MySecrets(_SecretUtils):
            call_count: int = 0

            def fetch_data(self, should_fail_first: bool = False) -> str:
                cache = self.vault().get_cache(KEY_1)

                @cache.catch_refresh
                def _do_fetch() -> str:
                    self.call_count += 1
                    token = cache.get()
                    if should_fail_first and self.call_count == 1:
                        raise cache.RefreshNeededError("Token expired")
                    return f"data-with-{token}"

                return _do_fetch()

        bakebook = MySecrets()
        bakebook.set_secret(KEY_1, "my-token")

        result = bakebook.fetch_data(should_fail_first=True)
        assert bakebook.call_count == 2
        assert "data-with-" in result


@dataclass(frozen=True)
class GCPSecretFetchFn(FetchFn[str | None]):
    project_id: str
    secret_id: str

    def __call__(self) -> str | None:
        return f"{self.project_id}/{self.secret_id}"


class _ProjectSecretUtils(_SecretUtils):
    def get_secret_namespace(self) -> str:
        return "test-secret-project"

    def get_secret_fetch_fns(self) -> tuple[FetchFn[str | None], ...]:
        return (
            GCPSecretFetchFn(KEY_1, "proj-bake", f"secret-{KEY_1}"),
            NullFetchFn[str | None](KEY_2),
        )


class TestSecretUtilsProjectSecretFetch:
    def test_get_auto_fetches_with_project_and_secret_id(self) -> None:
        bakebook = _ProjectSecretUtils()
        assert bakebook.get_secret(KEY_1) == f"proj-bake/secret-{KEY_1}"

    def test_refresh_fetches_with_project_and_secret_id(self) -> None:
        bakebook = _ProjectSecretUtils()
        bakebook.refresh_secret(KEY_1)
        assert bakebook.get_secret(KEY_1) == f"proj-bake/secret-{KEY_1}"

    def test_cli_get_after_refresh_shows_fetched_value(self) -> None:
        bakebook = _ProjectSecretUtils()
        bakebook.refresh_secret(KEY_1)
        result = runner.invoke(bakebook._app, ["secret", "get", KEY_1])
        assert result.exit_code == 0
        assert f"proj-bake/secret-{KEY_1}" in strip_ansi(result.stdout)

    def test_set_overrides_fetched_value(self) -> None:
        bakebook = _ProjectSecretUtils()
        bakebook.refresh_secret(KEY_1)
        bakebook.set_secret(KEY_1, "manual")
        assert bakebook.get_secret(KEY_1) == "manual"

    def test_keys_use_mixed_fetch_sources(self) -> None:
        bakebook = _ProjectSecretUtils()
        bakebook.refresh_secret(KEY_1)
        bakebook.refresh_secret(KEY_2)
        assert bakebook.get_secret(KEY_1) == f"proj-bake/secret-{KEY_1}"
        assert bakebook.get_secret(KEY_2) is None
