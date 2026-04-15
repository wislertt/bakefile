import logging

import pytest

from bake.bakebook.utils import parse_bake_log, serialize_bake_log


class TestParseBakeLog:
    def test_simple_global_level(self) -> None:
        result = parse_bake_log("info")
        assert result == {"": 20}

    def test_global_and_per_module(self) -> None:
        result = parse_bake_log("info,myapp=debug,myapp.db=warning")
        assert result == {"": 20, "myapp": 10, "myapp.db": 30}

    def test_module_only_raises(self) -> None:
        with pytest.raises(ValueError, match="default logging level"):
            parse_bake_log("myapp=debug,myapp.db=warning")

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError, match=r"BAKE_LOG must be a non-empty string"):
            parse_bake_log("")

    def test_warn_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid BAKE_LOG level 'warn'"):
            parse_bake_log("warn")

    def test_all_level_names(self) -> None:
        level_names = [
            "critical",
            "error",
            "warning",
            "info",
            "success",
            "debug",
            "trace",
            "notset",
        ]
        for level_name in level_names:
            result = parse_bake_log(level_name)
            assert "" in result

    def test_level_numbers_match_loguru(self) -> None:
        expected = {
            "critical": 50,
            "error": 40,
            "warning": 30,
            "success": 25,
            "info": 20,
            "debug": 10,
            "trace": 5,
            "notset": 0,
        }
        for level_name, expected_no in expected.items():
            assert parse_bake_log(level_name)[""] == expected_no

    def test_invalid_level_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid BAKE_LOG level 'invalid'"):
            parse_bake_log("invalid")

    def test_invalid_level_in_module_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid BAKE_LOG level 'bad'"):
            parse_bake_log("myapp=bad")

    def test_empty_module_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="empty module name"):
            parse_bake_log("=debug")

    def test_whitespace_handling(self) -> None:
        result = parse_bake_log(" info , myapp = debug ")
        assert result == {"": 20, "myapp": 10}

    def test_empty_parts_ignored(self) -> None:
        result = parse_bake_log("info,,myapp=debug")
        assert result == {"": 20, "myapp": 10}

    def test_module_then_global(self) -> None:
        result = parse_bake_log("myapp=debug,info")
        assert result == {"": 20, "myapp": 10}

    @pytest.mark.parametrize(
        "bake_log",
        [
            "warning",
            "warning,bake=debug",
            "info,myapp=debug,myapp.db=warning",
            "bake=debug,info",
        ],
    )
    def test_round_trip_from_str(self, bake_log: str) -> None:
        result = serialize_bake_log(parse_bake_log(bake_log))
        assert parse_bake_log(result) == parse_bake_log(bake_log)


class TestSerializeBakeLog:
    @pytest.mark.parametrize(
        "level_per_module, expected",
        [
            ({"": 30}, "warning"),
            ({"": logging.WARNING, "bake": logging.DEBUG}, "warning,bake=debug"),
            (
                {"": logging.WARNING, "bake": logging.DEBUG, "bakelib": logging.DEBUG},
                "warning,bake=debug,bakelib=debug",
            ),
        ],
    )
    def test_serialize(self, level_per_module: dict, expected: str) -> None:
        assert serialize_bake_log(level_per_module) == expected

    def test_none_key_raises(self) -> None:
        with pytest.raises(ValueError, match="default logging level"):
            serialize_bake_log({None: logging.INFO})  # ty: ignore[invalid-argument-type]

    def test_invalid_level_int_raises(self) -> None:
        with pytest.raises(KeyError):
            serialize_bake_log({"": logging.INFO, "bake": 99})

    def test_missing_default_key_raises(self) -> None:
        with pytest.raises(ValueError, match="default logging level"):
            serialize_bake_log({"bake": logging.DEBUG})

    def test_empty_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty dict"):
            serialize_bake_log({})

    @pytest.mark.parametrize(
        "level_per_module",
        [
            {"": 30},
            {"": 30, "bake": 10},
            {"": 20, "bake": 10, "bakelib": 10},
        ],
    )
    def test_round_trip_from_dict(self, level_per_module: dict) -> None:
        assert parse_bake_log(serialize_bake_log(level_per_module)) == level_per_module
