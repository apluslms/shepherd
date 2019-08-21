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
        self.log_cache = {}
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
            # Send all left message to frontend logger
            self.broker.notify(self.log_cache[step])
            # Append these sent log to logs, which has all previous logs.
            self.logs.setdefault(step, []).extend(self.log_cache[step])
            # The log of each step should be like {'step1':[{'state': 'state for log 1', 'step': 'step for log1',
            # 'log': 'log 1 content' }, {same dict for log2}, ...]}
            logs = self.logs.get(step, [])
            # Write all log in this step log entry to db
            self.logger(step, start, end, state, '\n'.join([l['log'] for l in logs]))
            self.log_cache[step] = []
        if type_ == ShepherdMessage.UPDATE:
            # Only update frontend, no log.
            frontend_msg = [{'step': step.name, 'state': state.name, 'roman_step': None, 'log': ''}]
            self.broker.notify(frontend_msg)
        if type_ == ShepherdMessage.MSG:
            fmt = '{} {}'
            # Composing a log entry
            log_txt = fmt.format(phase.name, str(data).rstrip())
            frontend_msg = {'step': step.name, 'state': state.name, 'roman_step': None, 'log': log_txt}
            self.log_cache.setdefault(step, []).append(frontend_msg)
            # We store the course info in logger function
            # Notify broker every 10 lines of log
            if len(self.log_cache[step]) > 10:
                self.broker.notify(self.log_cache[step])
                # Append log in cache to logs, which has all previous logs for every step.
                self.logs.setdefault(step, []).extend(self.log_cache[step])
                # Empty cache
                self.log_cache[step] = []
        if type_ == Message.CONTAINER_MSG:
            fmt = '{} >> {}'
            log_txt = fmt.format(phase.name, str(data).rstrip())
            celery_logger.info(log_txt)
            frontend_msg = {'step': BuildStep.BUILD.name, 'state': BuildState.RUNNING.name, 'roman_step': str(step),
                            'log': log_txt}
            self.log_cache.setdefault(BuildStep.BUILD, []).append(frontend_msg)
            # Notify broker every 10 lines of log
            if len(self.log_cache[BuildStep.BUILD]) > 10:
                self.broker.notify(self.log_cache[BuildStep.BUILD])
                self.logs.setdefault(BuildStep.BUILD, []).extend(self.log_cache[BuildStep.BUILD])
                self.log_cache[BuildStep.BUILD] = []

    def shepherd_step_start(self, step):
        self._message(self._phase, ShepherdMessage.START, step)

    def shepherd_step_end(self, step, state):
        self._message(self._phase, ShepherdMessage.END, step, state)

    def shepherd_msg(self, step, state, log):
        self._message(self._phase, ShepherdMessage.MSG, step, state, log)
