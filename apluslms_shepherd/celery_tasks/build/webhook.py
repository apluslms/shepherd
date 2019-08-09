import requests
from flask import jsonify

from apluslms_shepherd.config import DevelopmentConfig


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
