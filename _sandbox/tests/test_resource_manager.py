import asyncio
import time
import pytest

from zena_mode.resource_manager import ResourceManager


def test_run_in_thread_future_success(loop=None):
    rm = ResourceManager()

    async def runner():
        fut = rm.run_in_thread_future(lambda x: x + 1, 41)
        res = await fut
        assert res == 42

    asyncio.get_event_loop().run_until_complete(runner())


def test_run_in_thread_future_exception():
    rm = ResourceManager()

    def raise_exc():
        raise ValueError("boom")

    async def runner():
        fut = rm.run_in_thread_future(raise_exc)
        with pytest.raises(ValueError):
            await fut

    asyncio.get_event_loop().run_until_complete(runner())


def test_max_workers_enforced():
    rm = ResourceManager()

    # create a slow function
    def slow():
        time.sleep(0.2)
        return 1

    async def runner():
        # start several futures with max_workers=1 to force rejection
        fut1 = rm.run_in_thread_future(slow, max_workers=1)
        # second should raise at submission time
        with pytest.raises(RuntimeError):
            rm.run_in_thread_future(slow, max_workers=1)
        await fut1

    asyncio.get_event_loop().run_until_complete(runner())
