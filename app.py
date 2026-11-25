import os, requests, subprocess, uuid, threading
from flask import Flask, request
app = Flask(__name__)
TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY = os.environ.get("VERIFY_TOKEN", "bro-oreo-123")

# Para no repetir mensajes
procesados = set()

def msg(to, text):
    requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})

def procesar_video(num, mid):
    try:
        msg(num, "Recibi tu video, recortando de 3 a 7 seg...")
        h = {"Authorization": f"Bearer {TOKEN}"}
        url = requests.get(f"https://graph.facebook.com/v21.0/{mid}", headers=h).json().get("url")
        vid = requests.get(url, headers=h).content
        inp = f"/tmp/{uuid.uuid4()}.mp4"
        out = f"/tmp/{uuid.uuid4()}.mp4"
        open(inp, 'wb').write(vid)
        subprocess.run(["ffmpeg", "-y", "-ss", "3", "-t", "4", "-i", inp, "-c:a", "aac", out])
        with open(out, 'rb') as f:
            r = requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/media", headers=h, files={'file': (out, f, 'video/mp4'), 'messaging_product': (None, 'whatsapp')})
        media_id = r.json().get("id")
        # SIN caption, ya no copia ninguna frase
        requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": num, "type": "video", "video": {"id": media_id}})
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
        # Si es solo un estado (leido, entregado) ignorar
        if 'messages' not in value:
            return "OK", 200
        m = value['messages'][0]
        # Si ya lo procesamos, ignorar - ESTO EVITA QUE REPITA
        mid_msg = m.get('id')
        if mid_msg in procesados:
            return "OK", 200
        procesados.add(mid_msg)

        num = m['from']
        if m.get('type') == 'video':
            # Responder OK al instante y recortar en segundo plano
            threading.Thread(target=procesar_video, args=(num, m['video']['id'])).start()
        else:
            # Solo responder a texto si no es un estado
            if m.get('type') == 'text':
                msg(num, "Mandame un video y te lo recorto de 3 a 7 seg")
    except Exception as e:
        print(e)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
