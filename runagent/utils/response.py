import json
from jsonpath_ng import jsonpath, parse
from typing import Any, Union, List, Dict

def to_dict(obj: Any) -> Any:
    """
    Convert various object types to dictionary if possible.
    
    Args:
        obj: Object to convert (Pydantic model, dataclass, dict, etc.)
    
    Returns:
        dict: Dictionary representation of the object, or original object if conversion fails
    """
    # Already a dict
    if isinstance(obj, dict):
        return obj
    
    # Pydantic model (has model_dump method)
    if hasattr(obj, 'model_dump'):
        try:
            return obj.model_dump()
        except:
            return obj
    
    # Pydantic v1 model (has dict method)
    if hasattr(obj, 'dict'):
        try:
            return obj.dict()
        except:
            return obj
    
    # Dataclass
    if hasattr(obj, '__dataclass_fields__'):
        try:
            from dataclasses import asdict
            return asdict(obj)
        except:
            return obj
    
    # NamedTuple
    if hasattr(obj, '_asdict'):
        try:
            return obj._asdict()
        except:
            return obj
    
    # Has __dict__ attribute (regular classes)
    if hasattr(obj, '__dict__'):
        try:
            return obj.__dict__
        except:
            return obj
    
    # Try to serialize and deserialize as JSON (last resort)
    try:
        return json.loads(json.dumps(obj, default=str))
    except:
        # If all else fails, return the original object
        return obj


def extract_jsonpath(data: Any, jsonpath_expressions: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract values from any object using JSONPath expressions.
    
    Args:
        data: Any object that can be converted to dict (Pydantic model, dataclass, dict, etc.)
        jsonpath_expressions: A single JSONPath string or list of JSONPath strings
    
    Returns:
        If single expression: The first matched value (or None if no match)
        If multiple expressions: List of first matched values for each expression
    """
    # Convert to dictionary first
    dict_data = to_dict(data)

    extracted_resp = {}
    for key, expr in jsonpath_expressions.items():
        jsonpath_expression = parse(expr)
        matches = jsonpath_expression.find(dict_data)
        # Return just the first value, or None if no matches
        extracted_resp[key] = matches[0].value if matches else None

    return extracted_resp