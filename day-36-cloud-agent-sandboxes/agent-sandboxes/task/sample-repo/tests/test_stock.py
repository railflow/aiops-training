import unittest

from inventory.stock import add_item, remove_item


class StockTests(unittest.TestCase):
    def test_add_item_accumulates(self):
        self.assertEqual(add_item({"a": 1}, "a", 2), {"a": 3})

    def test_add_item_rejects_zero(self):
        with self.assertRaises(ValueError):
            add_item({}, "a", 0)

    def test_remove_item_deletes_empty_sku(self):
        self.assertEqual(remove_item({"a": 2}, "a", 2), {})


if __name__ == "__main__":
    unittest.main()
