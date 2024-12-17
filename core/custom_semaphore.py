import asyncio


class TimedReqsSemaphore:
    def __init__(self, limit, reset_interval=60):
        self.limit = limit
        self.reset_interval = reset_interval
        self.semaphore = asyncio.BoundedSemaphore(limit)

        async def reset_timer():
            while True:
                try:
                    await asyncio.sleep(reset_interval)
                    for _ in range(limit):
                        self.semaphore.release()
                except asyncio.CancelledError:
                    break

        self.resetTimer = asyncio.create_task(reset_timer())

    async def __aenter__(self):
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def cancel(self):
        self.resetTimer.cancel()

    def __repr__(self):
        return f"TimedReqsSemaphore(limit={self.limit},reset_interval={self.reset_interval})"


class FlowSemaphore:
    def __init__(self, limit, estimate_once, reset_interval=60):
        if limit < estimate_once:
            raise RuntimeError("limit must greater than estimate_once!")
        self.limit = limit  # 一段时间内允许的流量上限
        self.count = limit  # 流量计数器
        self.reset_interval = reset_interval
        self.estimate_once = estimate_once  # 每次进入上下文管理器最多消耗的流量
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.lock)

        async def reset_timer():
            while True:
                try:
                    await asyncio.sleep(reset_interval)
                    async with self.lock:
                        self.count = self.limit
                        # 保守地唤醒阻塞的协程
                        # 唤醒这么多协程一定不会触发流量限流
                        self.condition.notify(n=int(self.limit / self.estimate_once))
                except asyncio.CancelledError:
                    break

        self.resetTimer = asyncio.create_task(reset_timer())

    async def __aenter__(self):
        # 每次进入不一定会消耗estimate这么多的流量
        # 因此在多次进入的情况下，流量消耗一定比预估得少
        # 这样就可以在不触发流量限流的情况下 尽可能多的请求
        async with self.lock:
            self.count -= self.estimate_once
            if self.count < 0:
                await self.condition.wait()
        return self

    async def flow(self, n):
        # 该函数必须调用 以正确监测流量消耗
        async with self.lock:
            self.count -= n
            self.count += self.estimate_once
            if self.count > 0:
                self.condition.notify()  # 这里唤醒一个因流量不足而阻塞的协程

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def cancel(self):
        self.resetTimer.cancel()

    def __repr__(self):
        return f"FlowSemaphore(limit={self.limit},estimate_once={self.estimate_once},reset_interval={self.reset_interval})"
