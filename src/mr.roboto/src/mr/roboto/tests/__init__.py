def default_settings(github=None, parsed=True, override_settings=None):
    plone = ['5.2', '6.0']
    python = {
        '5.2': ['2.7', '3.6'],
        '6.0': ['3.8', '3.9'],
    }
    github_users = ['mister-roboto', 'jenkins-plone-org']
    if not parsed:
        plone = str(plone)
        python = str(python)
        github_users = str(github_users)
    data = {
        'plone_versions': plone,
        'py_versions': python,
        'roboto_url': 'http://jenkins.plone.org/roboto',
        'api_key': '1234567890',
        'sources_file': 'sources.pickle',
        'checkouts_file': 'checkouts.pickle',
        'github_token': 'secret',
        'jenkins_user_id': 'jenkins-plone-org',
        'jenkins_user_token': 'some-random-token',
        'jenkins_url': 'https://jenkins.plone.org',
        'collective_repos': '',
        'github': github,
        'github_users': github_users,
        'debug': 'True',
    }
    if override_settings:
        data.update(override_settings)
    return data


def minimal_main(override_settings=None, scan_path=''):
    from github import Github
    from pyramid.config import Configurator

    settings = default_settings(override_settings=override_settings)

    config = Configurator(settings=settings)
    config.include('cornice')

    for key, value in settings.items():
        config.registry.settings[key] = value

    config.registry.settings['github_users'] = (
        settings['jenkins_user_id'],
        'mister-roboto',
    )
    config.registry.settings['github'] = Github(settings['github_token'])

    config.scan(scan_path)
    config.end()
    return config.make_wsgi_app()
