import time
import random
import threading
from typing import Iterator, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    TEXT = "text"
    EMAIL = "email"
    CODE = "code"
    ANALYSIS = "analysis"


@dataclass
class StreamChunk:
    """Simulates streaming response chunks"""
    content: str
    delta: str
    finished: bool = False
    
    
@dataclass
class CompletionResponse:
    """Simulates a complete AI response"""
    content: str
    model: str
    usage_tokens: int
    response_time: float


class MockAIAgent:
    """
    A comprehensive mock AI agent that simulates realistic AI behavior
    including streaming responses, processing delays, and varied outputs.
    """
    
    def __init__(self, model_name: str = "mock-gpt-4", response_delay: float = 0.1):
        self.model_name = model_name
        self.response_delay = response_delay
        self.conversation_history = []
        
        # Pre-defined response templates for different types of requests
        self.email_templates = [
            """Subject: {subject}

Dear {recipient},

I hope this email finds you well. I am writing to {purpose}.

{body_content}

I would appreciate your prompt response on this matter.

Best regards,
{sender}""",
            
            """Subject: {subject}

Hello {recipient},

Thank you for your time. I wanted to reach out regarding {purpose}.

{body_content}

Please let me know if you have any questions or need additional information.

Sincerely,
{sender}""",
        ]
        
        self.code_templates = {
            "python": """def {function_name}({params}):
    \"\"\"
    {description}
    \"\"\"
    # Implementation here
    {implementation}
    return result""",
            
            "javascript": """function {function_name}({params}) {{
    /**
     * {description}
     */
    {implementation}
    return result;
}}""",
        }
        
        # Realistic response variations
        self.greeting_variations = [
            "I'll help you with that.",
            "Let me assist you with this request.",
            "I'd be happy to help.",
            "Here's what I can do for you:",
        ]
        
    def _simulate_thinking_delay(self, content_length: int = 100):
        """Simulate AI processing time based on content complexity"""
        base_delay = 0.5
        complexity_delay = content_length / 1000  # More complex = longer delay
        total_delay = base_delay + complexity_delay + random.uniform(0.1, 0.3)
        time.sleep(min(total_delay, 3.0))  # Cap at 3 seconds
        
    def _get_email_body_content(self, subject: str, context: str = "") -> str:
        """Generate contextual email body content"""
        subject_lower = subject.lower()
        
        if "meeting" in subject_lower:
            return """I would like to schedule a meeting to discuss the upcoming project milestones. Would you be available sometime next week? I'm flexible with timing and can accommodate your schedule.

The meeting should take approximately 30-45 minutes, and we can conduct it either in person or via video call, whichever works better for you."""
        
        elif "follow up" in subject_lower or "followup" in subject_lower:
            return """I wanted to follow up on our previous conversation regarding the project timeline. As discussed, I believe we should move forward with the proposed changes.

Could you please confirm if you've had a chance to review the documents I shared? I'm happy to address any questions or concerns you might have."""
        
        elif "request" in subject_lower:
            return """I am writing to formally request your assistance with an important matter. Your expertise in this area would be invaluable to our success.

I understand you have a busy schedule, but I would greatly appreciate any time you could spare to help us move this forward."""
        
        else:
            return f"""I hope you're doing well. I'm reaching out to discuss {subject.lower()} and would value your input on this matter.

Your insights would be extremely helpful as we work through the next steps. Please let me know when would be a good time to connect."""
    
    def _generate_code_implementation(self, language: str, description: str) -> str:
        """Generate mock code implementations"""
        if "sort" in description.lower():
            if language == "python":
                return """    data = list(input_data)
    data.sort()"""
            else:
                return """    let sortedData = [...inputData].sort();"""
        
        elif "calculate" in description.lower() or "math" in description.lower():
            if language == "python":
                return """    result = sum(numbers) / len(numbers)"""
            else:
                return """    const result = numbers.reduce((a, b) => a + b, 0) / numbers.length;"""
        
        else:
            if language == "python":
                return """    # Process the input
    processed_data = process_input(input_data)
    result = perform_operation(processed_data)"""
            else:
                return """    // Process the input
    const processedData = processInput(inputData);
    const result = performOperation(processedData);"""
    
    def chat_completion_create(self, 
                             messages: list, 
                             model: str = None,
                             stream: bool = False,
                             max_tokens: int = 1000,
                             temperature: float = 0.7):
        """
        Main method to simulate AI chat completion
        """
        if not model:
            model = self.model_name
            
        # Extract the user's message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Store in conversation history
        self.conversation_history.extend(messages)
        
        # Determine response type and generate content
        response_content = self._generate_response_content(user_message)
        
        if stream:
            return self._stream_response(response_content)
        else:
            # Simulate processing delay
            self._simulate_thinking_delay(len(response_content))
            
            return CompletionResponse(
                content=response_content,
                model=model,
                usage_tokens=len(response_content.split()) + 20,  # Rough token estimate
                response_time=random.uniform(0.8, 2.1)
            )
    
    def _generate_response_content(self, user_message: str) -> str:
        """Generate appropriate response based on user input"""
        message_lower = user_message.lower()
        
        # Email generation
        if "email" in message_lower or "write" in message_lower:
            return self._generate_email_response(user_message)
        
        # Code generation
        elif "code" in message_lower or "function" in message_lower or "python" in message_lower or "javascript" in message_lower:
            return self._generate_code_response(user_message)
        
        # Analysis requests
        elif "analyze" in message_lower or "summary" in message_lower or "explain" in message_lower:
            return self._generate_analysis_response(user_message)
        
        # General conversation
        else:
            return self._generate_general_response(user_message)
    
    def _generate_email_response(self, user_message: str) -> str:
        """Generate mock email content"""
        greeting = random.choice(self.greeting_variations)
        template = random.choice(self.email_templates)
        
        # Extract details from user message or use defaults
        sender = "John Doe"
        recipient = "Jane Smith"
        subject = "Professional Inquiry"
        purpose = "discuss an important matter"
        
        # Try to extract actual details from the message
        if "sender:" in user_message.lower():
            sender = user_message.split("sender:")[1].split("\n")[0].strip()
        if "recipient:" in user_message.lower():
            recipient = user_message.split("recipient:")[1].split("\n")[0].strip()
        if "subject:" in user_message.lower():
            subject = user_message.split("subject:")[1].split("\n")[0].strip()
        
        body_content = self._get_email_body_content(subject)
        
        email_content = template.format(
            sender=sender,
            recipient=recipient,
            subject=subject,
            purpose=purpose,
            body_content=body_content
        )
        
        return f"{greeting}\n\nHere's a professional email for you:\n\n{email_content}"
    
    def _generate_code_response(self, user_message: str) -> str:
        """Generate mock code content"""
        greeting = random.choice(self.greeting_variations)
        
        # Determine language
        language = "python"
        if "javascript" in user_message.lower() or "js" in user_message.lower():
            language = "javascript"
        
        # Generate function details
        function_name = "processData"
        params = "data"
        description = "Process the input data and return results"
        
        # Try to extract details from message
        if "function" in user_message:
            words = user_message.split()
            for i, word in enumerate(words):
                if word == "function" and i + 1 < len(words):
                    function_name = words[i + 1].replace("(", "").replace(")", "")
                    break
        
        template = self.code_templates[language]
        implementation = self._generate_code_implementation(language, user_message)
        
        code_content = template.format(
            function_name=function_name,
            params=params,
            description=description,
            implementation=implementation
        )
        
        return f"{greeting}\n\nHere's the {language} code you requested:\n\n```{language}\n{code_content}\n```\n\nThis function should handle your requirements. Let me know if you need any modifications!"
    
    def _generate_analysis_response(self, user_message: str) -> str:
        """Generate mock analysis content"""
        greeting = random.choice(self.greeting_variations)
        
        analysis_content = """Based on my analysis, here are the key findings:

**Main Points:**
- The topic you've mentioned has several important aspects to consider
- Current trends suggest this is an area of growing importance
- There are both opportunities and challenges to be aware of

**Recommendations:**
1. Focus on the core elements that drive the most value
2. Consider implementing a phased approach to minimize risk
3. Monitor key metrics to track progress and adjust strategy as needed

**Next Steps:**
- Gather additional data to validate these initial findings
- Consult with stakeholders to ensure alignment
- Develop a detailed implementation plan

This analysis provides a solid foundation for moving forward. Would you like me to dive deeper into any specific aspect?"""
        
        return f"{greeting}\n\n{analysis_content}"
    
    def _generate_general_response(self, user_message: str) -> str:
        """Generate general conversational response"""
        responses = [
            "That's an interesting question. Let me share some thoughts on that topic.",
            "I understand what you're asking about. Here's how I'd approach this:",
            "Thanks for bringing this up. This is definitely worth discussing.",
            "Good point! Let me break this down for you:",
        ]
        
        intro = random.choice(responses)
        
        # Generate contextual content based on message
        if "?" in user_message:
            content = """Based on the information available, there are several factors to consider. The best approach typically depends on your specific situation and goals.

I'd recommend starting with the fundamentals and building from there. This gives you a solid foundation and allows for adjustments as you learn more.

Is there a particular aspect you'd like to explore in more detail?"""
        else:
            content = """That's a valuable insight. This topic has several dimensions worth exploring further.

From my perspective, the key is to balance different considerations while staying focused on your primary objectives. It's often helpful to break complex topics into smaller, manageable parts.

What's your experience been with this so far?"""
        
        return f"{intro}\n\n{content}"
    
    def _stream_response(self, full_content: str) -> Iterator[StreamChunk]:
        """Simulate streaming response with realistic timing"""
        words = full_content.split()
        current_content = ""
        
        # Initial delay
        time.sleep(random.uniform(0.3, 0.8))
        
        for i, word in enumerate(words):
            # Add word to current content
            if current_content:
                current_content += " " + word
            else:
                current_content = word
            
            # Create delta (just the new word)
            delta = " " + word if current_content != word else word
            
            # Yield chunk
            yield StreamChunk(
                content=current_content,
                delta=delta,
                finished=False
            )
            
            # Variable delay between words (simulate typing speed)
            if random.random() < 0.1:  # 10% chance of longer pause
                time.sleep(random.uniform(0.2, 0.5))  # Thinking pause
            else:
                time.sleep(random.uniform(0.02, 0.1))  # Normal typing speed
        
        # Final chunk
        yield StreamChunk(
            content=full_content,
            delta="",
            finished=True
        )


# Convenient wrapper functions to match OpenAI-style API
class MockOpenAIClient:
    """OpenAI-compatible mock client"""
    
    def __init__(self):
        self.agent = MockAIAgent()
        self.chat = self
        self.completions = self
    
    def create(self,
               model: str = "gpt-4",
               messages: list = None,
               stream: bool = False,
               **kwargs):
        """OpenAI-compatible create method"""
        return self.agent.chat_completion_create(
            messages=messages or [],
            model=model,
            stream=stream,
            **kwargs
        )
