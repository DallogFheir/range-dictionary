from unittest import TestCase
from range_dictionary import Range, RangeDict
from range_dictionary import (
    InvalidMappingError,
    KeyNotFoundError,
    NotNumberError,
    OverlapError,
    RangeValueError,
)


class TestRange(TestCase):
    def test_init(self):
        with self.assertRaises(RangeValueError):
            Range("a", 2)
        with self.assertRaises(RangeValueError):
            Range(3, "b")
        with self.assertRaises(RangeValueError):
            Range(float("-inf"), 5, closed_left=True)
        with self.assertRaises(RangeValueError):
            Range(5, 3)
        with self.assertRaises(RangeValueError):
            Range[1]
        with self.assertRaises(RangeValueError):
            Range[1, 2, 3]

        r = Range[1, 2]
        self.assertIsInstance(r, Range)
        self.assertTrue(r.closed_left)
        self.assertTrue(r.closed_right)

    def test_contains(self):
        r = Range(3, 8)

        with self.assertRaises(NotNumberError):
            "a" in r

        self.assertTrue(5.5 in r)
        self.assertFalse(10 in r)

    def test_lt(self):
        r1 = Range(3, 8)
        self.assertTrue(r1 < 9)
        self.assertTrue(r1 < 8)

        with self.assertRaises(NotNumberError):
            r1 < [2, 3]

        r2 = Range(3, 8, closed_right=True)
        self.assertFalse(r2 < 8)

    def test_gt(self):
        r1 = Range(3, 8)
        self.assertTrue(r1 > 2)
        self.assertTrue(r1 > 3)

        with self.assertRaises(NotNumberError):
            r1 > {"a": 1, "b": 2}

        r2 = Range(3, 8, closed_left=True)
        self.assertFalse(r2 > 3)

    def test_overlaps(self):
        r1 = Range(1, 2)
        r2 = Range(4, 5)
        self.assertFalse(r1.overlaps(r2))
        self.assertFalse(r2.overlaps(r1))

        r3 = Range(1, 7)
        r4 = Range[4, 5]
        self.assertTrue(r3.overlaps(r4))
        self.assertTrue(r4.overlaps(r3))

        r5 = Range[1, 2]
        r6 = Range(2, 5)
        self.assertFalse(r5.overlaps(r6))
        self.assertFalse(r6.overlaps(r5))

        r7 = Range(1, 2)
        r8 = Range[1, 2]
        self.assertTrue(r7.overlaps(r8))
        self.assertTrue(r8.overlaps(r7))

        r9 = Range[1, 2]
        r10 = Range[2, 5]
        self.assertTrue(r9.overlaps(r10))
        self.assertTrue(r10.overlaps(r9))

        r11 = Range(5, 7)
        r12 = Range[7, 10]
        self.assertFalse(r11.overlaps(r12))
        self.assertFalse(r12.overlaps(r11))


class TestRangeDict(TestCase):
    def test_init(self):
        rd1 = RangeDict()
        self.assertIsNone(rd1.root)

        rd2 = RangeDict({(1, 2): "first", (3, 4): "second"})
        self.assertEqual(rd2.root.value, "first")
        self.assertIsNone(rd2.root.left)
        self.assertEqual(rd2.root.right.value, "second")

        rd3 = RangeDict(rd2)
        self.assertEqual(rd3.root.value, "first")
        self.assertIsNone(rd3.root.left)
        self.assertEqual(rd3.root.right.value, "second")

        with self.assertRaises(InvalidMappingError):
            RangeDict({(1, 2, 3): "first"})

    def test_getitem(self):
        rd = RangeDict(
            {Range[1, 2]: "first", Range(2, 5): "second", Range(5, 7): "third"}
        )

        self.assertEqual(rd[3], "second")
        self.assertEqual(rd[6.99], "third")
        with self.assertRaises(KeyNotFoundError):
            rd[7]

    def test_contains(self):
        rd = RangeDict(
            {Range[1, 2]: "first", Range(2, 5): "second", Range(5, 7): "third"}
        )

        self.assertTrue(6 in rd)
        self.assertFalse(5 in rd)

    def test_or(self):
        rd1 = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        items_rd1 = rd1.items_sorted()
        rd2 = RangeDict({Range[301, 400]: 4})

        rd3 = rd1 | rd2

        items_rd3 = rd3.items_sorted()
        self.assertListEqual(
            items_rd1, [(Range[1, 100], 1), (Range[101, 200], 2), (Range[201, 300], 3)]
        )
        self.assertListEqual(
            items_rd3,
            [
                (Range[1, 100], 1),
                (Range[101, 200], 2),
                (Range[201, 300], 3),
                (Range[301, 400], 4),
            ],
        )

    def test_ror(self):
        rd1 = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        items_rd1 = rd1.items_sorted()
        d2 = {Range[301, 400]: 4}

        rd3 = d2 | rd1

        items_rd3 = rd3.items_sorted()
        self.assertListEqual(
            items_rd1, [(Range[1, 100], 1), (Range[101, 200], 2), (Range[201, 300], 3)]
        )
        self.assertListEqual(
            items_rd3,
            [
                (Range[1, 100], 1),
                (Range[101, 200], 2),
                (Range[201, 300], 3),
                (Range[301, 400], 4),
            ],
        )

    def test_eq(self):
        rd1 = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        rd2 = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})

        self.assertEqual(rd1, rd2)

    def test_insert(self):
        rd = RangeDict(
            {Range[1, 2]: "first", Range(2, 5): "second", Range(5, 7): "third"}
        )

        with self.assertRaises(InvalidMappingError):
            rd.insert((1, 2, 3), "fourth")

        with self.assertRaises(OverlapError):
            rd.insert(Range[0, 1], "fifth")

        rd.insert(Range[7, 10], "sixth")
        self.assertEqual(rd.root.right.right.value, "sixth")

    def test_remove(self):
        rd = RangeDict(
            {Range[1, 2]: "first", Range(2, 5): "second", Range(5, 7): "third"}
        )

        with self.assertRaises(KeyNotFoundError):
            rd.remove(Range(5, 7, closed_right=True))

        rd.remove(Range(2, 5))
        self.assertEqual(rd.root.value, "first")
        self.assertEqual(rd.root.right.value, "third")

    def test_clear(self):
        rd = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        rd.clear()

        self.assertIsNone(rd.root)

    def test_items(self):
        rd = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        items = rd.items_sorted()

        self.assertListEqual(
            items, [(Range[1, 100], 1), (Range[101, 200], 2), (Range[201, 300], 3)]
        )

    def test_keys(self):
        rd = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        keys = rd.keys_sorted()

        self.assertListEqual(keys, [Range[1, 100], Range[101, 200], Range[201, 300]])

    def test_values(self):
        rd = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        values = rd.values_sorted()

        self.assertListEqual(values, [1, 2, 3])

    def test_get(self):
        rd = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})

        self.assertEqual(rd.get(2), 1)
        self.assertEqual(rd.get(150), 2)
        self.assertEqual(rd.get(300), 3)
        self.assertEqual(rd.get(2000, 5), 5)
        self.assertIsNone(rd.get(1000))

    def test_update(self):
        rd1 = RangeDict({Range[1, 100]: 1, Range[101, 200]: 2, Range[201, 300]: 3})
        rd2 = RangeDict({Range[301, 400]: 4})

        rd1.update(rd2)

        items = rd1.items_sorted()
        self.assertListEqual(
            items,
            [
                (Range[1, 100], 1),
                (Range[101, 200], 2),
                (Range[201, 300], 3),
                (Range[301, 400], 4),
            ],
        )
