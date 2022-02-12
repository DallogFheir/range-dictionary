import operator
from typing import Union
from .errors import (
    NotNumberError,
    NotRangeError,
    RangeValueError,
)


class RangeMeta(type):
    def __getitem__(cls, args):
        # allows to init Range with square brackets, like Range[1, 2]
        if not isinstance(args, tuple) or len(args) != 2:
            raise RangeValueError(
                "You must give two arguments separated by comma to initialize a Range with square brackets."
            )

        start, end = args
        return cls(start, end, closed_left=True, closed_right=True)


class Range(metaclass=RangeMeta):
    def __init__(
        self,
        start: Union[int, float],
        end: Union[int, float],
        closed_left: bool = False,
        closed_right: bool = False,
    ):
        """An object representing a range, either closed or open.

        Args:
            start (Union[int, float]): start of the range
            end (Union[int, float]): end of the range
            closed_left (bool, optional): if range is closed at the start. Defaults to False.
            closed_right (bool, optional): if range is closed at the end. Defaults to False.

        Raises:
            RangeValueError: if range start or end are not numbers, end is greater than start, or range is closed at infinity
        """
        if not (isinstance(start, int) or isinstance(start, float)) or not (
            isinstance(end, int) or isinstance(end, float)
        ):
            raise RangeValueError("Range start and end must be numbers.")

        if start > end:
            raise RangeValueError("Start must be less than or equal to end.")

        infs = (float("-inf"), float("inf"))
        if (start in infs and closed_left) or (end in infs and closed_right):
            raise RangeValueError("Range cannot be closed at infinity")

        self.start = start
        self.end = end

        self.closed_left = closed_left
        if not closed_left:
            self._left_less = operator.lt
            self._left_greater = operator.ge
        else:
            self._left_less = operator.le
            self._left_greater = operator.gt

        self.closed_right = closed_right
        if not closed_right:
            self._right_less = operator.lt
            self._right_reverse_less = operator.le
        else:
            self._right_less = operator.le
            self._right_reverse_less = operator.lt

    def __repr__(self):
        left = "[" if self.closed_left else "("
        right = "]" if self.closed_right else ")"
        return f"Range{left}{self.start}; {self.end}{right}"

    def __contains__(self, number: Union[int, float]):
        if not (isinstance(number, int) or isinstance(number, float)):
            raise NotNumberError

        return self._left_less(self.start, number) and self._right_less(
            number, self.end
        )

    def __eq__(self, other: "Range"):
        return (
            self.start == other.start
            and self.end == other.end
            and self.closed_left == other.closed_left
            and self.closed_right == other.closed_right
        )

    def __hash__(self):
        return hash((self.start, self.end, self.closed_left, self.closed_right))

    def __lt__(self, number: Union[int, float]):
        if not (isinstance(number, int) or isinstance(number, float)):
            raise NotNumberError

        return self._right_reverse_less(self.end, number)

    def __gt__(self, number: Union[int, float]):
        if not (isinstance(number, int) or isinstance(number, float)):
            raise NotNumberError

        return self._left_greater(self.start, number)

    def overlaps(self, other: "Range") -> bool:
        """Checks if two Ranges overlap.

        Args:
            other (Range): Range object to compare

        Raises:
            NotRangeError: if other is not a Range object

        Returns:
            bool: if two Ranges overlap or not
        """
        if not isinstance(other, Range):
            raise NotRangeError

        if self.start == other.start:
            this_range = self if self.closed_left else other
            other_range = self if not self.closed_left else other
        elif self.start > other.start:
            this_range = other
            other_range = self
        else:
            this_range = self
            other_range = other

        left_op = operator.ge if self.closed_left ^ other.closed_left else operator.gt
        right_op = (
            operator.lt
            if not (other_range.closed_left and this_range.closed_right)
            else operator.le
        )

        return left_op(other_range.start, this_range.start) and right_op(
            other_range.start, this_range.end
        )
