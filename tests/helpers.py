import sys

from functools import partial

from returns.contrib.pytest.plugin import _DesiredFunctionFound


class DesiredValueFound(_DesiredFunctionFound):
    def __init__(self, value):
        self.value = value


def trace_func(function_to_search, frame, event, arg):
    if event == "return" and frame.f_code.co_name == function_to_search.__name__:
        raise DesiredValueFound(arg)


def get_return_value(function_to_search, my_flow):
    old_tracer = sys.gettrace()
    sys.setprofile(partial(trace_func, function_to_search))

    try:
        my_flow()
    except DesiredValueFound as e:
        return e.value
    finally:
        sys.settrace(old_tracer)
