import blinker

on_starting = blinker.Signal()
on_started = blinker.Signal()
on_stopping = blinker.Signal()
on_stopped = blinker.Signal()
on_stdin_message = blinker.Signal()
on_stdout_message = blinker.Signal()
on_stderr_message = blinker.Signal()
