from bake import BakebookMixin


class GitHubActionsEnvVars(BakebookMixin):
    ci: bool = False
    github_actions: bool = False
