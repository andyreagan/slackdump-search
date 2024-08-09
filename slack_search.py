import glob
import gzip
import json
import os
import re
import subprocess
import sys
import webbrowser
from datetime import datetime
from typing import Iterable, Tuple


def search_in_stream(
    file_stream: Iterable[str], search_term: str
) -> Iterable[Tuple[str, str, str, str, str]]:
    """
        Search for a given term in a stream of JSON data and yield the matching message IDs, message texts, and URLs.

    n    Args:
            file_stream (Iterable[str]): A stream of JSON data.
            search_term (str): The search term to look for.

        Yields:
            Tuple[str, str, str]: The message ID, message text, and URL for each matching message.
    """
    for line in file_stream:
        data = json.loads(line)
        channel = data["id"]
        is_thread = data["t"] == 1
        timestamp = data["r"] if is_thread else None
        if "m" not in data:
            continue
        for message in data["m"]:
            if "text" not in message:
                # print('no text in message')
                continue
            message_text = message["text"]
            message_id = message["ts"]
            user = message.get("user")
            if re.search(search_term, message_text, re.IGNORECASE):
                if is_thread:
                    url = generate_thread_url(channel, timestamp, message_id)
                else:
                    url = generate_message_url(channel, message_id)
                yield (channel, user, message_id, message_text, url)


def get_user_lookup(file_path: str) -> dict[str, str]:
    user_lookup = {}
    with gzip.open(file_path, "rt") as f:
        for line in f:
            users = json.loads(line)["u"]
            for user in users:
                user_id = user["id"]
                display_name = user["profile"]["display_name"]
                user_lookup[user_id] = display_name
    return user_lookup


def get_channel_lookup(directory_path: str, user_lookup: dict[str, str]) -> dict[str, str]:
    channel_lookup = {}
    for filename in os.listdir(directory_path):
        if filename.endswith(".json.gz"):
            file_path = os.path.join(directory_path, filename)
            with gzip.open(file_path, "rt") as f:
                for line in f:
                    data = json.loads(line)
                    if data["t"] == 5:  # Check for "t: 5" entries
                        channel_id = data["id"]
                        channel_info = data["ci"]

                        # Determine the best name to use
                        if channel_info["is_im"]:
                            # For direct messages, use "dm_" prefix with the user ID
                            if channel_info["user"] in user_lookup:
                                channel_name = f"@{user_lookup[channel_info['user']]}"
                            else:
                                channel_name = f"@{channel_info['user']}"
                        elif channel_info["name"]:
                            channel_name = channel_info["name"]
                        elif channel_info["name_normalized"]:
                            channel_name = channel_info["name_normalized"]
                        else:
                            channel_name = (
                                channel_id  # Fallback to channel ID if no name is available
                            )

                        channel_lookup[channel_id] = channel_name
                        break  # Stop after finding the first "t: 5" entry
    return channel_lookup


def search_json(file_stream: Iterable[str], dir: str, search_term: str) -> str:
    """
    Search for a given term in a stream of JSON data and return an HTML string with the matching messages and their URLs.
    Args:
        file_stream (Iterable[str]): A stream of JSON data.
        search_term (str): The search term to look for.
    Returns:
        str: An HTML string with the search results.
    """
    matches = list(search_in_stream(file_stream, search_term))
    html_output = f"<h2>Found {len(matches)} matches:</h2>"
    user_lookup = get_user_lookup(f"{dir}/users.json.gz")
    channel_lookup = get_channel_lookup(dir, user_lookup)
    sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
    for channel, user, message_id, message_text, url in sorted_matches:
        date_time = datetime.fromtimestamp(float(message_id)).strftime("%Y-%m-%d %H:%M:%S")
        html_output += f"""
<article class="message">
    <header class="message-header" id="{message_id}">
        <span class="message-sender">
            <a href="http://localhost:8080/archives/{channel}" hx-get="/team/[team-id]" hx-target="#thread"> {channel_lookup[channel]}</a>
        </span>
        <span class="message-sender">
            <a href="#" hx-get="/team/{user}" hx-target="#thread"> {user_lookup.get(user, user)}</a>
        </span>
        <span class="message-timestamp grey">{date_time}</span>
        <span class="message-link"><a href="{url}">open</a></span>
    </header>
    <div class="message-content">
        <p>{message_text}</p>
    </div>
</article>
"""
    return html_output


def generate_message_url(channel: str, message_id: str) -> str:
    """
    Generate a URL for a message.

    Args:
        channel (str): The channel ID.
        message_id (str): The message ID.

    Returns:
        str: The URL for the message.
    """
    return f"http://localhost:8080/archives/{channel}#{message_id}"


def generate_thread_url(channel: str, thread_id: str, message_id: str) -> str:
    """
    Generate a URL for a message in a thread.

    Args:
        channel (str): The channel ID.
        thread_id (str): The thread ID.
        message_id (str): The message ID.

    Returns:
        str: The URL for the message in the thread.
    """
    return f"http://localhost:8080/archives/{channel}/{thread_id}#{message_id}"


def write_html(body: str) -> None:
    # Create an HTML file
    html_content = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <title>Search results</title>
          <style>
              body {{
                  font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
              }}

              @media (prefers-color-scheme: dark) {{
                  body {{

                      background-color: #202224;
                      color: #fff;
                  }}

                  a {{
                      color: #72b2ff;
                  }}

                  a:hover {{
                      color: #ff7b72;
                  }}

                  a:visited {{
                      color: #9669ff;
                  }}
              }}

              blockquote {{
                  margin: 0;
                  padding: 0;
                  border-left: 2px solid gray;
                  margin-left: 1em;
              }}

              .container {{
                  display: flex;
                  height: 97vh;
              }}

              .subtitle {{
                  display: block;
                  margin-bottom: 1em;
              }}

              .channel-list {{
                  flex: 0 0 20%;
                  overflow-y: auto;
                  border-right: 1px solid #ccc;
              }}

              .message {{
                  margin-left: 1em;
              }}

              .message-content {{
                  margin-left: 1em;
              }}

              .thread-info {{
                  margin-left: 1em;
                  margin-bottom: 1em;
              }}

              .welcome {{
                  text-align: center;
              }}

              .conversations {{
                  flex: 0 0 40%;
                  overflow-y: auto;
              }}

              .thread {{
                  flex: 1;
                  overflow-y: auto;
                  display: block;
              }}

              .message-timestamp,
              .message-link,
              .last-reply,
              .small {{
                  font-size: 12px;
              }}

              .slack-attachment .icon {{
                  max-width: 16px;
                  max-height: 16px;
              }}
              .slack-attachment .attachment-image {{
                  max-height: 136px;
                  max-width: 136px;
                  border-radius: 5px;
              }}

              .slack-files img {{
                  max-width: 320px;
                  max-height: 320px;
              }}

              .grey {{
                  color: #777;
              }}
          </style>
      </head>
      <body>
        {body}
      </body>
    </html>
    """

    # Write the HTML content to a file
    temp_file = "results.html"
    with open(temp_file, "w") as f:
        f.write(html_content)

    # Open the HTML file in the default web browser
    webbrowser.open(f"file://{os.path.abspath(temp_file)}")

    # time.sleep(5)

    # # Delete the temporary file
    # os.remove(temp_file)
    # print("The temporary HTML file has been deleted.")


def search_folder(folder_path: str, search_term: str) -> str | None:
    # Use glob to expand the pattern
    files = glob.glob(os.path.join(folder_path, "*.json.gz"))
    if not files:
        print(f"Error: No .json.gz files found in {folder_path}", file=sys.stderr)
        return None

    # Use zgrep on the expanded list of files
    cmd = ["zgrep", "-ih", search_term] + files
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if stderr:
        print(f"Error: {stderr}", file=sys.stderr)
        return None

    return search_json(stdout.splitlines(), folder_path, search_term)


if __name__ == "__main__":
    if len(sys.argv) == 4:
        input_path = sys.argv[1]
        slackdump_folder = sys.argv[2]
        search_term = sys.argv[3]

        if os.path.isdir(input_path):
            output = search_folder(input_path, search_term)
        elif input_path == "-":
            output = search_json(sys.stdin, slackdump_folder, search_term)
        elif os.path.isfile(input_path):
            with open(input_path, "r") as file:
                output = search_json(file, slackdump_folder, search_term)
        else:
            print(f"Error: {input_path} is not a valid file or directory", file=sys.stderr)
            sys.exit(1)

        if output is not None:
            write_html(output)
    else:
        print(
            "Usage: python slack_search.py <JSON file_path or directory> <directory> <search term>"
        )
        print(
            'or use stdin: zgrep -ih "$SEARCH_TERM" slackdump_20240807_214838/*.json.gz | python3 slack_search.py - slackdump_20240807_214838 "$SEARCH_TERM"'
        )
