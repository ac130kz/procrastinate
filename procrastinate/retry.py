"""
A retry strategy class lets procrastinate know what to do when a job fails: should it
try again? And when?
"""

from typing import Optional, Union

import attr
import pendulum

from procrastinate import exceptions


class BaseRetryStrategy:
    """
    If you want to implement your own retry strategy, you can inherit from this class.
    Children classes only need to implement `get_schedule_in`.
    """

    def get_retry_exception(self, attempts: int) -> Optional[exceptions.JobRetry]:
        schedule_in = self.get_schedule_in(attempts=attempts)
        if schedule_in is None:
            return None

        schedule_at = pendulum.now("UTC").add(seconds=schedule_in)
        return exceptions.JobRetry(schedule_at)

    def get_schedule_in(self, attempts: int) -> Optional[float]:
        """
        Parameters
        ----------
        attempts:
            The number of previous attempts for the current job. The first time
            a job is ran, `attempts` will be 0.

        Returns
        -------
        Optional[float]
            If a job should not be retried, this function should return None.
            Otherwise, it should return the duration after which to schedule the
            new job run, *in seconds*.
        """
        raise NotImplementedError()


@attr.dataclass(kw_only=True)
class RetryStrategy(BaseRetryStrategy):
    """
    The RetryStrategy class should handle classic retry strategies.

    You can mix and match several waiting strategies. The formula is::

        total_wait = wait + lineal_wait * attempts + exponential_wait ** attempts

    Parameters
    ----------
    max_attempts:
        The maximum number of attempts the job should be retried
    wait:
        Use this if you want to use a constant backoff.
        Give a number of seconds as argument, it will be used to compute the backoff.
        (e.g. if 3, then successive runs will wait 3, 3, 3, 3, 3 seconds)
    linear_wait:
        Use this if you want to use a linear backoff.
        Give a number of seconds as argument, it will be used to compute the backoff.
        (e.g. if 3, then successive runs will wait 0, 3, 6, 9, 12 seconds)
    exponential_wait:
        Use this if you want to use an exponential backoff.
        Give a number of seconds as argument, it will be used to compute the backoff.
        (e.g. if 3, then successive runs will wait 1, 3, 9, 27, 81 seconds)
    """

    max_attempts: Optional[int] = None
    wait: float = 0.0
    linear_wait: float = 0.0
    exponential_wait: float = 0.0

    def get_schedule_in(self, attempts: int) -> Optional[float]:
        if self.max_attempts and attempts >= self.max_attempts:
            return None
        wait: float = self.wait
        wait += self.linear_wait * attempts
        wait += self.exponential_wait ** attempts
        return wait


RetryValue = Union[bool, int, RetryStrategy]


def get_retry_strategy(retry: RetryValue) -> Optional[RetryStrategy]:
    if not retry:
        return None

    if retry is True:
        return RetryStrategy()

    if isinstance(retry, int):
        return RetryStrategy(max_attempts=retry)

    return retry