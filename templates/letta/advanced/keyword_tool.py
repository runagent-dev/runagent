def extract_keywords(text: str, num_keywords: int = 5) -> dict:
    """
    Extract keywords from input text.

    Args:
        text (str): The input text to extract keywords from
        num_keywords (int): Number of keywords to extract (default: 5)

    Returns:
        dict: Dictionary containing the extracted keywords
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate

    # Initialize the language model
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2)

    # Create prompt template for keyword extraction
    prompt_template = """
    Extract exactly {num_keywords} relevant keywords from the following text. 
    Return them as a comma-separated list without numbering or bullet points.
    Only include the keywords, no additional information or explanation.

    Text: {input_text}

    Keywords:
    """

    prompt = PromptTemplate(
        input_variables=["input_text", "num_keywords"],
        template=prompt_template
    )
    
    try:
        # Use the newer pattern with RunnableSequence instead of LLMChain
        chain = prompt | llm

        # Run the chain
        result = chain.invoke({"input_text": text, "num_keywords": num_keywords})

        # Extract content from the response object
        content = result.content if hasattr(result, 'content') else str(result)

        # Clean up and return as list
        keywords = [kw.strip() for kw in content.split(',')]

        return {
            "status": "success",
            "data": {
                "keywords": keywords
            },
            "message": f"Successfully extracted {len(keywords)} keywords."
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "data": None,
            "message": f"Error extracting keywords: {str(e)}",
            "error_details": traceback.format_exc()
        }