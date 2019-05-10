from apluslms_shepherd.extensions import celery


def get_current_build_number_list():
    inspector = celery.control.inspect()
    task_list = inspector.active()
    task_build_number_list = []
    for each_worker in task_list.values():
        task_build_number_list = [int(eval(each_task['args'])[-1]) for each_task in each_worker]
        print(task_build_number_list)
    return task_build_number_list

