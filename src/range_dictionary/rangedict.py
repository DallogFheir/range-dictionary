from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
import operator
from typing import Any, Dict, Generator, Iterable, List, Tuple, Union
from .range import Range
from .errors import (
    InvalidMappingError,
    KeyNotFoundError,
    OverlapError,
    UnknownDirectionError,
)

# misc.
ParentNode = namedtuple("ParentNode", ["node", "direction"])


class Direction(Enum):
    LEFT = 0
    RIGHT = 1


# AVL tree
@dataclass
class AVLTreeNode:
    key: Union[Iterable, Range]
    value: Any
    left: Union["AVLTreeNode", None] = None
    right: Union["AVLTreeNode", None] = None
    parent: Union["AVLTreeNode", None] = None
    height_left: int = 0
    height_right: int = 0

    def __repr__(self):
        return f"AVLTreeNode({self.key}, {self.value}, left={self.left}, right={self.right})"


class RangeDict:
    def __init__(
        self,
        mapping: Union[None, Dict[Union[Iterable, Range], Any], "RangeDict"] = None,
    ):
        """A dictionary whose keys are ranges.

        Args:
            mapping (Union[None, dict[Union[Iterable, Range], Any]], optional): Mapping of Range objects, lists or other iterables to any values. Iterables default to Ranges open at both sides. For closed or semi-open ranges, use Range objects. If None, creates an empty RangeDict. Defaults to None.

        Raises:
            InvalidMappingError: provided mapping is invalid according to the above rules
        """
        self._rotations = {
            (Direction.LEFT, Direction.LEFT): self._ll_rotate,
            (Direction.LEFT, Direction.RIGHT): self._lr_rotate,
            (Direction.RIGHT, Direction.LEFT): self._rl_rotate,
            (Direction.RIGHT, Direction.RIGHT): self._rr_rotate,
        }
        self.root = None

        if mapping is None:
            return

        try:
            for k, v in mapping.items():
                if not isinstance(k, Range):
                    start, end = k
                    k = Range[start, end] if isinstance(k, list) else Range(start, end)

                self.insert(k, v)
        except (TypeError, ValueError):
            raise InvalidMappingError from None

    def __repr__(self):
        node_number = len(self.items_sorted())
        return f"RangeDict({node_number} node{'s' if node_number != 1 else ''})"

    def __str__(self):
        if self.root is None:
            return "RangeDict()"

        sorted_items = self.items_sorted()

        if len(sorted_items) > 5:
            items = "\n\t".join(f"{k}: {v}" for k, v in sorted_items[:2])
            items += "\n\t...\n\t"
            items += "\n\t".join(f"{k}: {v}" for k, v in sorted_items[-2:])

        else:
            items = "\n\t".join(f"{k}: {v}" for k, v in sorted_items)

        return "RangeDict({\n\t" + items + "\n})"

    def __getitem__(self, number: Union[int, float]) -> Any:
        cur_node = self.root
        while True:
            if number in cur_node.key:
                return cur_node.value

            if number > cur_node.key:
                if cur_node.right is None:
                    raise KeyNotFoundError(number)

                cur_node = cur_node.right
            else:
                if cur_node.left is None:
                    raise KeyNotFoundError(number)

                cur_node = cur_node.left

    def __setitem__(self, key: Union[Iterable, Range], value: Any):
        self.insert(key, value)

    def __delitem__(self, key: Union[Iterable, Range]):
        self.remove(key)

    def __contains__(self, number: Union[int, float]) -> bool:
        try:
            self[number]
            return True
        except KeyNotFoundError:
            return False

    def __or__(
        self, other: Union["RangeDict", Dict[Union[Iterable, Range], Any]]
    ) -> "RangeDict":
        new_rd = RangeDict()

        for k, v in self.items():
            new_rd.insert(k, v)
        try:
            for k, v in other.items():
                new_rd.insert(k, v)
        except (AttributeError, InvalidMappingError):
            raise InvalidMappingError from None

        return new_rd

    def __ror__(
        self, other: Union["RangeDict", Dict[Union[Iterable, Range], Any]]
    ) -> "RangeDict":
        try:
            return self | other
        except InvalidMappingError:
            raise InvalidMappingError from None

    def __eq__(self, other: Union["RangeDict", Dict[Union[Iterable, Range], Any]]):
        return self.items_sorted() == other.items_sorted()

    def _check_without_updating_heights(self, path: List[ParentNode]) -> None:
        # only check and rebalance the tree, without updating heights
        reverse_path = path[::-1]
        for idx, path_node in enumerate(reverse_path):
            node, direction = path_node
            if direction == Direction.LEFT:
                if abs(node.height_left - node.height_right) == 2:
                    directions = (
                        Direction.LEFT,
                        reverse_path[idx - 1].direction,
                    )
                    self._rotations[directions](node)
            elif direction == Direction.RIGHT:
                if abs(node.height_left - node.height_right) == 2:
                    directions = (
                        Direction.RIGHT,
                        reverse_path[idx - 1].direction,
                    )
                    self._rotations[directions](node)
            else:
                raise UnknownDirectionError(direction)

    def _increase_heights(self, path: List[ParentNode]) -> None:
        reverse_path = path[::-1]

        # don't add height when parent node already had other children
        node, direction = reverse_path[0]
        if (direction == Direction.LEFT and node.right is not None) or (
            direction == Direction.RIGHT and node.left is not None
        ):
            return

        # add height to all nodes in path
        for idx, path_node in enumerate(reverse_path):
            node, direction = path_node
            if direction == Direction.LEFT:
                node.height_left += 1

                # if balance factor is not -1, 0, 1, rotate the tree
                if abs(node.height_left - node.height_right) == 2:
                    directions = (Direction.LEFT, reverse_path[idx - 1].direction)
                    self._rotations[directions](node)
                    return
            elif direction == Direction.RIGHT:
                node.height_right += 1

                # if balance factor is not -1, 0, 1, rotate the tree
                if abs(node.height_left - node.height_right) == 2:
                    directions = (Direction.RIGHT, reverse_path[idx - 1].direction)
                    self._rotations[directions](node)
                    return
            else:
                raise UnknownDirectionError(direction)

    def _decrease_heights(self, path: List[ParentNode]) -> None:
        reverse_path = path[::-1]

        # decrease height from all nodes in path
        for node, direction in reverse_path:
            if direction == Direction.LEFT:
                node.height_left -= 1

                # if balance factor is wrong, rebalance node, its child and its grandchild
                if abs(node.height_left - node.height_right) == 2:
                    child = node.right
                    if node.right.right is None:
                        grandchild = node.right.left
                    elif node.right.left is None:
                        grandchild = node.right.right
                    else:
                        grandchild = (
                            node.right.right
                            if max(
                                node.right.right.height_left,
                                node.right.right.height_right,
                            )
                            > max(
                                node.right.left.height_left,
                                node.right.left.height_right,
                            )
                            else node.right.left
                        )

                    rotation_configuration = (
                        child.parent.direction,
                        grandchild.parent.direction,
                    )
                    self._rotations[rotation_configuration](node)
            elif direction == Direction.RIGHT:
                node.height_right -= 1

                # if balance factor is wrong, rebalance node, its child and its grandchild
                if abs(node.height_left - node.height_right) == 2:
                    child = node.left
                    if node.left.right is None:
                        grandchild = node.left.left
                    elif node.left.left is None:
                        grandchild = node.left.right
                    else:
                        grandchild = (
                            node.left.right
                            if max(
                                node.left.right.height_left,
                                node.left.right.height_right,
                            )
                            > max(
                                node.left.left.height_left, node.left.left.height_right
                            )
                            else node.left.left
                        )

                    rotation_configuration = (
                        child.parent.direction,
                        grandchild.parent.direction,
                    )
                    self._rotations[rotation_configuration](node)
            else:
                raise UnknownDirectionError(direction)

    def _find_predecessor(self, node: AVLTreeNode) -> AVLTreeNode:
        # find the right-most child of the left element
        cur_node = node.left
        while cur_node.right is not None:
            cur_node = cur_node.right

        return cur_node

    def _ll_rotate(self, node: AVLTreeNode) -> None:
        middle_node = node.left

        node.left = middle_node.right
        node.height_left = middle_node.height_right
        if node.parent is None:
            self.root = middle_node
        else:
            direction = node.parent.direction

            if direction == Direction.LEFT:
                node.parent.node.left = middle_node
            elif direction == Direction.RIGHT:
                node.parent.node.right = middle_node
            else:
                raise UnknownDirectionError(direction)
        middle_node.parent, node.parent = node.parent, ParentNode(
            middle_node, Direction.RIGHT
        )
        middle_node.height_right = 1 + max(node.height_left, node.height_right)
        middle_node.right = node

    def _lr_rotate(self, node: AVLTreeNode) -> None:
        middle_node = node.left
        right_node = middle_node.right

        right_node.parent = middle_node.parent
        middle_node.parent = ParentNode(right_node, Direction.LEFT)
        middle_node.right = right_node.left
        middle_node.height_right = middle_node.height_left
        right_node.left = middle_node
        right_node.height_left = 1 + max(
            middle_node.height_left, middle_node.height_right
        )
        node.left = right_node
        node.height_left = 1 + max(right_node.height_left, right_node.height_right)

        self._ll_rotate(node)

    def _rr_rotate(self, node: AVLTreeNode) -> None:
        middle_node = node.right

        node.right = middle_node.left
        node.height_right = middle_node.height_left
        if node.parent is None:
            self.root = middle_node
        else:
            direction = node.parent.direction

            if direction == Direction.LEFT:
                node.parent.node.left = middle_node
            elif direction == Direction.RIGHT:
                node.parent.node.right = middle_node
            else:
                raise UnknownDirectionError(direction)
        middle_node.parent, node.parent = node.parent, ParentNode(
            middle_node, Direction.LEFT
        )
        middle_node.height_left = 1 + max(node.height_left, node.height_right)
        middle_node.left = node

    def _rl_rotate(self, node: AVLTreeNode) -> None:
        middle_node = node.right
        left_node = middle_node.left

        left_node.parent = middle_node.parent
        middle_node.parent = ParentNode(left_node, Direction.RIGHT)
        middle_node.left = left_node.right
        middle_node.height_left = middle_node.height_right
        left_node.right = middle_node
        left_node.height_right = 1 + max(
            middle_node.height_left, middle_node.height_right
        )
        node.right = left_node
        node.height_right = 1 + max(left_node.height_left, left_node.height_right)

        self._rr_rotate(node)

    def print_full(self) -> None:
        if self.root is None:
            return "RangeDict()"

        items = "\n\t".join(f"{k}: {v}" for k, v in self.items_sorted())

        print("RangeDict({\n\t" + items + "\n})")

    def insert(self, key: Union[Iterable, Range], value: Any) -> None:
        """Insert key-value pairs into the RangeDict.

        Args:
            key (Union[Iterable, Range]): key to insert. Must be a Range object, a list or another iterable. Lists default to Ranges closed at both sides, other iterables to Ranges open at both sides. For semi-open ranges, use Range objects.
            value (Any): value associated with the key

        Raises:
            InvalidMappingError: if provided key is invalid according to the above rules
            OverlapError: if key overlaps with another key
        """
        try:
            if not isinstance(key, Range):
                start, end = key
                key = Range[start, end] if isinstance(key, list) else Range(start, end)
        except ValueError:
            raise InvalidMappingError from None

        if self.root is None:
            self.root = AVLTreeNode(key, value)
            return

        cur_node = self.root
        path = []
        while True:
            if key.overlaps(cur_node.key):
                raise OverlapError(key, cur_node.key)
            else:
                op = (
                    operator.le
                    if cur_node.key.closed_left or key.closed_right
                    else operator.lt
                )

                if op(key.end, cur_node.key.start):
                    path.append(ParentNode(cur_node, Direction.LEFT))
                    if cur_node.left is not None:
                        cur_node = cur_node.left
                    else:
                        cur_node.left = AVLTreeNode(
                            key, value, parent=ParentNode(cur_node, Direction.LEFT)
                        )
                        self._increase_heights(path)
                        break
                else:
                    path.append(ParentNode(cur_node, Direction.RIGHT))
                    if cur_node.right is not None:
                        cur_node = cur_node.right
                    else:
                        cur_node.right = AVLTreeNode(
                            key, value, parent=ParentNode(cur_node, Direction.RIGHT)
                        )
                        self._increase_heights(path)
                        break

    def remove(self, key: Union[Iterable, Range]) -> None:
        """Removes the given key from the RangeDict.

        Args:
            key (Union[Iterable, Range]): key to delete

        Raises:
            KeyNotFoundError: if key is not found in the RangeDict
        """
        try:
            if not isinstance(key, Range):
                start, end = key
                key = Range[start, end] if isinstance(key, list) else Range(start, end)
        except ValueError:
            raise InvalidMappingError from None

        cur_node = self.root
        path = []
        while True:
            if cur_node.key == key:
                if cur_node.left is None and cur_node.right is None:
                    if cur_node.parent is None:
                        self.root = None
                        return

                    if cur_node.parent.direction == Direction.LEFT:
                        cur_node.parent.node.left = None
                    elif cur_node.parent.direction == Direction.RIGHT:
                        cur_node.parent.node.right = None
                    else:
                        raise UnknownDirectionError(cur_node.parent.direction)
                    self._decrease_heights(path)
                elif cur_node.left is None:
                    if cur_node.parent is None:
                        self.root = cur_node.right
                        self.root.parent = None
                        return

                    cur_node.right.parent = cur_node.parent
                    if cur_node.parent.direction == Direction.LEFT:
                        cur_node.parent.node.left = cur_node.right
                    elif cur_node.parent.direction == Direction.RIGHT:
                        cur_node.parent.node.right = cur_node.right
                    else:
                        raise UnknownDirectionError(cur_node.parent.direction)
                    self._decrease_heights(path)
                elif cur_node.right is None:
                    if cur_node.parent is None:
                        self.root = cur_node.left
                        self.root.parent = None
                        return

                    cur_node.left.parent = cur_node.parent
                    if cur_node.parent.direction == Direction.LEFT:
                        cur_node.parent.node.left = cur_node.left
                    elif cur_node.parent.direction == Direction.RIGHT:
                        cur_node.parent.node.right = cur_node.left
                    else:
                        raise UnknownDirectionError(cur_node.parent.direction)
                    self._decrease_heights(path)
                else:
                    predecessor = self._find_predecessor(cur_node)

                    if predecessor == cur_node.left:
                        predecessor.left = None
                    else:
                        predecessor.left = cur_node.left

                    predecessor.right = cur_node.right
                    predecessor.parent.node.left = None
                    predecessor.parent.node.height_left = 0
                    predecessor.parent = cur_node.parent

                    if cur_node.parent is None:
                        self.root = predecessor
                    elif cur_node.parent.direction == Direction.LEFT:
                        cur_node.parent.node.left = predecessor
                    elif predecessor.parent.direction == Direction.RIGHT:
                        cur_node.parent.node.right = predecessor
                    else:
                        raise UnknownDirectionError(predecessor.parent.direction)

                    predecessor.height_left = (
                        1
                        if predecessor.left is None
                        else 1
                        + max(
                            predecessor.left.height_left, predecessor.left.height_right
                        )
                    )
                    predecessor.height_right = cur_node.height_right

                    self._check_without_updating_heights(path)
                return
            else:
                op = (
                    operator.le
                    if cur_node.key.closed_left or key.closed_right
                    else operator.lt
                )

                if op(key.end, cur_node.key.start):
                    path.append(ParentNode(cur_node, Direction.LEFT))
                    if cur_node.left is None:
                        raise KeyNotFoundError(key)

                    cur_node = cur_node.left
                else:
                    path.append(ParentNode(cur_node, Direction.RIGHT))
                    if cur_node.right is None:
                        raise KeyNotFoundError(key)

                    cur_node = cur_node.right

    def clear(self) -> None:
        """Clears all key-value pairs from the RangeDict."""

        for key in self.keys_sorted():
            del self[key]

    def items(self) -> Generator[Tuple[Range, Any], None, None]:
        """Returns a generator yielding tuples of key-value pairs from the RangeDict. Order is not guaranteed.

        Yields:
            tuple(Range, Any): key-value pair
        """
        q = [self.root]

        while len(q) > 0:
            cur = q.pop()

            if cur is None:
                return

            if cur.left is not None:
                q.append(cur.left)
            if cur.right is not None:
                q.append(cur.right)

            yield (cur.key, cur.value)

    def items_sorted(self) -> List[Tuple[Range, Any]]:
        """Returns a list of tuple of key-value pairs from the RangeDict, sorted by keys.

        Returns:
            List[Tuple[Range, Any]]: sorted key-value pairs
        """
        return sorted(self.items(), key=lambda k: k[0].start)

    def keys(self) -> Generator[Range, None, None]:
        """Returns a generator yielding keys of the RangeDict. Order is not guaranteed.

        Yields:
            Range: key
        """

        for k, _ in self.items():
            yield k

    def keys_sorted(self) -> List[Range]:
        """Returns a list of keys of the RangeDict, sorted.

        Returns:
            List[Range]: sorted keys
        """

        return sorted(self.keys(), key=lambda k: k.start)

    def values(self) -> Generator[Any, None, None]:
        """Returns a generator yielding values from the RangeDict. Order is not guaranteed.

        Yields:
            Any: value
        """

        for _, v in self.items():
            yield v

    def values_sorted(self) -> List[Any]:
        """Returns a list of values of the RangeDict, sorted according to their keys.

        Returns:
            List[Any]: values, sorted by their keys
        """

        return [v for _, v in self.items_sorted()]

    def get(self, key: Union[int, float], default: Any = None) -> Any:
        """Returns the value for the given key if it's found in the RangeDict, else it returns default.

        Args:
            key (Union[int, float]): key to search for
            default (Any, optional): Default value to return if key is not found. Defaults to None.

        Returns:
            Any: value for the given key or default
        """
        try:
            return self[key]
        except KeyNotFoundError:
            return default

    def update(
        self, other: Union["RangeDict", Dict[Union[Iterable, Range], Any]]
    ) -> None:
        try:
            for k, v in other.items():
                self.insert(k, v)
        except (AttributeError, InvalidMappingError):
            raise InvalidMappingError from None
