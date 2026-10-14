import functools
import traceback
import typing as t

import schedule


class JobException(Exception):
    def __init__(self, code: t.Optional[int] = None, message: t.Optional[t.Any] = None) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def catch_exceptions(cancel_on_failure=False):  # noqa: ANN001, ANN201
    def catch_exceptions_decorator(job_func):  # noqa: ANN001, ANN202
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            try:
                return job_func(*args, **kwargs)
            except Exception:
                print(traceback.format_exc())
                if cancel_on_failure:
                    return schedule.CancelJob

        return wrapper

    return catch_exceptions_decorator
