class GitRepo(object):
    def __init__(self, ssh, http, branch='master'):
        self.ssh = ssh
        self.http = http
        self.branch = branch

    def pull(self, use_ssh=True):
        if use_ssh:
            pass
            # TODO:Git pull with ssh
        else:
            pass
            # TODO:Git pull with http
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

