import httpx
import getpass
from dotenv import load_dotenv
import os

load_dotenv(override=True)

url = os.getenv("url")
connect_timeout_seconds = 2
read_timeout_seconds = 180
username = os.getenv("username")
password = os.getenv("password")


def make_curl_request(username, password, prompt_or_messages):
    """
    Make an HTTP request similar to a curl command using httpx.

    :param username: Username for basic authentication.
    :param password: Password for basic authentication.
    :param prompt_or_messages: A single user prompt string, or a list of message dicts representing conversation history.
    :return: Response object from httpx.
    """
    # Create a client with basic authentication
    client = httpx.Client(auth=(username, password))

    if isinstance(prompt_or_messages, list):
        messages = prompt_or_messages
    else:
        messages = [{"role": "user", "content": prompt_or_messages}]

    json_data = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": messages,
        "temperature": 0,
        "max_tokens": 2000,
    }

    # Send a POST request with JSON data
    response = client.post(
        url,
        auth=(username, password),
        json=json_data,
        timeout=(connect_timeout_seconds, read_timeout_seconds),
    )

    # Close the client
    client.close()

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP Error {response.status_code} occurred:")
        print(response.text)
        raise e

    try:
        response_json = response.json()
    except Exception as e:
        print(f"\nFailed to decode JSON response from server (Status Code: {response.status_code}):")
        print(response.text)
        raise e

    # reasoning_text = response_json["choices"][0]["message"].get("reasoning_content")
    # if reasoning_text:
    #     print("#####Reasoning Start#####")
    #     print(reasoning_text)
    #     print("#####Reasoning End#####")

    try:
        text = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        print("\nUnexpected JSON structure in response:")
        print(response_json)
        raise e

    return text


# Example usage
if __name__ == "__main__":
    messages = []
    print("Chat session started. Type 'quit' to exit, or 'clear' to reset chat memory.")
    while True:
        prompt = input("Prompt: ")

        if prompt == "quit":
            break
        elif prompt == "clear":
            messages = []
            print("Chat memory cleared.")
            continue

        # Add the user message to memory
        messages.append({"role": "user", "content": prompt})

        try:
            response = make_curl_request(username, password, messages)
            print(response)
            # Add the assistant response to memory
            messages.append({"role": "assistant", "content": response})
        except Exception as e:
            # Remove the user message from history if the request failed to prevent pollution
            messages.pop()
            print(f"Request failed: {e}")
