import os
import urllib.request
import json
import base64

repo = "franklinbaldo/causaganha"
base_url = f"https://api.github.com/repos/{repo}/pulls"

def get_json(url):
    req = urllib.request.Request(url)
    # Some environments need a User-Agent
    req.add_header('User-Agent', 'CausaGanha-PM-Agent')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def get_messages():
    params = "state=open&sort=updated&direction=desc"
    prs = get_json(f"{base_url}?{params}")

    messages = []
    for pr in prs:
        pr_number = pr["number"]
        files_url = f"{base_url}/{pr_number}/files"
        try:
            files = get_json(files_url)
        except Exception as e:
            print(f"Error fetching files for PR #{pr_number}: {e}")
            continue

        for file in files:
            filename = file["filename"]
            if filename.startswith(".agents/comunication/Maildir/pm/new/") and filename.endswith(".md"):
                print(f"Found message in PR #{pr_number}: {filename}")
                content_url = file["contents_url"]
                try:
                    content_data = get_json(content_url)
                    content = base64.b64decode(content_data["content"]).decode("utf-8")
                    messages.append({
                        "pr": pr_number,
                        "filename": os.path.basename(filename),
                        "content": content
                    })
                except Exception as e:
                    print(f"Error fetching content for {filename}: {e}")
    return messages

if __name__ == "__main__":
    messages = get_messages()
    with open("synced_messages.json", "w") as f:
        json.dump(messages, f, indent=2)
