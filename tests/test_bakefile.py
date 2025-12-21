from bakefile.hello import hello


def test_hello_returns_expected_string():
    result = hello()
    lines = result.strip().split("\n")
    assert lines[0] == "Hello from bakefile!"
    assert "Current time:" in lines[1]
    assert "Current directory:" in lines[2]
    assert "Python version:" in lines[3]


def test_hello_returns_str():
    result = hello()
    assert isinstance(result, str)


def test_hello_is_not_empty():
    result = hello()
    assert len(result) > 0
