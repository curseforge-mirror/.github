import asyncio


def async_retry(attempts=3, delay=2):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            nonlocal attempts, delay
            exception = None
            for _ in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    exception = e
                    await asyncio.sleep(delay)
            raise exception

        return wrapper

    return decorator
