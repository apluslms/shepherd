from enum import Enum

from apluslms_shepherd import celery
from apluslms_shepherd.build.models import BuildLog, Build, BuildState, BuildStep


class ShepherdMessage(Enum):
    START = 0
    UPDATE = 9
    MSG = 9
    END = 10


class BrokerClient:
    def __init__(self, task: str, queue: str, course_info: dict):
        self.queue = queue
        self.task = task
        self.course_info = course_info

    def notify(self, log):
        """
        Send log to frontend
        :param log: List of dict which contains state and log
        :return:
        """
        for each in log:
            log_context = {**self.course_info, **each}
            celery.send_task(self.task, queue=self.queue, kwargs=log_context)


def get_logger(session, build_info: dict):
    """
    This function is for observer to write the data to database, will be called in in the end of each steps.
    :param session: Database session
    :param build_info: a dictionary, key must include: course_id, number.
    :return:
    """

    def log(step, start, end, result: BuildState, logs: str, roman_step=None):
        # If it is the last step, then write end time and result to Build.
        # Build entry is created in publish signal, while each buildlog only be created in then end of steps.
        if step == BuildStep.CLEAN:
            build = Build(**build_info, end_time=end, result=result)
            session.merge(build)
            session.commit()
        log_entry = BuildLog(**build_info, step=step, start_time=start, end_time=end, result=result, log_text=logs,
                             roman_step=roman_step)
        session.add(log_entry)
        session.commit()
    return log
