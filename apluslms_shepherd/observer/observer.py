from datetime import datetime
from typing import Callable

from apluslms_roman.observer import BuildObserver, Message

from apluslms_shepherd.build.models import BuildStep, BuildState
from apluslms_shepherd.observer.utils import BrokerClient, ShepherdMessage
from celery.utils.log import get_task_logger

celery_logger = get_task_logger(__name__)


class ShepherdObserver(BuildObserver):
    def __init__(self, logger: Callable = None, broker: BrokerClient = None):
        super().__init__()
        self.logger = logger
        self.broker = broker
        self.starts = {}
        self.logs = {}

    def set_logger(self, logger: Callable):
        self.logger = logger

    def set_broker(self, broker: BrokerClient):
        self.broker = broker

    def _message(self, phase, type_, step=None, state=None, data=None):
        if type_ == ShepherdMessage.START:
            self.starts[step] = datetime.utcnow()
        if type_ == ShepherdMessage.END:
            end = datetime.utcnow()
            start = self.starts.get(step, 0)
            # The log of each step should be like {'step1':[{'state': 'state for log 1', 'step': 'step for log1',
            # 'log': 'log 1 content' }, {same dict for log2}, ...]}
            logs = self.logs.get(step, [])
            # Write this log entry to db
            self.logger(step, start, end, state, '\n'.join([l['log'] for l in logs]))
            # Send all left message to frontend logger
            self.broker.notify(self.logs[step])
            # Empty log cache after send log to frontend.
            self.logs[step] = []
        if type_ == ShepherdMessage.UPDATE:
            # Only update frontend, no log.
            frontend_msg = [{'step': step.name, 'state': state.name, 'roman_step': None, 'log': ''}]
            self.broker.notify(frontend_msg)
        if type_ == ShepherdMessage.MSG:
            fmt = '{} {}'
            # Composing a log entry
            log_txt = fmt.format(phase.name, str(data).rstrip())
            frontend_msg = {'step': step.name, 'state': state.name, 'roman_step': None, 'log': log_txt}
            self.logs.setdefault(step, []).append(frontend_msg)
            # We store the course info in logger function
            # Notify broker every 10 lines of log
            if len(self.logs[step]) > 10:
                self.broker.notify(self.logs[step])
                self.logs[step] = []
        if type_ == Message.CONTAINER_MSG:
            fmt = '{} >> {}'
            log_txt = fmt.format(phase.name, str(data).rstrip())
            celery_logger.info(log_txt)
            frontend_msg = {'step': BuildStep.BUILD.name, 'state': BuildState.RUNNING.name, 'roman_step': str(step),
                            'log': log_txt}
            self.logs.setdefault(BuildStep.BUILD, []).append(frontend_msg)
            # Notify broker every 10 lines of log
            if len(self.logs[BuildStep.BUILD]) > 10:
                self.broker.notify(self.logs[BuildStep.BUILD])
                self.logs[BuildStep.BUILD] = []

    def shepherd_step_start(self, step):
        self._message(self._phase, ShepherdMessage.START, step)

    def shepherd_step_end(self, step, state):
        self._message(self._phase, ShepherdMessage.END, step, state)

    def shepherd_msg(self, step, state, log):
        self._message(self._phase, ShepherdMessage.MSG, step, state, log)
