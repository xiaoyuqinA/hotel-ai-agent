"""Hotel Configuration 异常定义。"""


class HotelConfigError(Exception):
    """配置错误基类。"""

    def __init__(self, hotel_id: str, message: str):
        self.hotel_id = hotel_id
        super().__init__(f"[{hotel_id}] {message}")


class HotelConfigNotFound(HotelConfigError):
    """配置不存在。"""

    def __init__(self, hotel_id: str):
        super().__init__(hotel_id, f"Hotel config not found: {hotel_id}")


class HotelConfigAlreadyExists(HotelConfigError):
    """酒店配置已存在。"""

    def __init__(self, hotel_id: str):
        super().__init__(hotel_id, f"Hotel config already exists: {hotel_id}")
