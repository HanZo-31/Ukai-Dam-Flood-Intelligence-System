"""Shared validation for local repository filters, independent of HTTP routes."""
import math
from datetime import datetime
from pydantic import TypeAdapter
from services.api.app.published_contract import Timestamp


def time_window(start, end):
    parser = TypeAdapter(Timestamp)
    start = parser.validate_python(start) if start is not None else None
    end = parser.validate_python(end) if end is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("start must not follow end")
    return start, end


def bbox_values(bbox):
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in bbox):
        raise ValueError("bbox requires four finite numbers")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox requires ordered WGS84 bounds; no dateline wrapping")
    return tuple(bbox)
