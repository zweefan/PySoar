from task import Task


class RaceTask(Task):

    def __init__(self, task_information):
        super(RaceTask, self).__init__(task_information)
        self.distances = []

    # def set_task_distances(self)
