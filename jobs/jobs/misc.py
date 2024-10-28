import functools
import traceback
import typing as t

import schedule


class JobException(Exception):
    def __init__(self, code: t.Optional[int] = None, message: t.Optional[t.Any] = None) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def catch_exceptions(cancel_on_failure=False):  # type: ignore[no-untyped-def]
    def catch_exceptions_decorator(job_func):  # type: ignore[no-untyped-def]
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            try:
                return job_func(*args, **kwargs)
            # pylint: disable=broad-except
            except Exception:  # noqa: E722

                print(traceback.format_exc())
                if cancel_on_failure:
                    return schedule.CancelJob

        return wrapper

    return catch_exceptions_decorator
