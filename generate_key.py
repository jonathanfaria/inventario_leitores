from cryptography.fernet import Fernet

key = Fernet.generate_key()
with open('chave.key', 'wb') as file:
    file.write(key)

print(f"Chave gerada e salva como chave.key")

