# Sistema de Integração Control iD

Este repositório contém uma implementação de referência para integrar um sistema
web à API de controle de acesso da Control iD (linha Acesso / iDFace). O
projeto inclui:

- **Cliente Python (`controlid_client.py`)**: biblioteca que encapsula as
  operações de autenticação, CRUD de usuários/grupos, envio de fotos e
  outras chamadas necessárias.
- **Documentação**: resumo da API, documento de arquitetura e checklist de
  go‑live em `docs/`.
- **Testes automatizados**: conjunto de testes unitários em `tests/`
  utilizando mocks para simular o equipamento.
- **Coleção Postman**: exemplo de requisiões agrupadas para testar o
  equipamento manualmente (`postman/controlid_collection.json`).

## Estrutura

```
controlid_system/
├── client/
│   ├── __init__.py
│   └── controlid_client.py     # implementação principal
├── docs/
│   ├── summary_api.md          # resumo dos endpoints e objetos
│   ├── architecture.md         # documento de arquitetura com diagramas mermaid
│   └── go_live_checklist.md    # lista de verificação para entrada em produção
├── tests/
│   └── test_client.py          # testes unitários utilizando unittest
├── postman/
│   └── controlid_collection.json
└── README.md                   # este arquivo
```

## Instalação

Requer Python ≥ 3.8 e o pacote `requests`. Para instalar em ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate
pip install requests
```

## Uso básico

```python
from controlid_system.client import ControlIDClient

# Endereço do equipamento e credenciais (geralmente admin/admin na fábrica)
client = ControlIDClient(base_url="http://192.168.0.10", login="admin", password="admin")

# Criar um usuário
user_id = client.create_user(registration="1234", name="Fulano de Tal")

# Atualizar o nome
client.update_user(user_id, name="Fulano de Souza")

# Enviar foto
client.set_user_image(user_id, "/caminho/para/foto.jpg")

# Listar usuários que possuem fotos
print(client.list_user_images())

# Excluir usuário
client.delete_user(user_id)
```

## Testes

Execute os testes unitários com:

```bash
cd controlid_system
python -m unittest discover tests
```

## Coleção Postman

A coleção `postman/controlid_collection.json` pode ser importada no Postman ou
Insomnia. Defina as variáveis de ambiente `base_url`, `login`, `password` e
`session` (este último será preenchido manualmente após o login) para testar
os principais endpoints.

## Próximos passos

Este projeto oferece uma base para o MVP. Extensões futuras incluem:

- Suporte a captura de eventos de acesso via monitor/push.
- Interfaces CLI/GUI para administração.
- Empacotamento como serviço Docker.
