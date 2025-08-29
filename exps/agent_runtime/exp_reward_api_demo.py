import asyncio
import httpx


async def main():
    url = "http://127.0.0.1:8011/agent/reward"
    payload = {
        "question": "地球上最大的哺乳动物是什么？",
        "candidates": ["蓝鲸是最大的哺乳动物。", "最大的哺乳动物是蓝鲸。", "大象是最大的哺乳动物。"],
        "target_answer": "蓝鲸是最大的哺乳动物。"
    }

    timeout = httpx.Timeout(30.0)  # 把超时调到 30 秒
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        print("Status:", resp.status_code)
        print("Response:", resp.text)


if __name__ == "__main__":
    asyncio.run(main())
