from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_NO_COLOR = "NO_COLOR"
ENV__BAKE_REINVOKED = "_BAKE_REINVOKED"


class BakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    ci: bool = False
    github_actions: bool = False
    no_color: bool = False
    bake_reinvoked: bool = Field(default=False, alias="_BAKE_REINVOKED")

    def should_use_colors(self) -> bool:
        return self.no_color


bake_settings = BakeSettings()
