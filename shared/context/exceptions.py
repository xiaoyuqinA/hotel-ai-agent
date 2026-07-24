"""Hotel context exceptions."""


class HotelContextNotFound(Exception):
    """酒店上下文配置不存在。"""

    def __init__(self, hotel_id: str):
        self.hotel_id = hotel_id
        super().__init__(f"Hotel context not found for hotel_id: {hotel_id}")
