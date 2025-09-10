from .base import PullRequestSubscriber
from mr.roboto.events import NewPullRequest
from mr.roboto.events import UpdatedPullRequest
from pyramid.events import subscriber


IGNORE_NO_AGREEMENT = (
    "documentation",
    "icalendar",
    "planet.plone.org",
    "training",
)


@subscriber(NewPullRequest, UpdatedPullRequest)
class ContributorsAgreementSigned(PullRequestSubscriber):
    def __init__(self, event):
        self.cla_url = "https://plone.org/foundation/contributors-agreement"  # noqa
        self.cla_email = "agreements@plone.org"
        self.github_help_setup_email_url = "https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/adding-an-email-address-to-your-github-account"  # noqa
        self.github_help_commit_email = "https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address"
        self.status_context = "Plone Contributors Agreement verifier"

        super().__init__(event)

    def run(self):
        """Check if all users involved in a pull request have signed the CLA"""
        if self.repo_name in IGNORE_NO_AGREEMENT:
            self.log("no need to sign contributors agreement")
            return

        json_data = self.get_json_commits()
        if not json_data:
            return

        not_foundation, unknown = self.check_membership(json_data)

        # get the pull request and last commit
        last_commit = self.get_pull_request_last_commit()

        status = "success"
        status_message = "All users have signed it"
        if not_foundation or unknown:
            status = "error"
            status_message = "Some users need to sign it"

        if not_foundation:
            # add a message mentioning all users that have not signed the
            # Contributors Agreement
            users = " @".join(not_foundation)
            msg = (
                f"@{users} you need to sign the Plone Contributor "
                "Agreement to merge this pull request."
                "\n\n"
                f"Learn about the Plone Contributor Agreement: {self.cla_url}"
                "\n\n"
                "If you have already signed the agreement, "
                "please allow a week for your agreement to be processed.\n"
                "Once it is processed, you will receive an email invitation "
                "to join the `plone` GitHub organization as a Contributor."
                "\n\n"
                "If after a week you have not received an invitation, then "
                f"please contact {self.cla_email}."
            )
            self.g_issue.create_comment(body=msg)

        if unknown:
            # add a message mentioning all unknown users,
            # but mention each of them only once
            users = ", ".join(set(unknown))
            self.log(f"{users} missing contributors agreement")
            msg = (
                f"{users} the email address in your commit does not match an "
                "email in your GitHub account. Thus it is impossible to "
                "determine whether you have signed the Plone Contributor "
                "Agreement, which is required to merge this pull request."
                "\n\n"
                f"Learn about the Plone Contributor Agreement: {self.cla_url} "
                "\n\n"
                "If you have sent in your Plone Contributor Agreement, "
                "and received and accepted an invitation to join the "
                "Plone GitHub organization, then you might need to either add "
                "the email address on your Agreement to your GitHub account "
                "or change the email address in your commits. If you need to "
                "do the latter, then you should squash the commits with your "
                "matching email and push them."
                "\n\n"
                "Add more emails to your GitHub account:\n"
                f"{self.github_help_setup_email_url}"
                "\n\n"
                "Change the email address in your commits:\n"
                f"{self.github_help_commit_email}"
            )
            self.g_issue.create_comment(body=msg)

        last_commit.create_status(
            status,
            target_url=self.cla_url,
            description=status_message,
            context=self.status_context,
        )
        self.log(f"Contributors Agreement report: {status}")
