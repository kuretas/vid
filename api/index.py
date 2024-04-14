from flask import Flask, abort, jsonify, request, make_response, Response, send_file
from quart import Quart, abort, jsonify, request, make_response, Response, send_file

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
import os
import requests
from static import COMMAND_IDS


# app = Flask(__name__)
app = Quart(__name__)
# PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
# BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
VIDEO_CHANNEL_ID = os.environ.get("VIDEO_CHANNEL_ID")
FAILED_CHANNEL_ID = os.environ.get("FAILED_CHANNEL_ID")


async def send_video(url):
    print("send_video")
    r = requests.get(url)
    img_b = r.content
    print("loaded")
    file = {"file": ("video.mp4", img_b)}
    api_url = f"https://discord.com/api/v10/channels/{VIDEO_CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    r = requests.post(
        api_url,
        headers=headers,
        data={"content": f"```\n{url}\n```"},
        files=file,
    )
    print("sent")
    if r.status_code != 200:
        r = requests.post(
            f"https://discord.com/api/v10/channels/{FAILED_CHANNEL_ID}/messages",
            headers=headers,
            data={"content": f"{url}"},
        )
        print("sent2", r.status_code, r.text)


@app.route("/api/interactions", methods=["POST"])
async def interactions():
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    message = timestamp.encode() + await request.data
    try:
        verify_key.verify(message, bytes.fromhex(signature))
    except BadSignatureError:
        abort(401, "Incorrect Signature")

    content = await request.json
    data = content.get("data", {})
    print(content)
    # ping
    if content["type"] == 1:
        return jsonify({"type": 1})
    if content["type"] == 5:
        components = data.get("components", [])
        url: str = components[0]["components"][0]["value"]
        if not url.startswith("https://video.twimg.com/"):
            return jsonify(
                {
                    "type": 4,
                    "data": {
                        "content": "Invalid URL",
                        "flags": 64,
                    },
                }
            )

        app.add_background_task(send_video, url)

        return jsonify(
            {
                "type": 4,
                "data": {
                    "content": "Success",
                    "flags": 64,
                },
            }
        )

    if data.get("id"):
        command_id = data["id"]
        if command_id == COMMAND_IDS["modal"]:

            return jsonify(
                {
                    "type": 9,
                    "data": {
                        "custom_id": "modal",
                        "title": "Modal",
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {
                                        "type": 4,
                                        "label": "URL",
                                        "style": 1,
                                        "custom_id": "url",
                                        "placeholder": "https://twitter.com/~",
                                        "required": True,
                                    }
                                ],
                            }
                        ],
                    },
                }
                # {
                #     "type": 4,
                #     "data": {
                #         "content": "Hello, World!",
                #         "flags": 64,
                #     },
                # }
            )
        if command_id == COMMAND_IDS["send"]:
            options = content["data"]["options"]
            url = options[0]["value"]
            app.add_background_task(send_video, url)
            return jsonify(
                {
                    "type": 4,
                    "data": {
                        "content": "Success",
                        "flags": 64,
                    },
                }
            )


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
