# llm_interface.py
import openai
import asyncio
import re
# Remove direct config import
# from config import API_KEY, OPENROUTER_MODEL, OPENROUTER_API_BASE

async def get_llm_response(prompt: str, api_key: str, model: str, api_base: str) -> str | None:
    """
    Sends a prompt to the specified OpenRouter LLM endpoint and returns the response content.

    Args:
        prompt: The user prompt to send to the LLM.
        api_key: The API key for authentication.
        model: The identifier of the LLM model to use.
        api_base: The base URL for the API endpoint.
    """
    if not api_key:
        print("Error: API Key not provided.")
        return None
    if not model:
        print("Error: LLM Model not provided.")
        return None
    if not api_base:
        print("Error: API Base URL not provided.")
        return None

    client = openai.AsyncOpenAI(
        base_url=api_base,
        api_key=api_key,
    )

    try:
        print(f"\n--- Sending Prompt to {model} ---")
        # print(prompt) # Optional: Print the exact prompt being sent
        print("--- End Prompt ---")

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.2, # Lower temperature for more predictable netlist generation
            max_tokens=1500, # Adjust as needed
            stream=False, # Wait for full response
        )

        print("--- LLM Response Received ---")
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            # print(content) # Optional: Print raw response content
            return content.strip()
        else:
            print("Error: No response choices received from LLM.")
            return None

    except openai.AuthenticationError:
        print("Error: OpenRouter Authentication Failed. Check your API Key.")
        return None
    except openai.RateLimitError:
        print("Error: OpenRouter Rate Limit Exceeded. Please wait and try again.")
        return None
    except openai.APIConnectionError as e:
        print(f"Error: Could not connect to OpenRouter API: {e}")
        return None
    except openai.NotFoundError as e:
        # Handle 404 errors which include model expiration
        error_message = str(e)
        if "alpha period" in error_message.lower() or "model has ended" in error_message.lower():
            print(f"Error: The model '{model}' is no longer available. The alpha period has ended.")
            # Return a special error message that the UI can detect
            return "__MODEL_EXPIRED__: The alpha period for this model has ended. Please update your model in settings."
        else:
            print(f"Error: Model not found: {e}")
            return None
    except Exception as e:
        error_message = str(e)
        print(f"An unexpected error occurred during LLM communication: {e}")
        # Check if the error message contains information about model expiration
        if "404" in error_message and ("alpha period" in error_message.lower() or "model has ended" in error_message.lower()):
            return "__MODEL_EXPIRED__: The alpha period for this model has ended. Please update your model in settings."
        return None
    finally:
        # Ensure client resources are potentially cleaned up if necessary,
        # though libraries often manage this. Explicit close might be needed
        # in specific long-running or resource-constrained scenarios.
        # await client.close() # Generally not needed for single calls with newer libraries
        pass

def extract_spice_netlist(llm_response: str) -> tuple[str | None, str | None]:
    """
    Extracts the SPICE netlist content and summary message from the LLM response.

    Args:
        llm_response: The raw response from the LLM

    Returns:
        A tuple containing (netlist, summary_message)
        - netlist: The extracted SPICE netlist or None if not found
        - summary_message: Any explanatory text outside the code block, or None if not present
    """
    if not llm_response:
        return None, None

    # Initialize summary message as None
    summary_message = None
    netlist = None

    # Pattern 1: Look for ```spice ... ```
    match = re.search(r'```spice\s*([\s\S]*?)\s*```', llm_response, re.IGNORECASE)
    if match:
        print("Found ```spice ... ``` block.")
        netlist = match.group(1).strip()

        # Extract summary message (text before and/or after the code block)
        code_block = match.group(0)  # The entire code block including ```
        parts = llm_response.split(code_block, 1)

        # Combine text before and after the code block
        summary_parts = []
        if parts[0].strip():
            summary_parts.append(parts[0].strip())
        if len(parts) > 1 and parts[1].strip():
            summary_parts.append(parts[1].strip())

        if summary_parts:
            summary_message = "\n\n".join(summary_parts)

        return netlist, summary_message

    # Pattern 2: Look for generic ``` ... ```
    match = re.search(r'```\s*([\s\S]*?)\s*```', llm_response)
    if match:
        print("Found generic ``` ... ``` block.")
        # Basic check if it looks like a netlist
        content = match.group(1).strip()
        lines = content.split('\n')
        if lines and (lines[0].strip().startswith(('*', 'V', 'R', 'I', 'C', 'L', 'D', 'M', 'K', 'X', '.')) or lines[-1].strip().lower() == '.end'):
            print("Content inside ``` looks like a netlist.")
            netlist = content

            # Extract summary message
            code_block = match.group(0)  # The entire code block including ```
            parts = llm_response.split(code_block, 1)

            # Combine text before and after the code block
            summary_parts = []
            if parts[0].strip():
                summary_parts.append(parts[0].strip())
            if len(parts) > 1 and parts[1].strip():
                summary_parts.append(parts[1].strip())

            if summary_parts:
                summary_message = "\n\n".join(summary_parts)

            return netlist, summary_message
        else:
            print("Content inside ``` didn't look like a netlist, discarding.")

    # Pattern 3: Fallback - Check if the entire response might be a netlist
    print("No code block found, checking if entire response is a netlist.")
    lines = llm_response.strip().split('\n')
    # Heuristic: Starts with a comment/component/directive and ends with .end
    if lines and \
       (lines[0].strip().startswith(('*', 'V', 'R', 'I', 'C', 'L', 'D', 'M', 'K', 'X', '.'))) and \
       (lines[-1].strip().lower() == '.end'):
        print("Entire response seems like a plausible netlist.")
        netlist = llm_response.strip()
        # No summary in this case since the entire response is the netlist
        return netlist, None

    print("Could not extract a valid SPICE netlist from the response.")
    return None, llm_response  # Return the entire response as the summary if no netlist found

# --- Add a test case for the extractor ---
def test_extractor():
    print("\n--- Testing Netlist Extractor ---")
    test_cases = [
        # Input, Expected (netlist, summary)
        ("Some text before\n```spice\nV1 1 0 1V\nR1 1 0 1k\n.end\n```\nSome text after",
         ("V1 1 0 1V\nR1 1 0 1k\n.end", "Some text before\n\nSome text after")),

        ("```\nV1 1 0 1V\nR1 1 0 1k\n.end\n```",
         ("V1 1 0 1V\nR1 1 0 1k\n.end", None)),

        ("* Just the netlist\nV1 1 0 1V\nR1 1 0 1k\n.end",
         ("* Just the netlist\nV1 1 0 1V\nR1 1 0 1k\n.end", None)),

        ("Here is the netlist:\n```spice\n* Comment\nV1 1 0 5V\nR1 1 0 10k\n.tran 1m\n.end\n```",
         ("* Comment\nV1 1 0 5V\nR1 1 0 10k\n.tran 1m\n.end", "Here is the netlist:")),

        ("I've created a simple RC circuit with a 5V source.\n```spice\n* RC Circuit\nV1 1 0 5V\nR1 1 2 1k\nC1 2 0 1uF\n.tran 10ms\n.end\n```\nThe circuit has a time constant of 1ms (R*C = 1k * 1uF).",
         ("* RC Circuit\nV1 1 0 5V\nR1 1 2 1k\nC1 2 0 1uF\n.tran 10ms\n.end", "I've created a simple RC circuit with a 5V source.\n\nThe circuit has a time constant of 1ms (R*C = 1k * 1uF).")),

        ("Sure, here it is:\n V1 1 0 1V\n R1 1 0 1k\n .end ",
         (None, "Sure, here it is:\n V1 1 0 1V\n R1 1 0 1k\n .end ")), # Should fail without ``` or * start AND .end

        ("```cpp\nint main() { return 0; }\n```",
         (None, "```cpp\nint main() { return 0; }\n```")), # Wrong language tag, content rejected
    ]

    for i, (input_str, expected_output) in enumerate(test_cases):
        netlist, summary = extract_spice_netlist(input_str)
        expected_netlist, expected_summary = expected_output

        print(f"Test Case {i+1}: ", end="")
        if netlist == expected_netlist and summary == expected_summary:
            print("Passed")
        else:
            print("Failed!")
            print(f"Input:\n'''{input_str}'''")
            print(f"Expected netlist:\n'''{expected_netlist}'''")
            print(f"Got netlist:\n'''{netlist}'''")
            print(f"Expected summary:\n'''{expected_summary}'''")
            print(f"Got summary:\n'''{summary}'''")
            print("-" * 20)

# List of alternative models that can be suggested when a model expires
ALTERNATIVE_MODELS = [
    "openrouter/anthropic/claude-3-opus:beta",
    "openrouter/anthropic/claude-3-sonnet:beta",
    "openrouter/anthropic/claude-3-haiku:beta",
    "openrouter/meta-llama/llama-3-70b-instruct",
    "openrouter/meta-llama/llama-3-8b-instruct",
    "openrouter/google/gemini-1.5-pro"
]

def get_alternative_models() -> list[str]:
    """Returns a list of alternative models that can be used if the current model is expired."""
    return ALTERNATIVE_MODELS

def is_model_expired_message(message: str) -> bool:
    """Checks if the message indicates that the model has expired."""
    if not message:
        return False
    return message.startswith("__MODEL_EXPIRED__:")

def extract_model_expired_message(message: str) -> str:
    """Extracts the human-readable part of the model expired message."""
    if not is_model_expired_message(message):
        return ""
    return message.replace("__MODEL_EXPIRED__:", "").strip()

# Optional: Add a small test block
async def main_test():
    # Note: This test function now requires config values to be passed
    # It won't run as is without modification or loading config here.
    print("LLM API test requires manual configuration passing now.")
    # Example (requires setting these variables first):
    # test_prompt = "Explain SPICE netlist syntax for a resistor in one sentence."
    # print(f"Testing LLM call with prompt: '{test_prompt}'")
    # response = await get_llm_response(
    #     prompt=test_prompt,
    #     api_key="YOUR_KEY", # Replace or load
    #     model="YOUR_MODEL", # Replace or load
    #     api_base="YOUR_URL" # Replace or load
    # )
    response = None # Keep it runnable without API call for now
    if response:
        print("\nLLM Test Response:")
        print(response)
    else:
        print("\nLLM Test Failed.")

if __name__ == "__main__":
    # To run this test: python llm_interface.py (ensure env vars are set)
    # Note: Running async code directly might require asyncio.run()
    test_extractor()
    # Uncomment to test the LLM API call
    # asyncio.run(main_test())
