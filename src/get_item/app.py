"""get_item: read one item from DynamoDB by id.

Input: API Gateway proxy event with pathParameters.id, or a direct {"id": "..."} invoke.
Output: API Gateway proxy response.
"""
import json
import os

import boto3

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _extract_id(event):
    path_params = event.get("pathParameters") or {}
    return path_params.get("id") or event.get("id")


def handler(event, context):
    item_id = _extract_id(event)
    if not item_id:
        return _response(400, {"error": "item id is required"})

    result = _get_table().get_item(Key={"id": str(item_id)})
    item = result.get("Item")
    if item is None:
        return _response(404, {"error": "item not found"})
    return _response(200, item)
