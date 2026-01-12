# Backend – Control iD Integration API

Este diretório contém um servidor simples em Python usando Flask que
exponibiliza as principais operações da biblioteca cliente `controlid_system`
via uma API REST. Ele serve como exemplo de como integrar a Control iD com
um sistema web backend e pode ser usado como base para o desenvolvimento
de sua própria API.

## Requisitos

* Python 3.11 ou superior.
* Instalar as dependências:

```bash
pip install flask requests
```

Para desenvolver com a biblioteca local `controlid_system`, certifique‑se de
que o diretório `controlid_system` esteja no `PYTHONPATH` ou instale‑o via
`pip install -e .` na raiz do repositório.

## Configuração

Defina as seguintes variáveis de ambiente conforme seu equipamento:

* `CONTROLID_BASE_URL`: URL do equipamento Control iD (ex.: `http://192.168.0.10`).
* `CONTROLID_LOGIN` e `CONTROLID_PASSWORD`: credenciais de acesso.
* (Opcional) `HOST` e `PORT`: endereço e porta em que o servidor Flask irá escutar (padrão `0.0.0.0:5000`).

## Uso

Execute o servidor com:

```bash
python backend/app.py
```

Ele iniciará em `http://localhost:5000/`. Principais endpoints:

* `POST /api/users` – cria usuário. Corpo JSON: `{ "registration": "...", "name": "..." }`.
* `PUT /api/users/{registration}` – atualiza usuário. Corpo JSON com campos a alterar.
* `DELETE /api/users/{registration}` – remove usuário.
* `POST /api/users/{registration}/image` – envia foto. Envie arquivo no campo `file` (multipart/form-data).
* `GET /api/users` – lista mapeamento de usuários locais → IDs no dispositivo.

## Observações

Este servidor utiliza um dicionário em memória (`user_map`) para mapear
registros locais aos IDs gerados pelo equipamento. Em um ambiente real,
substitua essa estrutura por um banco de dados persistente.

O backend não implementa autenticação própria; considere adicionar camadas
de segurança (tokens JWT, sessões, etc.) conforme a necessidade do seu projeto.
