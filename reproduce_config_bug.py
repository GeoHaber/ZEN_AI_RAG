
import json
from dataclasses import dataclass, field, is_dataclass
from typing import Any

@dataclass
class SubConfig:
    val: str = "default"

@dataclass
class MainConfig:
    sub: SubConfig = field(default_factory=SubConfig)
    simple: int = 1

def load_simulated():
    merged_data = {"sub": {"val": "loaded"}, "simple": 42}
    config_inst = MainConfig()
    
    for k, v in merged_data.items():
        if k in MainConfig.__dataclass_fields__:
            field_def = MainConfig.__dataclass_fields__[k]
            field_type = field_def.type
            print(f"Key: {k}, Type: {field_type}, is_dataclass: {is_dataclass(field_type)}")
            
            if is_dataclass(field_type) and isinstance(v, dict):
                valid_sub_fields = {
                    sk: sv for sk, sv in v.items() 
                    if sk in field_type.__dataclass_fields__
                }
                setattr(config_inst, k, field_type(**valid_sub_fields))
            else:
                setattr(config_inst, k, v)
    return config_inst

c = load_simulated()
print(f"Result config.sub: {c.sub} (Type: {type(c.sub)})")
