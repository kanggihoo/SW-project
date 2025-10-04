import asyncio
from contextlib import asynccontextmanager


def test():
    return test_async()


@asynccontextmanager
async def test_async():
    yield 10


async def main():
    async with test_async() as a:
        print(a)


if __name__ == '__main__':
    asyncio.run(main())
