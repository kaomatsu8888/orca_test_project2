#!/usr/bin/env python3
"""A small TODO management command-line application."""

import argparse
import json
import os
import tempfile
from datetime import datetime


def _storage_path():
    return os.environ.get("TODO_FILE", "./todos.json")


def _empty_data():
    return {"next_id": 1, "items": []}


def _validate_data(data):
    """Validate the on-disk format and raise ValueError if it is invalid."""
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    if not isinstance(data.get("next_id"), int) or isinstance(data["next_id"], bool):
        raise ValueError("next_id must be an integer")
    if data["next_id"] < 1:
        raise ValueError("next_id must be positive")
    if not isinstance(data.get("items"), list):
        raise ValueError("items must be a list")

    ids = set()
    for item in data["items"]:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")
        if not isinstance(item.get("id"), int) or isinstance(item["id"], bool):
            raise ValueError("item id must be an integer")
        if item["id"] < 1 or item["id"] in ids:
            raise ValueError("item ids must be unique positive integers")
        if not isinstance(item.get("title"), str):
            raise ValueError("item title must be a string")
        if not isinstance(item.get("done"), bool):
            raise ValueError("item done must be a boolean")
        if not isinstance(item.get("created_at"), str):
            raise ValueError("item created_at must be a string")
        ids.add(item["id"])

    if any(item_id >= data["next_id"] for item_id in ids):
        raise ValueError("next_id must be greater than every item id")


def load_todos(path=None):
    """Load todos from *path*, returning empty data when the file is absent."""
    path = _storage_path() if path is None else path
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return _empty_data()
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise ValueError("could not read todo file: {}".format(exc)) from exc

    try:
        _validate_data(data)
    except ValueError as exc:
        raise ValueError("invalid todo file: {}".format(exc)) from exc
    return data


def save_todos(data, path=None):
    """Atomically save todos as UTF-8 JSON."""
    path = _storage_path() if path is None else path
    directory = os.path.dirname(os.path.abspath(path)) or "."
    filename = os.path.basename(path)
    temporary_path = None
    try:
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=".{}-".format(filename), dir=directory, text=True
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def _error(message):
    print("Error: {}".format(message), file=os.sys.stderr)
    return 1


def _add(args):
    if args.title == "":
        return _error("title must not be empty")
    try:
        data = load_todos()
    except ValueError as exc:
        return _error(str(exc))

    item_id = data["next_id"]
    item = {
        "id": item_id,
        "title": args.title,
        "done": False,
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
    }
    data["items"].append(item)
    data["next_id"] = item_id + 1
    try:
        save_todos(data)
    except OSError as exc:
        return _error("could not save todo file: {}".format(exc))
    print("Added #{}: {}".format(item_id, args.title))
    return 0


def _list(args):
    try:
        data = load_todos()
    except ValueError as exc:
        return _error(str(exc))

    items = sorted(data["items"], key=lambda item: item["id"])
    if not args.all:
        items = [item for item in items if not item["done"]]
    if not items:
        print("No todos.")
        return 0
    for item in items:
        mark = "x" if item["done"] else " "
        print("#{} [{}] {}".format(item["id"], mark, item["title"]))
    return 0


def _done(args):
    try:
        data = load_todos()
    except ValueError as exc:
        return _error(str(exc))

    for item in data["items"]:
        if item["id"] == args.id:
            if item["done"]:
                print("Already done #{}".format(args.id))
                return 0
            item["done"] = True
            try:
                save_todos(data)
            except OSError as exc:
                return _error("could not save todo file: {}".format(exc))
            print("Done #{}: {}".format(args.id, item["title"]))
            return 0
    return _error("todo #{} not found".format(args.id))


def _rm(args):
    try:
        data = load_todos()
    except ValueError as exc:
        return _error(str(exc))

    for index, item in enumerate(data["items"]):
        if item["id"] == args.id:
            removed = data["items"].pop(index)
            try:
                save_todos(data)
            except OSError as exc:
                return _error("could not save todo file: {}".format(exc))
            print("Removed #{}: {}".format(args.id, removed["title"]))
            return 0
    return _error("todo #{} not found".format(args.id))


def build_parser():
    parser = argparse.ArgumentParser(prog="todo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("title")
    add_parser.set_defaults(function=_add)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--all", action="store_true")
    list_parser.set_defaults(function=_list)

    done_parser = subparsers.add_parser("done")
    done_parser.add_argument("id", type=int)
    done_parser.set_defaults(function=_done)

    rm_parser = subparsers.add_parser("rm")
    rm_parser.add_argument("id", type=int)
    rm_parser.set_defaults(function=_rm)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
