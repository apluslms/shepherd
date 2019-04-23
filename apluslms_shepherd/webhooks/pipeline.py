class GitPipeline(object):
    def __init__(self, repo, branch='master'):
        self.repo = repo
        self.branch = branch

    def pull(self):
        """
        pull the content of repo
        """
        pass

    def build(self):
        """
        Build the course material
        with roman
        """
        pass
