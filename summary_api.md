# Resumo Técnico da API Control iD

Este documento resume as principais características da API de acesso da Control iD, com foco nos recursos necessários ao MVP de integração.

## Autenticação e sessão

- **Login** (`POST /login.fcgi`): recebe `login` e `password` e retorna um token de sessão. Este token deve ser anexado como parâmetro de query (`?session=...`) em todas as requisições subsequentes【72953200591702†L139-L174】.  
- **Sessão válida** (`POST /session_is_valid.fcgi`): verifica se a sessão está ativa; retorna `{"session_is_valid": true}`【897149201966306†L139-L163】.  
- **Logout** (`POST /logout.fcgi`): encerra a sessão atual; não retorna corpo【49523207638765†L136-L156】.  

Recomenda-se reutilizar a mesma sessão ao máximo e desabilitar o header HTTP `Expect: 100-continue` conforme destacado na documentação【57880008018721†L163-L176】【57880008018721†L202-L205】.

## Objetos e CRUD

A API expõe uma estrutura de “objetos”, semelhantes a tabelas de banco de dados. Os principais métodos são:

- **Criar objetos** (`POST /create_objects.fcgi`): parâmetros `object` (tipo) e `values` (lista de registros)【776292371146098†L146-L175】; retorna `ids` gerados.  
- **Modificar objetos** (`POST /modify_objects.fcgi`): parâmetros `object`, `values` (campos), `where` (filtro)【579828952357670†L139-L175】; retorna número de registros modificados.  
- **Carregar objetos** (`POST /load_objects.fcgi`): parâmetros `object`, `fields`, `limit`, `offset`, `where`【822935365942615†L146-L176】; retorna lista de objetos.  
- **Destruir objetos** (`POST /destroy_objects.fcgi`): remove registros com base no `where`.

### Principais tipos de objetos

- **users**: usuários; campos importantes incluem `id` (gerado), `registration`, `name`, `password`/`salt`, `begin_time`/`end_time`【498153051113835†L180-L210】.  
- **groups**: grupos de acesso (`id`, `name`)【498153051113835†L350-L359】.  
- **user_groups**: ligação usuário–grupo (`user_id`, `group_id`)【498153051113835†L360-L367】.  
- **access_rules**: regras de acesso com campos `id`, `name`, `type` (0 = bloqueio, 1 = liberação), `priority`【498153051113835†L418-L435】.  
- **group_access_rules**: associa grupos às regras【498153051113835†L444-L450】.  
- **time_zones**, **time_spans** e **access_rule_time_zones**: definem janelas de tempo permitidas【498153051113835†L458-L491】.

## Reconhecimento facial (iDFace)

Os equipamentos da linha iDFace permitem upload e gerenciamento de fotos faciais para autenticação. Endpoints relevantes:

- **Cadastrar foto** (`POST /user_set_image.fcgi`): envia bytes da foto (JPEG) via `Content-Type: application/octet-stream`. Parâmetros na query: `user_id`, `timestamp` (milissegundos) e `match` (1 para verificar duplicidade)【483554058158489†L354-L406】.  
- **Cadastrar fotos em lote** (`POST /user_set_image_list.fcgi`): corpo JSON com `match` e `user_images` (cada item com `user_id`, `timestamp`, `image` em base64). Tamanho máximo total de 2 MB【483554058158489†L520-L548】.  
- **Listar usuários com fotos** (`GET /user_list_images.fcgi`): retorna IDs ou, se `get_timestamp=1`, lista com `id` e `timestamp`【483554058158489†L218-L259】.  
- **Obter fotos** (`POST /user_get_image_list.fcgi`): retorna até 100 fotos por chamada, cada uma com `id`, `timestamp` e `image` (base64)【483554058158489†L278-L352】.  
- **Remover fotos** (`POST /user_destroy_image.fcgi`): remove foto(s) de um ou mais usuários; aceita `user_id`, `user_ids`, `all` ou `dangling`【631453093151667†L267-L296】.

### Qualidade e restrições

As fotos devem ter tamanho máximo de 2 MB e estar em formato JPEG【483554058158489†L354-L360】. A API aplica algoritmos de verificação que retornam métricas (largura do rosto, offsets, pose, nitidez). Se os valores não atenderem aos critérios (ex.: largura entre 60–800 px, nitidez ≥ 450) a foto é rejeitada【483554058158489†L417-L475】. O parâmetro `match=1` instrui o equipamento a verificar se o rosto já existe para evitar duplicidades.

## Fluxo recomendado para cadastro

O cadastro no modo stand‑alone segue a sequência: 1) criar usuários, 2) criar grupos, 3) vincular usuários aos grupos, 4) criar regras de acesso, 5) associar grupos às regras, 6) criar zonas de tempo, 7) criar intervalos de tempo e 8) associar regras às zonas【874569193093321†L149-L184】. Para exceções (regras específicas por usuário), usar `user_access_rules`【874569193093321†L188-L200】.

No modo online, o equipamento consulta o servidor para autorizar cada acesso; assim, etapas 4 a 8 podem ser implementadas no servidor em vez de localmente.