"""create_item: store one item in DynamoDB.

Input  (API Gateway proxy event or direct invoke): JSON body {"id": "...", "name": "..."}
Output (API Gateway proxy response): statusCode + JSON body.
"""
import json
import os
import time

import boto3

_table = None


def _get_table():
    # Created lazily so unit tests can import this module without AWS access.
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_body(event):
    body = event.get("body", event)
    if isinstance(body, str):
        body = json.loads(body)
    return body


def handler(event, context):
    try:
        data = _parse_body(event)
    except (ValueError, TypeError):
        return _response(400, {"error": "body must be valid JSON"})

    item_id = data.get("id") if isinstance(data, dict) else None
    name = data.get("name") if isinstance(data, dict) else None
    if not item_id or not name:
        return _response(400, {"error": "fields 'id' and 'name' are required"})

    item = {"id": str(item_id), "name": str(name), "createdAt": int(time.time())}
    _get_table().put_item(Item=item)
    return _response(201, item)
