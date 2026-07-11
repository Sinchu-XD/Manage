from asyncio import gather, to_thread
import requests


def get(url: str, *args, **kwargs):
    resp = requests.get(url, *args, **kwargs)

    if resp.status_code != 200:
        return resp.status_code

    try:
        data = resp.json()
    except Exception:
        data = resp.text

    return data


def head(url: str, *args, **kwargs):
    resp = requests.head(url, *args, **kwargs)

    try:
        data = resp.json()
    except Exception:
        data = resp.text

    return data


def post(url: str, *args, **kwargs):
    resp = requests.post(url, *args, **kwargs)

    if resp.status_code != 200:
        return resp.status_code

    try:
        data = resp.json()
    except Exception:
        data = resp.text

    return data


async def multiget(url: str, times: int, *args, **kwargs):

    return await gather(
        *[to_thread(get, url, *args, **kwargs) for _ in range(times)]
    )


async def multihead(url: str, times: int, *args, **kwargs):

    return await gather(
        *[to_thread(head, url, *args, **kwargs) for _ in range(times)]
    )


async def multipost(url: str, times: int, *args, **kwargs):

    return await gather(
        *[to_thread(post, url, *args, **kwargs) for _ in range(times)]
    )


def resp_get(url: str, *args, **kwargs):
    return requests.get(url, *args, **kwargs)


def resp_post(url: str, *args, **kwargs):
    return requests.post(url, *args, **kwargs)
