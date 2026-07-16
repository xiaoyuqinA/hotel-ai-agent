from agents import TResponseInputItem


class InMemorySession:
    """内存实现的 Session，用于测试和轻量场景"""

    def __init__(self) -> None:
        self._items: list[TResponseInputItem] = []

    async def get_items(self, limit: int | None = None):
        if limit is None:
            return self._items.copy()
        return self._items[-limit:]

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        self._items.extend(items)

    async def clear_session(self) -> None:
        self._items.clear()

    async def pop_item(self) -> TResponseInputItem | None:
        return self._items.pop() if self._items else None