import os
import json
import logging
from typing import Any, Dict, Optional, Union
from dataclasses import asdict
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
            raise ValueError(f"Invalid JSON string: {e}")
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            self.logger.error(f"Deserialization failed: {e}")
            raise

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
