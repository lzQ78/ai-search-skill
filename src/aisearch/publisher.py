from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def to_json(model: BaseModel | dict[str, Any]) -> str:
    if isinstance(model, BaseModel):
        data = model.model_dump(mode="json")
    else:
        data = model
    return json.dumps(data, ensure_ascii=False, indent=2)

