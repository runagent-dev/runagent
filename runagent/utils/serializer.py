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
            serialized_data = self._try_serialize_strategies(obj)
            json_str = json.dumps(serialized_data, ensure_ascii=False, default=self._json_serializer_fallback)
            
            if not self.check_size_limit(json_str):
                self.logger.warning(f"Serialized object exceeds size limit: {len(json_str)} bytes")
            
            return json_str
        except Exception as e:
            self.logger.error(f"Core serialization failed: {e}")
            # Return a safe fallback JSON string
            fallback = {
                "content": f"<Serialization Error: {str(e)}>",
                "strategy": "error_fallback",
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
                # Return the parsed dictionary/JSON version with proper nested structure
                return self._reconstruct_nested_json(deserialized_data.get("content"))
            
            # Try to reconstruct original object
            return self._reconstruct_object(deserialized_data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON deserialization failed: {e}")
            raise ValueError(f"Invalid JSON string: {e}")
        except Exception as e:
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
            # Use SafeMessage's to_dict method and ensure nested objects are properly serialized
            message_dict = message.to_dict()
            
            # Deep serialize the data field to handle nested objects
            if message_dict.get('data'):
                message_dict['data'] = self._deep_serialize_value(message_dict['data'])
            
            if message_dict.get('metadata'):
                message_dict['metadata'] = self._deep_serialize_value(message_dict['metadata'])
            
            json_str = json.dumps(message_dict, ensure_ascii=False, default=self._json_serializer_fallback)
            
            if not self.check_size_limit(json_str):
                self.logger.warning(f"Serialized message exceeds size limit: {len(json_str)} bytes")
            
            return json_str
            
        except Exception as e:
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
            deserialized_data = json.loads(json_str)  # .get("content")
            
            # Ensure required fields exist with defaults
            if not isinstance(deserialized_data, dict):
                raise ValueError("JSON must deserialize to a dictionary")
            
            # Reconstruct nested JSON structures in data and metadata
            if deserialized_data.get('data'):
                deserialized_data['data'] = self._reconstruct_nested_json(deserialized_data['data'])
            
            if deserialized_data.get('metadata'):
                deserialized_data['metadata'] = self._reconstruct_nested_json(deserialized_data['metadata'])
            return SafeMessage(**deserialized_data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON deserialization failed: {e}")
            raise ValueError(f"Invalid JSON string: {e}")
        except TypeError as e:
            self.logger.error(f"SafeMessage construction failed: {e}")
            raise ValueError(f"Invalid SafeMessage data: {e}")
        except Exception as e:
            self.logger.error(f"Message deserialization failed: {e}")
            raise

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

    def _json_serializer_fallback(self, obj: Any) -> Any:
        """
        Fallback serializer for JSON.dumps when encountering non-serializable objects
        """
        try:
            # Try basic conversions first
            if hasattr(obj, '__dict__'):
                return self._safe_dict_extract(obj.__dict__)
            elif hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, 'dict'):
                return obj.dict()
            elif hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            else:
                return str(obj)
        except Exception:
            return f"<Unserializable {type(obj).__name__}>"

    def _deep_serialize_value(self, value: Any) -> Any:
        """
        Deep serialize any value, handling all types and nested structures
        """
        try:
            # Test if value is directly JSON serializable
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            pass
        
        # Handle different types
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, dict):
            return self._deep_serialize_dict(value)
        elif isinstance(value, (list, tuple)):
            return self._serialize_sequence(value)
        elif isinstance(value, set):
            return self._serialize_sequence(list(value))
        elif hasattr(value, '__dict__'):
            # Serialize object to dict
            try:
                serialized = self._try_serialize_strategies(value)
                return serialized
            except Exception:
                return str(value)
        else:
            # Convert to string as fallback
            try:
                return str(value)
            except Exception:
                return f"<Unserializable {type(value).__name__}>"

    def _deep_serialize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep serialize dictionary, handling nested objects and ensuring JSON compatibility
        """
        if not isinstance(data, dict):
            return self._deep_serialize_value(data)
        
        result = {}
        
        for key, value in data.items():
            # Ensure key is string (JSON requirement)
            str_key = str(key) if not isinstance(key, str) else key
            result[str_key] = self._deep_serialize_value(value)
        
        return result

    def _serialize_sequence(self, seq: Union[list, tuple, set]) -> list:
        """Serialize list, tuple, or set, handling nested objects"""
        if not seq:
            return []
        
        result = []
        
        for item in seq:
            result.append(self._deep_serialize_value(item))
        
        return result

    def _reconstruct_nested_json(self, data: Any) -> Any:
        """
        Reconstruct nested JSON structures, converting string representations back to proper types
        """
        if data is None:
            return None
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self._reconstruct_nested_json(value)
            return result
        elif isinstance(data, list):
            return [self._reconstruct_nested_json(item) for item in data]
        # elif isinstance(data, str):
        #     # Try to parse as JSON if it looks like JSON
        #     stripped = data.strip()
        #     if stripped.startswith(('{', '[')):
        #         try:
        #             parsed = json.loads(data)
        #             return self._reconstruct_nested_json(parsed)
        #         except (json.JSONDecodeError, ValueError):
        #             pass
        #     return data
        else:
            return data

    def _reconstruct_object(self, data: Any) -> Any:
        """
        Attempt to reconstruct original object from serialized data
        """
        if not isinstance(data, dict):
            return self._reconstruct_nested_json(data)
        
        strategy = data.get('strategy')
        content = data.get('content')
        
        if strategy == 'direct':
            return self._reconstruct_nested_json(content)
        
        elif strategy == 'dataclass':
            # Would need class registry to properly reconstruct dataclasses
            return self._reconstruct_nested_json(content)
        
        elif strategy == 'dict_extract':
            # Create a simple object with the extracted attributes
            class_name = data.get('class_name', 'ReconstructedObject')
            
            class ReconstructedObject:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, self._reconstruct_nested_json(value))
                
                def __repr__(self):
                    return f"{class_name}({', '.join(f'{k}={v}' for k, v in self.__dict__.items())})"
            
            ReconstructedObject.__name__ = class_name
            return ReconstructedObject(**content) if isinstance(content, dict) else content
        
        elif strategy == 'pydantic':
            # Would need model registry to properly reconstruct Pydantic models
            return self._reconstruct_nested_json(content)
        
        elif strategy in ('string_repr', 'fallback', 'error_fallback'):
            return content
        
        else:
            return self._reconstruct_nested_json(data)
    
    def _try_serialize_strategies(self, obj: Any) -> Dict[str, Any]:
        """Try multiple serialization strategies in order of preference"""
        
        # Handle None explicitly
        if obj is None:
            return {"content": None, "strategy": "direct"}
        
        # Strategy 1: Direct JSON serializable
        try:
            # Test with actual JSON serialization to catch all edge cases
            json.dumps(obj, default=str)
            return {"content": obj, "strategy": "direct"}
        except (TypeError, ValueError, OverflowError):
            pass
        
        # Strategy 2: Dataclass/attrs
        if hasattr(obj, '__dataclass_fields__'):
            try:
                content = asdict(obj)
                # Ensure the content is JSON serializable
                json.dumps(content, default=str)
                return {"content": content, "strategy": "dataclass"}
            except Exception:
                pass
        
        # Strategy 3: Pydantic models (check before __dict__ as they also have __dict__)
        if hasattr(obj, 'model_dump') or hasattr(obj, 'dict'):
            try:
                if hasattr(obj, 'model_dump'):
                    content = obj.model_dump()
                else:
                    content = obj.dict()
                # Ensure the content is JSON serializable
                json.dumps(content, default=str)
                return {"content": content, "strategy": "pydantic"}
            except Exception:
                pass
        
        # Strategy 4: Dict-like objects
        if hasattr(obj, '__dict__'):
            try:
                content = self._safe_dict_extract(obj.__dict__)
                return {
                    "content": content,
                    "strategy": "dict_extract",
                    "class_name": obj.__class__.__name__,
                    "module": getattr(obj.__class__, '__module__', 'unknown')
                }
            except Exception:
                pass
        
        # Strategy 5: Iterables (but not strings)
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                content = list(obj)
                # Test if serializable
                json.dumps(content, default=str)
                return {"content": content, "strategy": "iterable"}
            except Exception:
                pass
        
        # Strategy 6: Convert to string representation
        try:
            str_repr = str(obj)
            return {
                "content": str_repr,
                "strategy": "string_repr",
                "type": str(type(obj)),
                "length": len(str_repr)
            }
        except Exception:
            pass
        
        # Strategy 7: Last resort - minimal info
        return {
            "content": f"<Unserializable {type(obj).__name__}>",
            "strategy": "fallback",
            "type": str(type(obj)),
            "error": "Could not serialize object"
        }
    
    def _safe_dict_extract(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Safely extract dictionary, handling non-serializable values"""
        if not isinstance(obj_dict, dict):
            return {}
        
        safe_dict = {}
        
        for key, value in obj_dict.items():
            # Ensure key is string
            str_key = str(key) if not isinstance(key, str) else key
            
            try:
                # Test if value is JSON serializable
                json.dumps(value, default=str)
                safe_dict[str_key] = value
            except (TypeError, ValueError, OverflowError):
                # Handle non-serializable values recursively
                safe_dict[str_key] = self._deep_serialize_value(value)
        
        return safe_dict
    
    def _extract_metadata(self, obj: Any) -> Dict[str, Any]:
        """Extract metadata about the object"""
        try:
            obj_str = str(obj)
            obj_size = len(obj_str)
        except Exception:
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