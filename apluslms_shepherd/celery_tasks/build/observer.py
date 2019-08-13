import sys
from datetime import datetime
from enum import Enum

from apluslms_roman.observer import BuildObserver

from apluslms_shepherd.build.models import BuildAction, BuildState, Build, BuildLog
from apluslms_shepherd.extensions import celery, db


class ShepherdMessage(Enum):
    ENTER = 0
    START_STEP = 1
    END_STEP = 2
    MANAGER_MSG = 11
    CONTAINER_MSG = 12
    STATE_UPDATE = 13


class ShepherdObserver(BuildObserver):
    def __init__(self, data=None, stream=None):
        self.stream = stream or sys.stdout
        self.data = data

    def _message(self, phase, type_, step=None, data=None):
        if type_ == ShepherdMessage.ENTER: return
        phase_s = '{} {}'.format(phase.name, step) if step is not None else phase.name
        if type_ == ShepherdMessage.CONTAINER_MSG:
            fmt = '{} >> {}'
        elif type_ == ShepherdMessage.MANAGER_MSG:
            fmt = '{} : {}'
        elif type_ == ShepherdMessage.STATE_UPDATE:
            fmt = '{} {}'
            celery.send_task('apluslms_shepherd.celery_tasks.build.tasks.update_state', queue='celery_state',
                             args=data)
        elif type_.value == 12:
            fmt = '{} >> {}'
            output = fmt.format(phase_s, str(data).rstrip()) + '\n'
            self.data[-1] = output
            celery.send_task('apluslms_shepherd.celery_tasks.build.tasks.update_state', queue='celery_state',
                             args=self.data)
        else:
            fmt = '{} {}'
        if not data: data = type_.name.lower()
        self.stream.write(fmt.format(phase_s, str(data).rstrip()) + '\n')

    def update_database(self, instance_id, number, step, state, log=None):
        self._state = step
        now = datetime.utcnow()
        build_log = None
        build = None
        # We create new Build and BuildLog when it is the start of the first step, and only the first step has
        # publish state.

        # We don't catch the task publish signal form the second task (after task CLONE). That's because the celery
        # will be publish all taks before the first task runs, thus the state in of Build table will be changed too
        # early. In this case, we create the BuildLog and change the state in the Build table of Build task in this
        # function.
        if step == BuildAction.CLONE and state == BuildState.PUBLISH:
            build = Build(instance_id=instance_id, start_time=now,
                          state=BuildState.PUBLISH,
                          action=BuildAction.CLONE, number=number)
            build_log = BuildLog(
                instance_id=instance_id,
                start_time=now,
                number=number,
                action=BuildAction.CLONE,
                log_text=log
            )
        # We create new build log when it comes to next step
        elif state == BuildState.RUNNING and step != BuildAction.CLONE:
            build_log = BuildLog(
                instance_id=instance_id,
                start_time=now,
                number=number,
                action=step,
                log_text=log
            )
            build = Build.query.filter_by(instance_id=instance_id, number=number).first()
            build.state = state
            build.action = step
        # If task finished, set end time for BuildLog, if the current step is the last step,
        # set end time for Build as well
        elif state == BuildState.FINISHED or BuildState.FAILED:
            build = Build.query.filter_by(instance_id=instance_id,
                                          number=number).first()
            # Get current build_log, filter condition "action" is different according to the task
            build_log = BuildLog.query.filter_by(instance_id=instance_id,
                                                 number=number,
                                                 action=step).first()
            build.state = state
            build_log.log_text = log
            build.end_time = now if step == BuildAction.CLEAN else None
            build_log.end_time = now
        if build_log is not None and build is not None:
            # Submit the changes to db
            db.session.add(build_log)
            db.session.add(build)
            db.session.commit()
            self.stream.write('Current state write to database: build id:{}, build number: {}, step: {}, state: {}'
                              .format(instance_id, number, step.name, state.name))

    def state_update(self, instance_id, build_number, step, state, log=None):
        self._state = step
        state_name = state.name if state is not None else None
        state_list = [instance_id, build_number, step.name, state_name, log]
        self._message(self._state, ShepherdMessage.STATE_UPDATE, step, state_list)
