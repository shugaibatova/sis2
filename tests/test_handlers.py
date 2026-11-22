"""Unit tests with a fake DynamoDB table (no AWS account needed).

Run from the project root:  python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Provide a stub "boto3" if the real one is not installed.
if "boto3" not in sys.modules:
    try:
        import boto3  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["boto3"] = types.SimpleNamespace(resource=lambda *a, **k: None)

os.environ.setdefault("TABLE_NAME", "test-table")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src" / name / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item):
        self.items[Item["id"]] = Item

    def get_item(self, Key):
        item = self.items.get(Key["id"])
        return {"Item": item} if item else {}


class CreateItemTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("create_item")
        self.table = FakeTable()
        self.mod._table = self.table

    def test_creates_item_from_api_gateway_event(self):
        event = {"body": json.dumps({"id": "1", "name": "book"})}
        resp = self.mod.handler(event, None)
        self.assertEqual(resp["statusCode"], 201)
        self.assertEqual(self.table.items["1"]["name"], "book")

    def test_creates_item_from_direct_invoke(self):
        resp = self.mod.handler({"id": "2", "name": "pen"}, None)
        self.assertEqual(resp["statusCode"], 201)

    def test_missing_fields_returns_400(self):
        resp = self.mod.handler({"body": json.dumps({"id": "3"})}, None)
        self.assertEqual(resp["statusCode"], 400)

    def test_invalid_json_returns_400(self):
        resp = self.mod.handler({"body": "not json"}, None)
        self.assertEqual(resp["statusCode"], 400)


class GetItemTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("get_item")
        self.table = FakeTable()
        self.table.put_item({"id": "1", "name": "book"})
        self.mod._table = self.table

    def test_returns_existing_item(self):
        resp = self.mod.handler({"pathParameters": {"id": "1"}}, None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(json.loads(resp["body"])["name"], "book")

    def test_unknown_id_returns_404(self):
        resp = self.mod.handler({"pathParameters": {"id": "nope"}}, None)
        self.assertEqual(resp["statusCode"], 404)

    def test_missing_id_returns_400(self):
        resp = self.mod.handler({}, None)
        self.assertEqual(resp["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
