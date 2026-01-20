from pydantic import Field, SecretStr

from bakelib import PythonSpace


class MyPythonSpace(PythonSpace):
    x1: int = 1
    x2: int = 2
    secert: SecretStr = SecretStr("111")
    x3: None = None
    x4: bool = True
    x5: dict = Field(
        default_factory=lambda: {
            "path": "/usr/bin",
            "query": 'SELECT * FROM "users"',
            "command": "echo $HOME",
            "command1": "echo $HOME",
            "command2": "echo $HOME",
            "command3": "echo $HOME; echo $HOME;echo $HOME;echo $HOME",
        }
    )
    x6: str = """
    this
    is
    multi
    line
    """


bakebook = MyPythonSpace()
