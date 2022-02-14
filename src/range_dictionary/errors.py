class RangeDictError(Exception):
    pass


class InvalidMappingError(RangeDictError):
    def __init__(self):
        super().__init__(
            "argument for RangeDict must be a dictionary with iterables of length 2 as keys"
        )


class KeyNotFoundError(RangeDictError):
    def __init__(self, key):
        super().__init__(f"key {key} not found in RangeDict")


class NotNumberError(RangeDictError):
    def __init__(self):
        super().__init__("Ranges can only be compared with numbers")


class NotRangeError(RangeDictError):
    def __init__(self):
        super().__init__("arguments must be Range objects")


class OverlapError(RangeDictError):
    def __init__(self, key1, key2):
        super().__init__(f"RangeDict keys cannot overlap ({key1} and {key2})")


class UnknownDirectionError(RangeDictError):
    def __init__(self, direction):
        super().__init__(f"unknown direction {direction}")


class RangeValueError(RangeDictError):
    pass
