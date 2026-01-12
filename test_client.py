"""
Testes unitários para o ControlIDClient.

Como não temos acesso a um equipamento real durante os testes, utilizamos
``unittest.mock`` para simular respostas da API. Esses testes validam o
funcionamento dos métodos de alto nível e o gerenciamento de sessões.
"""

import os
import io
import json
import unittest
from unittest.mock import MagicMock, patch

# Ajusta sys.path para permitir importação do pacote local quando os testes são
# executados a partir do diretório controlid_system. Sem esse ajuste,
# 'controlid_system' pode não ser encontrado pelo import.
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from controlid_system.client.controlid_client import ControlIDClient, ControlIDError


class TestControlIDClient(unittest.TestCase):
    def setUp(self) -> None:
        # Configuração básica para o cliente; base_url é fictício
        self.base_url = "http://device.test"
        self.login = "admin"
        self.password = "admin"

    @patch("requests.Session.post")
    def test_login_session_success(self, mock_post: MagicMock) -> None:
        # Simula retorno da API de login
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"session": "abc123"}
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        session = client.login_session()
        self.assertEqual(session, "abc123")
        self.assertEqual(client._session_id, "abc123")
        # Verifica se a chamada foi feita com JSON correto
        mock_post.assert_called_with(
            f"{self.base_url}/login.fcgi",
            json={"login": self.login, "password": self.password},
            timeout=client.timeout,
        )

    @patch("requests.Session.post")
    def test_login_session_error(self, mock_post: MagicMock) -> None:
        # Simula erro HTTP
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        with self.assertRaises(ControlIDError):
            client.login_session()

    @patch("requests.Session.post")
    def test_create_user(self, mock_post: MagicMock) -> None:
        # Simula login e criação de usuário
        def side_effect(url, json=None, timeout=None, **kwargs):
            # Respostas para login
            if url.endswith("/login.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session": "sess1"}
                return resp
            # Verificação de sessão válida
            if url.endswith("/session_is_valid.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session_is_valid": True}
                return resp
            # Criação de usuário
            if url.endswith("/create_objects.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"ids": [99]}
                return resp
            raise AssertionError(f"Unexpected URL called: {url}")
        mock_post.side_effect = side_effect
        # auto_login=False pois vamos lidar com login na primeira chamada
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        # Força login antes de criar usuário para simplificar side_effect
        client.login_session()
        user_id = client.create_user("1234", "Test User")
        self.assertEqual(user_id, 99)

    @patch("requests.Session.post")
    def test_update_user(self, mock_post: MagicMock) -> None:
        # Simula login e modificação
        def side_effect(url, json=None, timeout=None, **kwargs):
            if url.endswith("/login.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session": "sess1"}
                return resp
            if url.endswith("/session_is_valid.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session_is_valid": True}
                return resp
            if url.endswith("/modify_objects.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"modified": 1}
                return resp
            raise AssertionError(f"Unexpected URL called: {url}")
        mock_post.side_effect = side_effect
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        client.login_session()
        # chamada não deve lançar exceção
        client.update_user(99, name="Novo Nome")

    @patch("requests.Session.post")
    def test_delete_user(self, mock_post: MagicMock) -> None:
        # Simula login e remoção
        def side_effect(url, json=None, timeout=None, **kwargs):
            if url.endswith("/login.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session": "sess1"}
                return resp
            if url.endswith("/session_is_valid.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session_is_valid": True}
                return resp
            if url.endswith("/destroy_objects.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"destroyed": 1}
                return resp
            raise AssertionError(f"Unexpected URL called: {url}")
        mock_post.side_effect = side_effect
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        client.login_session()
        client.delete_user(99)

    @patch("requests.Session.post")
    @patch("requests.Session.get")
    def test_set_user_image_and_list_images(self, mock_get: MagicMock, mock_post: MagicMock) -> None:
        # Simula login e upload de imagem, seguida de listagem
        def post_side_effect(url, data=None, headers=None, json=None, timeout=None, **kwargs):
            if url.endswith("/login.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session": "sess1"}
                return resp
            if url.endswith("/session_is_valid.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"session_is_valid": True}
                return resp
            if url.startswith(f"{self.base_url}/user_set_image.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"scores": {"sharpness": 500}}
                return resp
            if url.startswith(f"{self.base_url}/user_set_image_list.fcgi"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"result": [{"id": 1, "success": True}]}
                return resp
            if url.endswith("/create_objects.fcgi?session=sess1"):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"ids": [1]}
                return resp
            raise AssertionError(f"Unexpected POST called: {url}")
        mock_post.side_effect = post_side_effect
        # Simula listagem de imagens
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"user_ids": [1]}
        client = ControlIDClient(self.base_url, self.login, self.password, auto_login=False)
        client.login_session()
        fake_img_bytes = b"\xff\xd8\xff"
        result = client.set_user_image(1, fake_img_bytes)
        self.assertIn("scores", result)
        ids = client.list_user_images()
        self.assertEqual(ids, [1])


if __name__ == "__main__":
    unittest.main()