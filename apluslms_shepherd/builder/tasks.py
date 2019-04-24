from apluslms_shepherd.builder import app as celery_app


@celery_app.task(bind=True, default_retry_delay=10)
def pull_and_build(Gitreop, is_ssh=True):
    """
    Pull repo and complie the course
    :param Gitreop:
    :param is_ssh:
    :return:
    """
    try:
        pass
        # TODO: pull repo
    except ConnectionError:
        pass
