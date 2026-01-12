# Checklist de Go‑Live para Integração Control iD

Esta lista de verificação deve ser seguida antes e durante a entrada em produção da integração com equipamentos Control iD.

## Pré‑requisitos no equipamento

- Firmware atualizado compatível com a API de acesso.
- Configuração de rede (IP fixo ou DHCP reservado) com conectividade estável ao servidor.
- Usuário e senha de administrador definidos; credenciais armazenadas de forma segura (ex.: vault).
- Verificar se o modo de operação está conforme a necessidade:
  - **Stand‑alone**: equipamento decide acesso localmente conforme regras.
  - **Online**: equipamento envia eventos de identificação para o servidor; regras de acesso são aplicadas pelo servidor.
- Ajustar fuso horário (timezone) do equipamento para garantir consistência de timestamps.

## Configuração de rede e segurança

- Liberação das portas HTTP/HTTPS (padrão 80/443) entre servidor e equipamentos.
- Se houver VPN ou NAT, configurar regras de encaminhamento e certificação de latência aceitável.
- Certificados SSL se a comunicação for via HTTPS; considerar certificados autoassinados apenas em ambientes internos.
- Desabilitar o header `Expect: 100‑continue` no cliente (conforme requerido pela documentação【57880008018721†L202-L205】).

## Credenciais e rotação

- Armazenar `login` e `password` do equipamento em cofre de segredos.
- Implementar política de rotação periódica de senhas (ex.: a cada 90 dias).
- Garantir que mudanças de credenciais sejam propagadas para todos os serviços que utilizam o `ControlIDClient`.

## Sincronização inicial

- Carregar usuários existentes do equipamento com `load_objects(users)` para preencher a tabela `device_user_map`.
- Reconciliar divergências: excluir usuários obsoletos no equipamento (se não existirem no banco) e criar usuários ausentes.
- Realizar carga inicial de fotos com `user_set_image_list.fcgi` em lotes de até 2 MB【483554058158489†L520-L548】.

## Testes finais

- **Sessão expirada**: validar que o sistema renova a sessão ao receber resposta negativa de `session_is_valid`.
- **Usuário inexistente**: testar a criação e atualização de usuário não cadastrado; esperar erro significativo.
- **Foto inválida**: usar imagens corrompidas ou com rosto fora dos critérios; confirmar recebimento de código de erro apropriado【483554058158489†L417-L475】.
- **Duplicidade de rosto**: com `match=1`, enviar foto de um usuário diferente; o equipamento deve rejeitar com erro 39 (“Face already exists”).
- **Limites**: enviar batch de imagens com mais de 100 registros ou tamanho total > 2 MB e verificar manejo de erro.
- **Falha de rede**: simular interrupção na comunicação e confirmar que o serviço realiza retry com backoff.

## Rollback e contingência

- Manter backups das configurações originais dos equipamentos (export via Web UI ou API).
- Caso a integração apresente falhas graves, desligar o modo online e retornar ao stand‑alone, garantindo que regras locais estejam atualizadas.
- Documentar procedimentos para restaurar a versão anterior do software e das dependências.