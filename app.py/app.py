import os, requests, subprocess, uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "bro-oreo-123")

def send_message(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, headers=headers, json=data)

def send_video(to, video_path, caption):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with open(video_path, 'rb') as f:
        files = {'file': (video_path, f, 'video/mp4'), 'messaging_product': (None, 'whatsapp')}
        r = requests.post(url, headers=headers, files=files)
    media_id = r.json().get("id")
    if not media_id:
        send_message(to, "Error subiendo video")
        return
    url2 = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers2 = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "video", "video": {"id": media_id, "caption": caption}}
    requests.post(url2, headers=headers2, json=data)

@app.route("/", methods=["GET"])
def home():
    return "Bot Bro Oreo activo"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403
    data = request.get_json()
    try:
        msg = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_num = msg['from']
        if msg.get('type') == 'video':
            send_message(from_num, "Recibi tu video bro, lo estoy recortando de 3 a 7 seg...")
            media_id = msg['video']['id']
            headers = {"Authorization": f"Bearer {TOKEN}"}
            info = requests.get(f"https://graph.facebook.com/v21.0/{media_id}", headers=headers).json()
            video_url = info.get("url")
            r = requests.get(video_url, headers=headers)
            input_path = f"/tmp/{uuid.uuid4()}.mp4"
            output_path = f"/tmp/{uuid.uuid4()}_out.mp4"
            open(input_path, 'wb').write(r.content)
            subprocess.run(["ffmpeg", "-y", "-ss", "3", "-t", "4", "-i", input_path, "-vf", "drawtext=text='EL HDPT DE MI BRO':fontcolor=white:fontsize=48:borderw=3:bordercolor=black:x=(w-text_w)/2:y=50", "-c:a", "aac", output_path])
            send_video(from_num, output_path, "EL HDPT DE MI BRO")
        elif msg.get('type') == 'text':
            send_message(from_num, "Mandame un video y te lo recorto de 3 a 7 seg con el texto EL HDPT DE MI BRO")
    except Exception as e:
        print("Error:", e)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
