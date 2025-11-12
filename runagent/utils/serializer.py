import os
import json
import logging
import math
from typing import Any, Dict, Optional, Union
from dataclasses import asdict
from datetime import datetime, date, time
from runagent.utils.schema import SafeMessage

class CoreSerializer:
    """Core serialization logic that can be used independently"""

    def __init__(self, max_size_mb: float = 10.0):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.logger = logging.getLogger(__name__)

    def serialize_object(self, obj: Any) -> str:
        """
        Core serialization logic - returns JSON string
        
        Args:
            obj: Any object to serialize
            
        Returns:
            JSON string representation
        """
        try:
            # Try direct JSON serialization first
            json_str = json.dumps(obj, ensure_ascii=False, default=self._json_serializer_fallback)
            
            if not self.check_size_limit(json_str):
                self.logger.warning(f"Serialized object exceeds size limit: {len(json_str)} bytes")
            
            return json_str
            
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Core serialization failed: {e}")
            # Return a safe fallback JSON string
            fallback = {
                "content": f"<Serialization Error: {str(e)}>",
                "type": str(type(obj)),
                "error": str(e)
            }
            return json.dumps(fallback, ensure_ascii=False)
    
    def deserialize_object(self, json_str: str, reconstruct: bool = False) -> Union[Dict[str, Any], Any]:
        """
        Parse JSON string to data dict or reconstruct original object
        
        Args:
            json_str: JSON string to deserialize
            reconstruct: If True, attempt to reconstruct original object type
                        If False, return parsed dictionary/JSON version
        """
        if not isinstance(json_str, str):
            raise ValueError(f"Expected string input, got {type(json_str)}")
        
        try:
            deserialized_data = json.loads(json_str)
            
            if not reconstruct:
                return deserialized_data
            
            # Simple reconstruction - just return the parsed data for now
            return deserialized_data
            
        except json.JSONDecodeError as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"JSON deserialization failed: {e}")
            return json_str
        #     raise ValueError(f"Invalid JSON string: {e}")
        # except Exception as e:
        #     if os.getenv('DISABLE_TRY_CATCH'):
        #         raise
        #     self.logger.error(f"Deserialization failed: {e}")
        #     raise

    def serialize_message(self, message: SafeMessage) -> str:
        """
        Serialize SafeMessage to JSON string
        
        Args:
            message: SafeMessage instance to serialize
            
        Returns:
            JSON string representation
        """
        if not isinstance(message, SafeMessage):
            raise ValueError(f"Expected SafeMessage, got {type(message)}")
        
        try:
            # Use SafeMessage's to_dict method
            message_dict = message.to_dict()
            
            json_str = json.dumps(message_dict, ensure_ascii=False, default=self._json_serializer_fallback)
            
            if not self.check_size_limit(json_str):
                self.logger.warning(f"Serialized message exceeds size limit: {len(json_str)} bytes")
            
            return json_str
            
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Message serialization failed: {e}")
            # Return a safe fallback JSON string
            fallback = {
                "id": getattr(message, 'id', 'unknown'),
                "type": str(getattr(message, 'type', 'unknown')),
                "timestamp": getattr(message, 'timestamp', ''),
                "data": {"error": f"Serialization failed: {str(e)}"},
                "metadata": None,
                "error": f"Serialization Error: {str(e)}"
            }
            return json.dumps(fallback, ensure_ascii=False)

    def deserialize_message(self, json_str: str) -> SafeMessage:
        """
        Deserialize JSON string to SafeMessage
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            SafeMessage instance
        """
        if not isinstance(json_str, str):
            raise ValueError(f"Expected string input, got {type(json_str)}")
        
        try:
            deserialized_data = json.loads(json_str)
            
            # Ensure required fields exist with defaults
            if not isinstance(deserialized_data, dict):
                raise ValueError("JSON must deserialize to a dictionary")
            
            return SafeMessage(**deserialized_data)
            
        except json.JSONDecodeError as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"JSON deserialization failed: {e}")
            raise ValueError(f"Invalid JSON string: {e}")
        except TypeError as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"SafeMessage construction failed: {e}")
            raise ValueError(f"Invalid SafeMessage data: {e}")
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Message deserialization failed: {e}")
            raise

    def serialize_object_to_structured(self, obj: Any) -> str:
        """
        Serialize object to structured format with explicit type information.
        
        Returns a JSON string containing:
        - type: OpenAPI-compatible type (string, integer, number, boolean, array, object, null)
        - payload: JSON-stringified representation of the object
        
        Args:
            obj: Any object to serialize
            
        Returns:
            JSON string with 'type' and 'payload' keys
        """
        try:
            # Determine type before serialization
            data_type = self._determine_type(obj)
            
            # Handle special conversions before JSON serialization
            obj_to_serialize = self._prepare_for_serialization(obj)
            
            # Serialize to JSON string
            payload = json.dumps(
                obj_to_serialize, 
                ensure_ascii=False, 
                allow_nan=False,  # Explicitly reject NaN/Inf
                default=self._json_serializer_fallback
            )
            
            if not self.check_size_limit(payload):
                self.logger.warning(f"Serialized payload exceeds size limit: {len(payload)} bytes")
            
            # Return the structured format as a JSON string
            structured = {
                "type": data_type,
                "payload": payload
            }
            return json.dumps(structured, ensure_ascii=False)
            
        except (ValueError, TypeError) as e:
            # Handle NaN/Inf or other JSON errors
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Structured serialization failed: {e}")
            error_payload = json.dumps({
                "error": f"Serialization Error: {str(e)}",
                "original_type": str(type(obj))
            })
            error_structured = {
                "type": "object",
                "payload": error_payload
            }
            return json.dumps(error_structured, ensure_ascii=False)
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Structured serialization failed: {e}")
            error_payload = json.dumps({
                "error": f"Serialization Error: {str(e)}",
                "original_type": str(type(obj))
            })
            error_structured = {
                "type": "object",
                "payload": error_payload
            }
            return json.dumps(error_structured, ensure_ascii=False)
    
    def deserialize_object_from_structured(self, structured_json: str) -> Any:
        """
        Deserialize object from structured format JSON string.
        
        Args:
            structured_json: JSON string with 'type' and 'payload' keys
            
        Returns:
            Deserialized Python object
        """
        try:
            # Parse the JSON string
            if not isinstance(structured_json, str):
                raise ValueError(f"Expected JSON string input, got {type(structured_json)}")
            
            structured_data = json.loads(structured_json)
            
            if not isinstance(structured_data, dict):
                raise ValueError(f"JSON must deserialize to a dict, got {type(structured_data)}")
            
            data_type = structured_data.get("type")
            payload = structured_data.get("payload")
            
            if data_type is None or payload is None:
                raise ValueError("Structured data must have 'type' and 'payload' keys")
            
            # Parse payload based on type
            if data_type == "null":
                return None
            elif data_type == "string":
                # Payload is JSON string, parse to get the actual string
                return json.loads(payload)
            elif data_type == "integer":
                value = json.loads(payload)
                return int(value)
            elif data_type == "number":
                value = json.loads(payload)
                return float(value)
            elif data_type == "boolean":
                return json.loads(payload)
            elif data_type in ("array", "object"):
                # Parse JSON to get structured data
                return json.loads(payload)
            else:
                # Unknown type, try to parse as JSON
                self.logger.warning(f"Unknown type '{data_type}', attempting JSON parse")
                return json.loads(payload)
                
        except json.JSONDecodeError as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Failed to deserialize structured data: {e}")
            raise ValueError(f"Invalid structured data: {e}")
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Deserialization failed: {e}")
            raise
    
    def _determine_type(self, obj: Any) -> str:
        """
        Determine OpenAPI-compatible type for an object.
        
        Returns: string, integer, number, boolean, array, object, null
        """
        # Check None first
        if obj is None:
            return "null"
        
        # Check bool before int (bool is subclass of int in Python)
        if isinstance(obj, bool):
            return "boolean"
        
        # Check numeric types
        if isinstance(obj, int):
            return "integer"
        
        if isinstance(obj, float):
            # Check for NaN or Infinity
            if math.isnan(obj) or math.isinf(obj):
                self.logger.warning(f"Float value is NaN or Inf: {obj}, treating as number")
            return "number"
        
        # Check string
        if isinstance(obj, str):
            return "string"
        
        # Check array-like (list, tuple, set)
        if isinstance(obj, (list, tuple, set)):
            return "array"
        
        # Check dict
        if isinstance(obj, dict):
            return "object"
        
        # For complex objects, check if they can be converted to dict
        if hasattr(obj, 'to_dict') or hasattr(obj, 'model_dump') or hasattr(obj, 'dict') or hasattr(obj, '__dict__'):
            return "object"
        
        # Fallback: will be stringified
        self.logger.warning(f"Unknown type {type(obj)}, will stringify as 'string'")
        return "string"
    
    def _prepare_for_serialization(self, obj: Any) -> Any:
        """
        Prepare object for JSON serialization by converting special types.
        """
        # Handle None
        if obj is None:
            return None
        
        # Handle primitives (pass through)
        if isinstance(obj, (bool, int, str)):
            return obj
        
        # Handle floats with NaN/Inf check
        if isinstance(obj, float):
            if math.isnan(obj):
                # Convert NaN to null
                self.logger.warning("Converting NaN to null")
                return None
            elif math.isinf(obj):
                # Convert Infinity to string representation
                self.logger.warning(f"Converting Infinity to string: {obj}")
                return str(obj)
            return obj
        
        # Handle datetime objects - convert to ISO format string
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.isoformat()
        
        # Handle sets - convert to list
        if isinstance(obj, set):
            return list(obj)
        
        # Handle bytes - convert to base64 or hex string
        if isinstance(obj, (bytes, bytearray)):
            self.logger.warning("Converting bytes to hex string")
            return obj.hex()
        
        # For pandas DataFrame, try to_dict
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            try:
                return obj.to_dict()
            except Exception as e:
                self.logger.warning(f"Failed to call to_dict on {type(obj)}: {e}")
        
        # For Pydantic models
        if hasattr(obj, 'model_dump'):
            try:
                return obj.model_dump()
            except Exception as e:
                self.logger.warning(f"Failed to call model_dump on {type(obj)}: {e}")
        
        if hasattr(obj, 'dict'):
            try:
                return obj.dict()
            except Exception as e:
                self.logger.warning(f"Failed to call dict on {type(obj)}: {e}")
        
        # Collections - recursively prepare elements
        if isinstance(obj, (list, tuple)):
            return [self._prepare_for_serialization(item) for item in obj]
        
        if isinstance(obj, dict):
            return {k: self._prepare_for_serialization(v) for k, v in obj.items()}
        
        # Last resort: use the fallback which will be called by json.dumps
        return obj

    def _json_serializer_fallback(self, obj: Any) -> Any:
        """
        Simplified fallback serializer for JSON.dumps when encountering non-serializable objects
        """
        try:
            # Try dataclass first
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            # Try pydantic models
            elif hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, 'dict'):
                return obj.dict()
            # Try basic dict extraction
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)
        except Exception:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return f"<Unserializable {type(obj).__name__}>"

    # Keep these utility methods unchanged
    def extract_metadata(self, obj: Any) -> Dict[str, Any]:
        """Extract metadata about the object"""
        return self._extract_metadata(obj)
    
    def check_size_limit(self, json_str: str) -> bool:
        """Check if serialized data exceeds size limit"""
        if not isinstance(json_str, str):
            return False
        return len(json_str.encode('utf-8')) <= self.max_size_bytes
    
    def serialize_to_json(self, data: Dict[str, Any]) -> str:
        """Convert data dict to JSON string (legacy method)"""
        return json.dumps(data, ensure_ascii=False, default=self._json_serializer_fallback)
    
    def _deserialize_from_json(self, json_str: str) -> Dict[str, Any]:
        """Parse JSON string to data dict (legacy method)"""
        return json.loads(json_str)

    def _extract_metadata(self, obj: Any) -> Dict[str, Any]:
        """Extract metadata about the object"""
        try:
            obj_str = str(obj)
            obj_size = len(obj_str)
        except Exception:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            obj_str = f"<Cannot convert {type(obj)} to string>"
            obj_size = 0
        
        return {
            "object_type": str(type(obj)),
            "object_size": obj_size,
            "has_dict": hasattr(obj, '__dict__'),
            "is_dataclass": hasattr(obj, '__dataclass_fields__'),
            "is_pydantic": hasattr(obj, 'model_dump') or hasattr(obj, 'dict'),
            "module": getattr(type(obj), '__module__', 'unknown'),
            "is_none": obj is None,
            "is_iterable": hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes))
        }
