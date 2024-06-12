import inspect
import json
import numpy as np
import os
from datetime import datetime
from IPython.display import clear_output

import sqlite3
import psycopg2
import requests
from cachetools import LRUCache

_LOCAL_PARAMS_CACHE = LRUCache(maxsize=64)


def verbose_raise_for_status(response):
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.text:
            print(response.text)
        response.raise_for_status()


def local_param(param_name: str):
    """
    This function returns a parameter from an adjacent './params/' directory of a calling function sight
    Parameters should be valid json files
    Parameter is cached for efficiency reasons, so files are read only once

    :param param_name: name of a parameter file to be loaded. Postfix '.json' can be ommited,
        so "my_param.json" and "my_param" are equivalent

    :raises ValueError: if the referenced file doesn't exist, or is outside of './params' directory

    :Example:
        given:
            /my_task
                /params
                    my_param.json
                my_task.py

        calling `local_param('my_param')` will return the contents of './params/my_param.json'
    """

    try:
        current_frame = inspect.currentframe()
        if current_frame is None:
            raise ValueError("Caller doesn't have frame info")
        calling_function_filepath = inspect.getframeinfo(current_frame.f_back).filename  # type: ignore[arg-type]
    except BaseException as e:
        raise ValueError("Caller as not defined in a file") from e

    base_dir = os.path.dirname(calling_function_filepath)

    if not param_name.endswith(".json"):
        param_name = param_name + ".json"

    param_dir = os.path.join(base_dir, "params")
    abs_param_path = os.path.abspath(os.path.join(param_dir, param_name))
    if abs_param_path not in _LOCAL_PARAMS_CACHE:
        # ensure that the destination doesn't look outside of our sql folder
        abs_param_dir = os.path.abspath(param_dir)
        common_path = os.path.commonpath([abs_param_path, abs_param_dir])
        if not common_path.startswith(abs_param_dir):
            raise ValueError(
                "Only parameter files in a sibling './params/' directory can be referenced"
            )

        if os.path.islink(abs_param_path):
            raise ValueError("Links can not be referenced as local parameter fle")

        try:
            with open(abs_param_path, "r", encoding="utf-8") as f:
                _LOCAL_PARAMS_CACHE[abs_param_path] = json.load(f)
        except Exception as e:
            raise ValueError(
                f"Couldn't read referenced file: '{abs_param_path}': {e}"
            ) from e

    return _LOCAL_PARAMS_CACHE[abs_param_path]


def create_connection(connection_string, connection_type):
    """create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    assert connection_type in ("sqlite3", "psycopg2")
    if connection_type == "sqlite3":
        conn = None
        try:
            conn = sqlite3.connect(connection_string)
        except sqlite3.Error as e:
            print(e)

        return conn
    elif connection_type == "psycopg2":
        try:
            conn = psycopg2.connect(connection_string)
            return conn
        except psycopg2.Error as e:
            print(f"Error: {e}")
            return None
