from cryptography.fernet import Fernet

with open('chave.key', 'rb') as key_file:
    key = key_file.read()

fernet = Fernet(key)

with open('db_config.json', 'rb') as f:
    dados = f.read()

dados_criptografados = fernet.encrypt(dados)

with open('db_config.json.enc', 'wb') as f:
    f.write(dados_criptografados)

print("Configuração criptografada com sucesso.")

