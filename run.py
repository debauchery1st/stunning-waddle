import signal
import os
import subprocess
from threading import Thread, Event
from functools import partial
from time import sleep


class Task(Thread):
    def __init__(self, *args, **kwargs):
        super(Task, self).__init__(*args, **kwargs)
        self.shutdown_flag = Event()

    def run(self):
        print("Thread {tid} started".format(tid=self.ident))
        while not self.shutdown_flag.is_set():
            self._target(*self._args, **self._kwargs)
            self.shutdown_flag.set()


def shutdown(*args):
    _, o = args
    t = getattr(o, 'f_locals').get('self')
    if t:
        while t.is_alive():
            t.join()
        print("Thread {tid} stopped".format(tid=t.ident))
        del t
    else:
        print('\n[CTRL-C to shutdown server]\n')
    return


def start():
    threads = []
    if os.name in ['posix', 'darwin']:
        cli = "sh client.sh"
    else:
        cli = ''  # not tested on windows yet.
    server_task = Task(name='ChatServer', target=partial(subprocess.call, ["python3", "server.py", "64007"]))
    threads.append(server_task)
    server_task.start()
    sleep(.123)
    client_task = Task(name='ChatClient', target=partial(subprocess.call, cli.split()))
    threads.append(client_task)
    client_task.start()
    sig = signal.SIGTERM if os.name == 'posix' else signal.CTRL_C_EVENT
    while not client_task.shutdown_flag.is_set():
        sleep(.1)
    client_task.join()
    print("Thread {tid} stopped".format(tid=client_task.ident))
    del client_task
    os.kill(os.getpid(), sig.SIGINT)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    start()
