from github import Github
import Queue
import threading
import logging

logger = logging.getLogger('mr.roboto')

DEV_TEAM_ID = 14533


class MessageWriter(threading.Thread):
    """
    Worker that writes the comments on gh
    """

    def __init__(self, queue, gh):
        threading.Thread.__init__(self)
        self.queue = queue
        self.gh = gh

    def run(self):
        while True:
            # Get the message to write
            todo = self.queue.get()
            if 'type' in todo and todo['type'] == 'add':
                self.add_message(todo)
            elif 'type' in todo and todo['type'] == 'replace':
                self.replace_message(todo)

            self.queue.task_done()

    def add_message(self, todo):
        comment = self.gh.get_commit_comment(todo['repo'], todo['sha'])
        message = comment.body
        message += todo['message']
        logger.info('Add to GH commit ' + todo['sha'] + ' message : ' + message)
        comment.edit(message)

    def replace_message(self, todo):
        comment = self.gh.get_commit_comment(todo['repo'], todo['sha'])
        message = comment.body
        message = message.replace(todo['oldmessage'], todo['message'])
        logger.info('Replace to GH commit ' + todo['sha'] + ' message : ' + todo['message'])
        comment.edit(message)


class PloneGithub(Github):

    def __init__(self, user, passwd):
        self.queue = Queue.Queue()
        self.thread = MessageWriter(self.queue, self)
        self.thread.setDaemon(True)
        self.thread.start()
        self.user = user
        return super(PloneGithub, self).__init__(user, passwd)

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

    # Comment helper funcions

    def get_commit_comment(self, repo, sha):
        """
        We create the comment object
        """
        repo_object = self.get_repo(repo)
        commit = repo_object.get_commit(sha)
        comment_object = None
        for comment in commit.get_comments():
            if comment.user.login == self.user:
                comment_object = comment
        if comment_object is None:
            comment_object = commit.create_comment("Testing information:\n")
        return comment_object

    def add_commit_message(self, repo, sha, message):
        self.queue.put({'type': 'add',
                        'repo': repo, 
                        'sha': sha,
                        'message': message
        })

    def replace_commit_message(self, repo, sha, old_message, message):
        self.queue.put({'type': 'replace',
                        'repo': repo,
                        'sha': sha,
                        'message': message,
                        'oldmessage': old_message
        })
