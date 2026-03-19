from bake import Bakebook


class GitHubActionsEnvVars(Bakebook):
    ci: bool = False
    github_actions: bool = False
