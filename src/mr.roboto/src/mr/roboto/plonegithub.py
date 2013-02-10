from github import Github


DEV_TEAM_ID = 14533


class PloneGithub(Github):

    @property
    def organization(self):
        return self.get_organization('plone')

    @property
    def developer_team(self):
        return self.organization.get_team(DEV_TEAM_ID)

    def is_core_contributor(self, user_name):
        user = self.get_user(user_name)
        return self.developer_team.has_in_members(user)

    def get_pull_request(self, pull_id):
        return self.get_pull(pull_id)

    def add_comment_to_pull_request(self, pull_id, comment):
        pull = self.get_pull_request(pull_id)
        pull.create_comment(comment)

