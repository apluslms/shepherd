import sys
from datetime import datetime
from enum import Enum

from apluslms_roman.observer import BuildObserver, Phase, Message

from apluslms_shepherd.build.models import BuildStep, BuildState, Build, BuildLog
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
        super().__init__()
        self._phase = Phase.NONE
        self.stream = stream or sys.stdout
        self.data = data

    def _message(self, phase, type_, step=None, state=None, data=None):
        print('New msg:phase {}, type:{} step: {} state: {}'.format(phase, type_, step, state))
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
        elif type_ in [Message.CONTAINER_MSG, type_ == Message.MANAGER_MSG]:
            # This is a task from roman.
            fmt = '{} >> {}'
            output = fmt.format(phase_s, str(data).rstrip()) + '\n'
            self.data[-1] = output
            celery.send_task('apluslms_shepherd.celery_tasks.build.tasks.update_state', queue='celery_state',
                             args=self.data)
        else:
            fmt = '{} {}'
        if not data: data = type_.name.lower()
        self.stream.write(fmt.format(phase_s, str(data).rstrip()) + '\n')

    def update_database(self, course_id, number, step, state, log=None):
        now = datetime.utcnow()
        build_log = None
        build = None
        # We create new Build and BuildLog when it is the start of the first step, and only the first step has
        # publish state.

        # We don't catch the task publish signal form the second task (after task CLONE). That's because the celery
        # will be publish all taks before the first task runs, thus the state in of Build table will be changed too
        # early. In this case, we create the BuildLog and change the state in the Build table of Build task in this
        # function.
        if step == BuildStep.CLONE and state == BuildState.PUBLISH:
            build = Build(course_id=course_id, start_time=now,
                          state=BuildState.PUBLISH,
                          step=BuildStep.CLONE, number=number)
            build_log = BuildLog(
                course_id=course_id,
                start_time=now,
                number=number,
                step=BuildStep.CLONE,
                log_text=log
            )
        # We create new build log when it comes to next step
        elif state == BuildState.RUNNING and step != BuildStep.CLONE:
            build_log = BuildLog(
                course_id=course_id,
                start_time=now,
                number=number,
                step=step,
                log_text=log
            )
            build = Build.query.filter_by(course_id=course_id, number=number).first()
            build.state = state
            build.step = step
        # If task finished, set end time for BuildLog, if the current step is the last step,
        # set end time for Build as well
        elif state == BuildState.SUCCESS or BuildState.FAILED:
            build = Build.query.filter_by(course_id=course_id,
                                          number=number).first()
            # Get current build_log, filter condition "step" is different according to the task
            build_log = BuildLog.query.filter_by(course_id=course_id,
                                                 number=number,
                                                 step=step).first()
            build.state = state
            build_log.log_text = log
            build.end_time = now if step == BuildStep.CLEAN else None
            build_log.end_time = now
        if build_log is not None and build is not None:
            # Submit the changes to db
            db.session.add(build_log)
            db.session.add(build)
            db.session.commit()
            self.stream.write('Current state write to database: build id:{}, build number: {}, step: {}, state: {}'
                              .format(course_id, number, step.name, state.name))

    def state_update(self, course_id, build_number, step, state, log=None):
        state_name = state.name if state is not None else None
        state_list = [course_id, build_number, step.name, state_name, log]
        self._message(self._phase, ShepherdMessage.STATE_UPDATE, step, state, state_list)
