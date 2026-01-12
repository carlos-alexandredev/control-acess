"""
controlid_client.py
====================

Uma biblioteca cliente em Python para integrar sistemas web com a API de
controle de acesso da Control iD. O cliente encapsula as operações de
sessão, CRUD de usuários e grupos e manipulação de fotos faciais
necessárias para o MVP descrito na documentação de integração.

Características principais:

* Gerenciamento automático da sessão: login na inicialização e renovação
  da sessão quando necessário.
* Desabilitação do cabeçalho `Expect: 100-continue` para conformidade
  com a API Control iD.
* Métodos convenientes para criar, atualizar e excluir usuários,
  associar grupos e regras e cadastrar fotos faciais.

Este módulo depende do pacote `requests`. Para instalar:

    pip install requests

Exemplo de uso::

    from controlid_system.client.controlid_client import ControlIDClient

    client = ControlIDClient(base_url="http://192.168.0.10", login="admin", password="admin")
    user_id = client.create_user(registration="1234", name="Fulano de Tal")
    client.set_user_image(user_id, "/caminho/para/foto.jpg")

"""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Dict, Iterable, List, Optional

import requests


class ControlIDError(Exception):
    """Exceção base para erros retornados pela API Control iD."""


class ControlIDClient:
    """Cliente da API Control iD.

    :param base_url: URL base do equipamento, por exemplo "http://192.168.0.10".
    :param login: Usuário para autenticação.
    :param password: Senha para autenticação.
    :param timeout: Timeout padrão (segundos) para requisições HTTP.
    :param auto_login: Se verdadeiro, efetua login durante a inicialização.
    """

    def __init__(
        self,
        base_url: str,
        login: str,
        password: str,
        *,
        timeout: int = 10,
        auto_login: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.login = login
        self.password = password
        self.timeout = timeout
        # Usa requests.Session para reutilizar conexões e desabilitar Expect: 100-continue
        self._session_http = requests.Session()
        # Remove header Expect se existir
        self._session_http.headers['Expect'] = ''
        self._session_id: Optional[str] = None
        if auto_login:
            self.login_session()

    # ------------------------------------------------------------------
    # Sessão
    def login_session(self) -> str:
        """Efetua login no equipamento.

        :returns: string da sessão
        :raises ControlIDError: se a autenticação falhar
        """
        url = f"{self.base_url}/login.fcgi"
        payload = {"login": self.login, "password": self.password}
        try:
            resp = self._session_http.post(url, json=payload, timeout=self.timeout)
        except Exception as exc:
            raise ControlIDError(f"Erro ao conectar ao equipamento: {exc}")
        if resp.status_code != 200:
            raise ControlIDError(f"Erro HTTP ao efetuar login: {resp.status_code} - {resp.text}")
        data = resp.json()
        session = data.get("session")
        if not session:
            raise ControlIDError(f"Resposta inesperada ao efetuar login: {data}")
        self._session_id = session
        return session

    def session_is_valid(self) -> bool:
        """Verifica se a sessão corrente é válida.

        :returns: True se a sessão estiver válida
        :raises ControlIDError: se a verificação falhar
        """
        if not self._session_id:
            return False
        url = f"{self.base_url}/session_is_valid.fcgi?session={self._session_id}"
        try:
            resp = self._session_http.post(url, timeout=self.timeout)
        except Exception as exc:
            raise ControlIDError(f"Erro ao checar sessão: {exc}")
        if resp.status_code != 200:
            raise ControlIDError(f"Erro HTTP ao checar sessão: {resp.status_code} - {resp.text}")
        data = resp.json()
        return bool(data.get("session_is_valid"))

    def ensure_session(self) -> None:
        """Garante que existe uma sessão válida, realizando login se necessário."""
        if not self._session_id or not self.session_is_valid():
            self.login_session()

    def logout(self) -> None:
        """Encerra a sessão atual (opcional)."""
        if not self._session_id:
            return
        url = f"{self.base_url}/logout.fcgi?session={self._session_id}"
        try:
            self._session_http.post(url, timeout=self.timeout)
        finally:
            self._session_id = None

    # ------------------------------------------------------------------
    # Operações genéricas
    def _post_json(self, endpoint: str, payload: Dict[str, Any]) -> Any:
        """Envia um POST JSON ao endpoint especificado com o payload dado.

        O método já adiciona o parâmetro de sessão na query‑string.

        :param endpoint: Caminho do endpoint (por exemplo, "/create_objects.fcgi").
        :param payload: Dicionário com o corpo da requisição.
        :returns: Dados retornados pela API (normalmente um dicionário).
        :raises ControlIDError: se a requisição falhar.
        """
        self.ensure_session()
        url = f"{self.base_url}{endpoint}?session={self._session_id}"
        try:
            resp = self._session_http.post(url, json=payload, timeout=self.timeout)
        except Exception as exc:
            raise ControlIDError(f"Erro ao chamar {endpoint}: {exc}")
        if resp.status_code != 200:
            raise ControlIDError(f"Erro HTTP ao chamar {endpoint}: {resp.status_code} - {resp.text}")
        # algumas respostas retornam texto em vez de JSON válido
        try:
            return resp.json()
        except json.JSONDecodeError:
            return resp.text

    # ------------------------------------------------------------------
    # CRUD de objetos
    def create_objects(self, object_type: str, values: Iterable[Dict[str, Any]]) -> List[int]:
        """Cria objetos do tipo especificado.

        :param object_type: Nome do objeto (ex.: "users", "groups").
        :param values: Iterable de dicionários com os campos a serem criados.
        :returns: Lista de IDs gerados.
        """
        payload = {"object": object_type, "values": list(values)}
        data = self._post_json("/create_objects.fcgi", payload)
        # a API retorna normalmente {'ids': [1, 2, 3]}
        ids = data.get("ids")
        return ids if ids is not None else []

    def modify_objects(self, object_type: str, values: Dict[str, Any], where: Dict[str, Any]) -> int:
        """Modifica objetos do tipo especificado.

        :param object_type: Tipo de objeto (ex.: "users").
        :param values: Campos a serem atualizados.
        :param where: Filtro (ex.: {"id": 1}).
        :returns: Número de registros alterados.
        """
        payload = {"object": object_type, "values": values, "where": {object_type: where}}
        data = self._post_json("/modify_objects.fcgi", payload)
        return int(data.get("modified", 0))

    def destroy_objects(self, object_type: str, where: Dict[str, Any]) -> int:
        """Exclui objetos com base em um filtro.

        :param object_type: Tipo do objeto.
        :param where: Condição de remoção.
        :returns: Número de registros removidos.
        """
        payload = {"object": object_type, "where": {object_type: where}}
        data = self._post_json("/destroy_objects.fcgi", payload)
        return int(data.get("destroyed", 0))

    def load_objects(
        self,
        object_type: str,
        *,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Carrega objetos de um tipo específico com filtros opcionais.

        :param object_type: Tipo do objeto a carregar.
        :param fields: Lista de campos a retornar.
        :param limit: Quantidade máxima de itens.
        :param offset: Posição inicial.
        :param where: Filtro de consulta.
        :returns: Lista de objetos.
        """
        payload: Dict[str, Any] = {"object": object_type}
        if fields:
            payload["fields"] = fields
        if limit is not None:
            payload["limit"] = limit
        if offset is not None:
            payload["offset"] = offset
        if where:
            payload["where"] = {object_type: where}
        data = self._post_json("/load_objects.fcgi", payload)
        return data.get("objects", [])  # returns list of dicts

    # ------------------------------------------------------------------
    # Métodos de alto nível (usuários)
    def create_user(self, registration: str, name: str, **extra_fields: Any) -> int:
        """Cria um usuário no equipamento.

        :param registration: Código/registro do usuário (chave natural).
        :param name: Nome do usuário.
        :param extra_fields: Demais campos opcionais (ex.: password_hash, salt, user_type_id, begin_time, end_time).
        :returns: ID do usuário criado.
        """
        values = {
            "registration": registration,
            "name": name,
        }
        values.update(extra_fields)
        ids = self.create_objects("users", [values])
        if not ids:
            raise ControlIDError("Falha ao criar usuário: nenhum ID retornado")
        return ids[0]

    def update_user(self, user_id: int, **fields: Any) -> None:
        """Atualiza campos de um usuário existente.

        :param user_id: ID interno do usuário no dispositivo.
        :param fields: Campos a atualizar.
        """
        modified = self.modify_objects("users", fields, {"id": user_id})
        if modified == 0:
            raise ControlIDError(f"Nenhum usuário modificado ao atualizar ID {user_id}")

    def delete_user(self, user_id: int) -> None:
        """Remove um usuário pelo ID.
        :param user_id: ID interno do usuário.
        """
        removed = self.destroy_objects("users", {"id": user_id})
        if removed == 0:
            raise ControlIDError(f"Nenhum usuário removido ao excluir ID {user_id}")

    def list_users(self, **filters: Any) -> List[Dict[str, Any]]:
        """Lista usuários com filtros opcionais.

        :param filters: Dicionário de filtros (ex.: id, registration, name).
        :returns: Lista de objetos de usuários.
        """
        return self.load_objects("users", where=filters)

    # ------------------------------------------------------------------
    # Operações de imagem facial
    def set_user_image(
        self,
        user_id: int,
        image: Any,
        *,
        timestamp: Optional[int] = None,
        match: bool = True,
    ) -> Dict[str, Any]:
        """Envia uma foto facial para um usuário.

        :param user_id: ID do usuário.
        :param image: Caminho para o arquivo de imagem ou bytes da imagem JPEG.
        :param timestamp: Unix timestamp em milissegundos; se None, usa agora.
        :param match: Verdadeiro para detectar duplicidade de rosto.
        :returns: Objeto JSON retornado pelo equipamento, contendo scores ou erros.
        """
        self.ensure_session()
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        match_param = 1 if match else 0
        url = (
            f"{self.base_url}/user_set_image.fcgi"
            f"?session={self._session_id}&user_id={user_id}&timestamp={timestamp}&match={match_param}"
        )
        # abrir arquivo se for caminho
        if isinstance(image, str):
            with open(image, "rb") as fh:
                data = fh.read()
        else:
            data = bytes(image)
        try:
            resp = self._session_http.post(
                url,
                data=data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=self.timeout,
            )
        except Exception as exc:
            raise ControlIDError(f"Erro ao enviar imagem: {exc}")
        if resp.status_code != 200:
            raise ControlIDError(f"Erro HTTP ao enviar imagem: {resp.status_code} - {resp.text}")
        # a resposta pode ser JSON ou plain text
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"response": resp.text}

    def set_user_image_list(
        self,
        user_images: Iterable[Dict[str, Any]],
        *,
        match: bool = True,
    ) -> Dict[str, Any]:
        """Envia uma lista de fotos faciais para vários usuários.

        :param user_images: Iterable de dicts com chaves `user_id`, `timestamp` (opcional) e `image` (bytes ou base64).
        :param match: Se verdadeiro, ativa verificação de duplicidade.
        :returns: JSON com resultados por usuário.
        """
        self.ensure_session()
        images_payload = []
        for item in user_images:
            uid = item["user_id"]
            ts = item.get("timestamp", int(time.time() * 1000))
            img = item["image"]
            if isinstance(img, bytes):
                img_base64 = base64.b64encode(img).decode()
            elif isinstance(img, str):
                if os.path.isfile(img):
                    with open(img, "rb") as fh:
                        img_base64 = base64.b64encode(fh.read()).decode()
                else:
                    # assume string já em base64
                    img_base64 = img
            else:
                raise ValueError("Campo image deve ser bytes, caminho ou string base64")
            images_payload.append({"user_id": uid, "timestamp": ts, "image": img_base64})
        payload = {
            "match": 1 if match else 0,
            "user_images": images_payload,
        }
        data = self._post_json("/user_set_image_list.fcgi", payload)
        return data

    def list_user_images(self, *, get_timestamp: bool = False) -> List[Any]:
        """Lista usuários que possuem imagens cadastradas.

        :param get_timestamp: Se verdadeiro, retorna objetos com user_id e timestamp.
        :returns: Lista de IDs ou de objetos {"id": ..., "timestamp": ...}.
        """
        self.ensure_session()
        get_ts = 1 if get_timestamp else 0
        url = (
            f"{self.base_url}/user_list_images.fcgi"
            f"?session={self._session_id}&get_timestamp={get_ts}"
        )
        resp = self._session_http.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            raise ControlIDError(f"Erro ao listar imagens: {resp.status_code} - {resp.text}")
        return resp.json().get("user_ids", [])

    def get_user_image_list(self, user_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Obtém imagens (base64) de usuários.

        :param user_ids: Lista de IDs; se None, solicita imagens de todos os usuários com imagem.
        :returns: Lista de dicts com keys `id`, `timestamp` e `image` (base64).
        """
        self.ensure_session()
        payload: Dict[str, Any] = {}
        if user_ids:
            payload["user_ids"] = user_ids
        data = self._post_json("/user_get_image_list.fcgi", payload)
        return data.get("user_images", [])

    def delete_user_image(self, user_id: Optional[int] = None, user_ids: Optional[List[int]] = None, all_images: bool = False) -> None:
        """Remove imagens faciais de usuários.

        :param user_id: Remove imagem de um único usuário.
        :param user_ids: Remove imagens de vários usuários.
        :param all_images: Se verdadeiro, remove todas as imagens (use com cautela).
        """
        self.ensure_session()
        payload: Dict[str, Any] = {}
        if all_images:
            payload["all"] = True
        elif user_id is not None:
            payload["user_id"] = user_id
        elif user_ids is not None:
            payload["user_ids"] = user_ids
        else:
            raise ValueError("Informe user_id, user_ids ou all_images=True")
        # A documentação diz que este endpoint não retorna corpo
        self._post_json("/user_destroy_image.fcgi", payload)
