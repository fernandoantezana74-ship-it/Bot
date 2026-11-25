
import os, requests, subprocess, uuid, threading
from flask import Flask, request
app = Flask(__name__)
TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY = os.environ.get("VERIFY_TOKEN", "bro-oreo-123")

procesados = set()

def msg(to, text):
    requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})

def subir_media(path, mime):
    h = {"Authorization": f"Bearer {TOKEN}"}
    with open(path, 'rb') as f:
        r = requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/media", headers=h, files={'file': (path, f, mime), 'messaging_product': (None, 'whatsapp')})
    return r.json().get("id")

def procesar_video(num, mid):
    try:
        msg(num, "Recibi tu video, haciendo sticker + video con sonido...")
        h = {"Authorization": f"Bearer {TOKEN}"}
        url = requests.get(f"https://graph.facebook.com/v21.0/{mid}", headers=h).json().get("url")
        vid = requests.get(url, headers=h).content
        inp = f"/tmp/{uuid.uuid4()}.mp4"
        out_video = f"/tmp/{uuid.uuid4()}.mp4"
        out_sticker = f"/tmp/{uuid.uuid4()}.webp"
        open(inp, 'wb').write(vid)

        # 1. VIDEO CON SONIDO de 3 a 7 seg
        subprocess.run(["ffmpeg", "-y", "-ss", "3", "-t", "4", "-i", inp, "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-c:a", "aac", "-shortest", out_video])
        video_id = subir_media(out_video, 'video/mp4')

        # 2. STICKER SIN SONIDO (WhatsApp no deja sonido en sticker)
        subprocess.run(["ffmpeg", "-y", "-ss", "3", "-t", "4", "-i", inp, "-vf", "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000,fps=15", "-loop", "0", "-an", "-c:v", "libwebp", "-lossless", "0", "-quality", "50", out_sticker])
        sticker_id = subir_media(out_sticker, 'image/webp')

        # Mandar sticker primero
        requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": num, "type": "sticker", "sticker": {"id": sticker_id}})

        # Mandar video con sonido despues
        requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": num, "type": "video", "video": {"id": video_id}})
    except Exception as e:
        print(e)

@app.route("/")
def home():
    return "Bot activo"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY:
            return request.args.get("hub.challenge")
        return "Error", 403
    try:
        data = request.get_json()
        value = data['entry'][0]['changes'][0]['value']
        if 'messages' not in value:
            return "OK", 200
        m = value['messages'][0]
        mid_msg = m.get('id')
        if mid_msg in procesados:
            return "OK", 200
        procesados.add(mid_msg)
        num = m['from']
        if m.get('type') == 'video':
            threading.Thread(target=procesar_video, args=(num, m['video']['id'])).start()
        else:
            if m.get('type') == 'text':
                msg(num, "Mandame un video y te lo recorto de 3 a 7 seg")
    except Exception as e:
        print(e)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
