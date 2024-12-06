import os
from flask import Flask, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import requests

# Configurações a partir de variáveis de ambiente do Render
MONGO_URI = os.environ.get('MONGO_URI')
DB_NAME = os.environ.get('DB_NAME')
ZAPI_INSTANCE = os.environ.get('ZAPI_INSTANCE')
ZAPI_TOKEN = os.environ.get('ZAPI_TOKEN')
CLIENT_TOKEN = os.environ.get('CLIENT_TOKEN')
ZAPI_BASE_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}"
GRUPOS_WHATSAPP = ["120363356072490260-group"]  # Substitua pelos IDs de grupo
HORARIO_SILENCIO_INICIO = 22  # 22:00
HORARIO_SILENCIO_FIM = 8  # 08:00

# Conexão MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
produtos_collection = db.produtos
mensagens_enviadas_collection = db.mensagens_enviadas
engajamento_collection = db.engajamento

# Inicialização do Flask
app = Flask(__name__)

# Rota básica para testar o servidor
@app.route('/')
def home():
    return jsonify({"status": "Servidor rodando!", "timestamp": datetime.now(timezone.utc).isoformat()}), 200

# Função para verificar conexão com WhatsApp
def verificar_conexao():
    url = f"{ZAPI_BASE_URL}/status"
    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        status = response.json()
        if status.get('connected'):
            return True
        else:
            print("WhatsApp não está conectado.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar status da conexão: {e}")
        return False

# Função para verificar se está no horário de silêncio
def horario_silencio():
    agora = datetime.now().hour
    if HORARIO_SILENCIO_INICIO <= agora or agora < HORARIO_SILENCIO_FIM:
        return True
    return False

# Função para enviar mensagens ao WhatsApp
def enviar_mensagem(grupo_id, mensagem):
    if horario_silencio():
        print("Horário de silêncio. Mensagem não enviada.")
        return

    url = f"{ZAPI_BASE_URL}/send-message"
    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "to": grupo_id,
        "message": mensagem
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Mensagem enviada para o grupo {grupo_id}: {mensagem}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")

# Rota para forçar envio de mensagem (para teste)
@app.route('/enviar', methods=['POST'])
def forcar_envio():
    grupo_id = GRUPOS_WHATSAPP[0]  # Apenas para exemplo
    mensagem = "Esta é uma mensagem de teste enviada manualmente."
    enviar_mensagem(grupo_id, mensagem)
    return jsonify({"status": "Mensagem enviada", "grupo": grupo_id, "mensagem": mensagem}), 200

# Função principal para iniciar o servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
