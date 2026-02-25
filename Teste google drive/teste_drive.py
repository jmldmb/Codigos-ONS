from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd

# 1. Autenticar com sua conta Google
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# 2. Criar base de exemplo
df = pd.DataFrame({
    "usina": ["Usina A", "Usina B"],
    "potencia": [150.0, 220.5],
    "cvu": [320.4, 285.0],
})
csv_file = "base_master.csv"
df.to_csv(csv_file, index=False)

# 3. ID da pasta no Google Drive
folder_id = "1sOrNy-xtIdZLJ7gOsnv7DeahV5xItJu8"

# 4. Upload para a pasta desejada
arquivo = drive.CreateFile({
    'title': csv_file,
    'parents': [{'id': folder_id}]
})
arquivo.SetContentFile(csv_file)
arquivo.Upload()

# 5. Mostrar link público (não necessariamente acessível sem login)
print("✅ Arquivo enviado com sucesso para a pasta desejada!")
print(f"🔗 Link para o arquivo: https://drive.google.com/file/d/{arquivo['id']}/view?usp=sharing")
