import inspect

import pytest
from typer.testing import CliRunner

from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import ChainedCache
from bakelib.utils.secret import SECRET_GROUP, SecretUtils

runner = CliRunner()

NAMESPACE = "test-secret"
KEY_1 = "test-key-1"
KEY_2 = "test-key-2"


class TestSecretUtilsInit:
    def test_creates_secret_group(self) -> None:
        """SecretUtils should create a 'secret' command group."""

        class TestSecretUtils(SecretUtils):
            def get_secret_namespace(self) -> str:
                return "test-namespace"

        bakebook = TestSecretUtils()
        assert SECRET_GROUP in bakebook._command_groups

    def test_get_secret_namespace_defaults_to_bakebook(self) -> None:
        """get_secret_namespace should return 'bakebook' by default."""
        bakebook = SecretUtils()
        assert bakebook.get_secret_namespace() == "bakebook"

    def test_get_group_kwargs_returns_secret_config(self) -> None:
        """get_group_kwargs should return config for 'secret' group."""
        bakebook = SecretUtils()
        group_kwargs = bakebook.get_group_kwargs()
        assert SECRET_GROUP in group_kwargs
        assert group_kwargs[SECRET_GROUP].help == "Manage cached secrets"

    def test_group_help_shows_in_cli(self) -> None:
        """Group help text should appear in CLI --help output."""
        result = runner.invoke(SecretUtils()._app, ["--help"])
        # Look for the secret command with its help text
        assert "secret" in result.output
        assert "Manage cached secrets" in result.output


class TestSecretList:
    def test_list_shows_no_secrets_message(self) -> None:
        """secret list should show message when no secrets tracked."""
        result = runner.invoke(SecretUtils()._app, ["secret", "list"])
        assert result.exit_code == 0
        assert "No tracked secrets" in result.stdout

    def test_list_shows_tracked_secrets(self) -> None:
        """secret list should show tracked keys with status."""

        class SecretsWithKeys(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1, KEY_2}

        bakebook = SecretsWithKeys()

        result = runner.invoke(bakebook._app, ["secret", "list"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert f"Tracked secrets (namespace: {NAMESPACE}):" in stdout
        assert KEY_1 in stdout
        assert KEY_2 in stdout
        assert "not cached" in stdout  # Both keys are not cached initially

    def test_list_shows_cached_status_after_set(self) -> None:
        """secret list should show 'cached' status after setting a value."""

        class SecretsWithKeys(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1}

        bakebook = SecretsWithKeys()

        # Set a value first
        runner.invoke(bakebook._app, ["secret", "set", KEY_1, "my-value"])

        # Now list should show cached
        result = runner.invoke(bakebook._app, ["secret", "list"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "cached" in stdout


class TestSecretGet:
    def test_get_returns_value(self) -> None:
        """secret get should return the cached value."""
        bakebook = SecretUtils()

        # Set a value first
        bakebook.set_secret(KEY_1, "my-secret-value")

        result = runner.invoke(bakebook._app, ["secret", "get", KEY_1])
        assert result.exit_code == 0
        assert "my-secret-value" in result.stdout

    def test_get_errors_when_not_found(self) -> None:
        """secret get should error when key not found."""
        bakebook = SecretUtils()

        result = runner.invoke(bakebook._app, ["secret", "get", KEY_2])
        assert result.exit_code == 1


class TestSecretSet:
    def test_set_stores_value(self) -> None:
        """secret set should store value in keyring."""
        bakebook = SecretUtils()

        result = runner.invoke(bakebook._app, ["secret", "set", KEY_1, "my-value"])

        assert result.exit_code == 0

        # Verify value was actually stored
        value = bakebook.get_secret(KEY_1)
        assert value == "my-value"

    def test_set_warns_for_unregistered_key(self) -> None:
        """secret set should warn when key is not pre-registered."""
        bakebook = SecretUtils()

        result = runner.invoke(bakebook._app, ["secret", "set", KEY_2, "value"])
        output = strip_ansi(result.output)  # output includes both stdout and stderr

        assert "is not registered" in output
        assert "will not persist" in output


class TestSecretDel:
    def test_del_removes_single_key(self) -> None:
        """secret del <key> should remove specific key."""
        bakebook = SecretUtils()
        bakebook.set_secret(KEY_1, "value-to-delete")

        result = runner.invoke(bakebook._app, ["secret", "del", KEY_1])

        assert result.exit_code == 0

        # Verify value was actually deleted
        value = bakebook.get_secret(KEY_1)
        assert value is None

    def test_del_no_args_deletes_all(self) -> None:
        """secret del (no args) should delete all tracked keys."""

        class SecretsWithKeys(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1, KEY_2}

        bakebook = SecretsWithKeys()
        bakebook.set_secret(KEY_1, "value-1")
        bakebook.set_secret(KEY_2, "value-2")

        result = runner.invoke(bakebook._app, ["secret", "del"])

        assert result.exit_code == 0

        # Verify both values were deleted
        assert bakebook.get_secret(KEY_1) is None
        assert bakebook.get_secret(KEY_2) is None


class TestSecretDelVsRefresh:
    def test_del_vs_refresh_behavior(self) -> None:
        """del_secret vs refresh_secret: del just clears, refresh clears and fetches."""

        class SecretsWithFetchFn(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1, KEY_2}

            def _get_fetch_fn(self, key: str):
                def fetch() -> str | None:
                    return f"fetched-{key}"

                return fetch

        bakebook = SecretsWithFetchFn()
        bakebook.set_secret(KEY_1, "original-value")

        # del_secret: just clears cache
        bakebook.del_secret(KEY_1)
        cache1 = bakebook.get_secret_cache(KEY_1)
        assert cache1._get_entry() is None  # No entry after del

        # Set again for refresh test
        bakebook.set_secret(KEY_2, "original-value")

        # refresh_secret: clears cache then fetches
        bakebook.refresh_secret(KEY_2)
        cache2 = bakebook.get_secret_cache(KEY_2)
        entry2 = cache2._get_entry()
        assert entry2 is not None  # Entry exists (fetch was called)
        assert entry2.value == f"fetched-{KEY_2}"  # Value is from fetch_fn


class TestSecretRefresh:
    def test_refresh_clears_single_key(self) -> None:
        """secret refresh <key> should delete and fetch fresh value."""
        bakebook = SecretUtils()
        bakebook.set_secret(KEY_1, "value-to-refresh")

        result = runner.invoke(bakebook._app, ["secret", "refresh", KEY_1])

        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()

        # Verify cache was refreshed (deleted old, fetched new which is None for default fetch_fn)
        cache = bakebook.get_secret_cache(KEY_1)
        entry = cache._get_entry()
        assert entry is not None  # Entry exists (fetch was called)
        assert entry.value is None  # Value is None (from null_fetch_fn)

    def test_refresh_no_args_refreshes_all(self) -> None:
        """secret refresh (no args) should refresh all tracked keys."""

        class SecretsWithKeys(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1, KEY_2}

        bakebook = SecretsWithKeys()
        bakebook.set_secret(KEY_1, "value-1")
        bakebook.set_secret(KEY_2, "value-2")

        result = runner.invoke(bakebook._app, ["secret", "refresh"])

        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()

        # Verify both were refreshed (entries exist with None values from fetch_fn)
        cache1 = bakebook.get_secret_cache(KEY_1)
        cache2 = bakebook.get_secret_cache(KEY_2)
        entry1 = cache1._get_entry()
        entry2 = cache2._get_entry()
        assert entry1 is not None
        assert entry1.value is None
        assert entry2 is not None
        assert entry2.value is None


class TestGetSecretKeys:
    def test_get_secret_keys_returns_empty_by_default(self) -> None:
        """get_secret_keys should return empty set by default."""
        bakebook = SecretUtils()
        assert bakebook.get_secret_keys() == set()

    def test_get_secret_keys_override_in_subclass(self) -> None:
        """get_secret_keys can be overridden in subclass."""

        class SecretsWithKeys(SecretUtils):
            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1, KEY_2}

        bakebook = SecretsWithKeys()
        assert bakebook.get_secret_keys() == {KEY_1, KEY_2}


class TestGetSecretCache:
    def test_get_secret_cache_creates_chained_cache(self) -> None:
        """get_secret_cache should create ChainedCache with correct params."""

        class TestSecretUtils(SecretUtils):
            def get_secret_namespace(self) -> str:
                return "test-ns"

        bakebook = TestSecretUtils()
        cache = bakebook.get_secret_cache("test-key")

        assert cache._namespace == "test-ns"
        assert cache._key == "test-key"

    def test_get_secret_cache_signature_consistent_with_chained_cache(self) -> None:
        """get_secret_cache should expose all ChainedCache optional params.

        This test ensures maintenance consistency - when ChainedCache adds new
        optional parameters, get_secret_cache should be updated to expose them.

        Controlled params (NOT exposed - managed by SecretUtils):
        - backends: from self.secret_backends
        - namespace: from self.get_secret_namespace()
        - fetch_fn: from self._get_fetch_fn(key)
        - key: positional param in get_secret_cache
        """
        get_secret_cache_sig = inspect.signature(SecretUtils.get_secret_cache)
        chained_cache_sig = inspect.signature(ChainedCache.__init__)

        # Params controlled by SecretUtils (should NOT be in get_secret_cache)
        controlled_params = {"backends", "namespace", "fetch_fn", "key"}

        # Find all optional params in ChainedCache.__init__
        chained_cache_optional = {
            name
            for name, param in chained_cache_sig.parameters.items()
            if param.default is not inspect.Parameter.empty
        }

        # get_secret_cache should expose all optional params except controlled ones
        expected_exposed = chained_cache_optional - controlled_params

        # Verify all expected params are in get_secret_cache
        for param_name in expected_exposed:
            assert param_name in get_secret_cache_sig.parameters, (
                f"ChainedCache has optional param '{param_name}' "
                f"but get_secret_cache doesn't expose it. "
                f"Add '{param_name}' to get_secret_cache signature."
            )

        # Verify they're optional in get_secret_cache
        for param_name in expected_exposed:
            get_secret_cache_param = get_secret_cache_sig.parameters[param_name]
            assert get_secret_cache_param.default is not inspect.Parameter.empty, (
                f"'{param_name}' should be optional in get_secret_cache"
            )

    def test_get_secret_cache_accepts_stop_parameter(self) -> None:
        """get_secret_cache should accept optional stop parameter."""
        from tenacity import stop_after_attempt

        bakebook = SecretUtils()
        cache = bakebook.get_secret_cache("test-key", stop=stop_after_attempt(1))

        # Verify stop was passed through by checking the string representation
        assert "stop_after_attempt" in str(cache._stop)


class TestSecretMethods:
    def test_secret_methods_work_together(self) -> None:
        """set_secret, get_secret, del_secret should work together."""
        bakebook = SecretUtils()

        # Set
        bakebook.set_secret(KEY_1, "test-value")
        assert bakebook.get_secret(KEY_1) == "test-value"

        # Get
        assert bakebook.get_secret(KEY_1) == "test-value"

        # Delete
        bakebook.del_secret(KEY_1)
        assert bakebook.get_secret(KEY_1) is None


class TestCatchRefresh:
    def test_catch_refresh_as_decorator(self) -> None:
        """catch_refresh should work as decorator via get_secret_cache."""
        call_count = 0

        bakebook = SecretUtils()
        bakebook.set_secret(KEY_1, "cached-token")

        cache = bakebook.get_secret_cache(KEY_1)

        @cache.catch_refresh
        def api_call(should_fail_first: bool = False) -> str:
            nonlocal call_count
            call_count += 1
            token = cache.get_value()
            if should_fail_first and call_count == 1:
                raise cache.RefreshNeededError("Token expired")
            return f"success-{token}"

        result = api_call(should_fail_first=True)
        assert call_count == 2  # Initial call + 1 retry
        assert "success-" in result

    def test_catch_refresh_no_error(self) -> None:
        """catch_refresh should pass through when no error occurs."""
        call_count = 0

        bakebook = SecretUtils()
        bakebook.set_secret(KEY_1, "my-token")

        cache = bakebook.get_secret_cache(KEY_1)

        @cache.catch_refresh
        def api_call() -> str:
            nonlocal call_count
            call_count += 1
            return f"success-{cache.get_value()}"

        result = api_call()
        assert result == "success-my-token"
        assert call_count == 1

    def test_catch_refresh_deletes_cache_on_error(self) -> None:
        """catch_refresh should delete cache when RefreshNeededError is raised."""
        bakebook = SecretUtils()
        bakebook.set_secret(KEY_1, "cached-token")

        cache = bakebook.get_secret_cache(KEY_1)

        @cache.catch_refresh
        def api_call() -> str:
            raise cache.RefreshNeededError("Token expired")

        with pytest.raises(cache.RefreshNeededError):
            api_call()

        # Cache should be deleted after error
        assert cache._get_entry() is None

    def test_catch_refresh_in_subclass_method(self) -> None:
        """catch_refresh should work in a method of SecretUtils subclass."""

        class MySecrets(SecretUtils):
            call_count: int = 0

            def get_secret_namespace(self) -> str:
                return NAMESPACE

            def get_secret_keys(self) -> set[str]:
                return {KEY_1}

            def fetch_data(self, should_fail_first: bool = False) -> str:
                cache = self.get_secret_cache(KEY_1)

                @cache.catch_refresh
                def _do_fetch() -> str:
                    self.call_count += 1
                    token = cache.get_value()
                    if should_fail_first and self.call_count == 1:
                        raise cache.RefreshNeededError("Token expired")
                    return f"data-with-{token}"

                return _do_fetch()

        bakebook = MySecrets()
        bakebook.set_secret(KEY_1, "my-token")

        result = bakebook.fetch_data(should_fail_first=True)
        assert bakebook.call_count == 2  # Initial + 1 retry
        assert "data-with-" in result
