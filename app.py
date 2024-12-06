import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import requests
import time
from dotenv import load_dotenv
import locale

# Configura o locale para o padrão brasileiro
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

load_dotenv()

# Configurações
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME')
ZAPI_INSTANCE = os.getenv('ZAPI_INSTANCE')
ZAPI_TOKEN = os.getenv('ZAPI_TOKEN')
CLIENT_TOKEN = os.getenv('CLIENT_TOKEN')
ZAPI_BASE_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}"
GRUPOS_WHATSAPP = ["120363356072490260-group"]  # Substitua pelos seus IDs de grupo

# Configurações de horário
HORARIO_SILENCIO_INICIO = 22  # 22:00
HORARIO_SILENCIO_FIM = 8  # 08:00

# Conexão MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
produtos_collection = db.produtos
mensagens_enviadas_collection = db.mensagens_enviadas
engajamento_collection = db.engajamento

ultimo_envio = None

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
            print("Conexão com WhatsApp estabelecida.")
            return True
        else:
            print("WhatsApp não está conectado. Por favor, verifique sua instância Z-API.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar status da conexão: {e}")
        return False

def esta_no_horario_silencio():
    agora = datetime.now().hour
    return HORARIO_SILENCIO_INICIO <= agora or agora < HORARIO_SILENCIO_FIM

def enviar_mensagem_whatsapp(produto, grupo_id):
    url = f"{ZAPI_BASE_URL}/send-link"
    headers = {
        "Client-Token": CLIENT_TOKEN,
        "Content-Type": "application/json"
    }
    mensagem = formatar_mensagem(produto)
    payload = {
        "phone": grupo_id,
        "message": mensagem,
        "image": produto.get('imagem_url', ''),  # URL da imagem do produto
        "linkUrl": produto['link_afiliado'],
        "title": produto['nome'],  # Título do link
        "description": f"De R$ {locale.currency(produto['precoAntigo'], grouping=True, symbol=None)} por R$ {locale.currency(produto['preco'], grouping=True, symbol=None)}"  # Descrição do link
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        resultado = response.json()
        if resultado.get("zaapId") or resultado.get("messageId"):
            print(f"Mensagem enviada com sucesso! ZaapID: {resultado.get('zaapId', 'N/A')}")
            return resultado
        else:
            print("Não foi possível confirmar o envio da mensagem.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para o grupo {grupo_id}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Resposta do servidor: {e.response.text}")
        return None

def formatar_mensagem(produto):
    preco_antigo = locale.currency(produto['precoAntigo'], grouping=True, symbol=None)
    preco_atual = locale.currency(produto['preco'], grouping=True, symbol=None)
    economia = locale.currency(produto['precoAntigo'] - produto['preco'], grouping=True, symbol=None)

    mensagem = f"""🔥 *OFERTA IMPERDÍVEL!*

*{produto['nome']}*
💰 De: R$ {preco_antigo}
💥 Por apenas: R$ {preco_atual}

Economize R$ {economia}!

🛒 Compre agora pelo link abaixo
"""
    
    return mensagem

def registrar_engajamento(produto_id, grupo_id, tipo_engajamento):
    engajamento_collection.insert_one({
        "produto_id": produto_id,
        "grupo_id": grupo_id,
        "tipo": tipo_engajamento,
        "data": datetime.now(timezone.utc)
    })

def verificar_e_enviar_produto():
    global ultimo_envio
    
    if esta_no_horario_silencio():
        print("Horário de silêncio. Nenhuma mensagem será enviada.")
        return

    if ultimo_envio and datetime.now() - ultimo_envio < timedelta(minutes=10):
        return

    try:
        produto = produtos_collection.find_one({
            "_id": {
                "$nin": [
                    msg["produto_id"] 
                    for msg in mensagens_enviadas_collection.find({}, {"produto_id": 1})
                ]
            },
            "ativo": True
        })

        if produto:
            print(f"Processando produto: {produto['nome']}")

            for grupo_id in GRUPOS_WHATSAPP:
                resultado = enviar_mensagem_whatsapp(produto, grupo_id)
                
                if resultado and (resultado.get("zaapId") or resultado.get("messageId")):
                    mensagens_enviadas_collection.insert_one({
                        "produto_id": produto["_id"],
                        "grupo_id": grupo_id,
                        "data_envio": datetime.now(timezone.utc),
                        "sucesso": True,
                        "zaapId": resultado.get("zaapId"),
                        "messageId": resultado.get("messageId")
                    })
                    print(f"Mensagem enviada com sucesso para o grupo {grupo_id}")
                    
                    registrar_engajamento(produto["_id"], grupo_id, "envio")
                else:
                    print(f"Falha ao enviar mensagem para o grupo {grupo_id}")
                
                time.sleep(5)  # Espera 5 segundos entre envios para diferentes grupos

            ultimo_envio = datetime.now()
            print(f"Próximo envio será após {ultimo_envio + timedelta(minutes=10)}")
        else:
            print("Nenhum novo produto para enviar.")

    except Exception as e:
        print(f"Erro ao processar produtos: {str(e)}")

def main():
    print("Iniciando monitoramento de novos produtos...")
    
    if not verificar_conexao():
        print("Encerrando o script devido a problemas de conexão.")
        return
    
    while True:
        try:
            verificar_e_enviar_produto()
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nEncerrando o monitoramento...")
            break
        except Exception as e:
            print(f"Erro no loop principal: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
