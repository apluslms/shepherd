from apluslms_shepherd.extensions import celery
from apluslms_shepherd.config import DevelopmentConfig
from flask import jsonify
import requests


def get_current_build_number_list():
    inspector = celery.control.inspect()
    task_list = inspector.active()
    task_build_number_list = []
    for each_worker in task_list.values():
        task_build_number_list = [int(eval(each_task['args'])[-1]) for each_task in each_worker]
        print(task_build_number_list)
    return task_build_number_list


def update_frontend(instance_id, build_number, action, state):
    celery.send_task('apluslms_shepherd.celery_tasks.tasks.update_state', queue='celery_state',
                     args=[instance_id, build_number, action.name, state.name])


class WebHook(object):
    def __init__(self, course_key, instance_key, build_number, action, state):
        self.action = action.name
        self.state = state.name
        self.course_key = course_key
        self.instance_key = instance_key
        self.build_number = build_number

    def send_to_slack(self):
        """
        Send json request to slack webhook
        """
        pass

    def send_to_frontend(self):
        """
        Send json request to frontend webhook, for updating state display
        """
        requests.post(DevelopmentConfig.BUILD_WEBHOOK_URL,
                      headers={'Webhook-Token': DevelopmentConfig.BUILD_WEBHOOK_TOKEN},
                      json=jsonify(self.course_key, self.instance_key, self.build_number, self.action, self.state))
