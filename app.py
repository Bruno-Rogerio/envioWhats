from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME')

# Conexão MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
mensagens_enviadas_collection = db.mensagens_enviadas

def limpar_mensagens_enviadas():
    resultado = mensagens_enviadas_collection.delete_many({})
    print(f"Foram removidos {resultado.deleted_count} documentos da coleção 'mensagens_enviadas'.")

if __name__ == "__main__":
    confirmacao = input("Você tem certeza que deseja limpar a coleção 'mensagens_enviadas'? (s/n): ")
    if confirmacao.lower() == 's':
        limpar_mensagens_enviadas()
        print("A coleção foi limpa com sucesso.")
    else:
        print("Operação cancelada.")

    # Fecha a conexão com o MongoDB
    client.close()
