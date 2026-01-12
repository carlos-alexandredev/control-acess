"""Simple Flask backend to expose ControlID client operations via HTTP API.

This backend provides endpoints to create, update and delete users, and to
upload facial images.  It maintains a simple in‑memory mapping between
registrations (string IDs in your system) and the numeric IDs assigned by
the Control iD device.  Adjust the mapping store to a persistent database
as needed for your production environment.

Configuration is done via environment variables:

* ``CONTROLID_BASE_URL`` – base URL of the Control iD device (e.g. ``http://192.168.0.10``).
* ``CONTROLID_LOGIN`` – login username for the device.
* ``CONTROLID_PASSWORD`` – password for the device.

Run the server with ``python app.py``.  By default it listens on port 5000.

"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from flask import Flask, jsonify, request

from controlid_system.client.controlid_client import ControlIDClient, ControlIDError

# Initialise the Flask app
app = Flask(__name__)

# Create a single client instance; session will be reused automatically
client = ControlIDClient(
    base_url=os.getenv("CONTROLID_BASE_URL", "http://127.0.0.1"),
    login=os.getenv("CONTROLID_LOGIN", "admin"),
    password=os.getenv("CONTROLID_PASSWORD", "admin"),
)

# In‑memory mapping of registration (string) -> device user ID (int)
# Replace this with a database for persistent storage in production.
user_map: Dict[str, int] = {}


def lookup_user(registration: str) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
    """Helper to resolve a local registration to a device ID.

    Returns the device ID if known and an error response if not.
    """
    device_id = user_map.get(registration)
    if device_id is None:
        return None, {
            "error": f"Usuário com registro {registration!r} não encontrado no mapeamento local."
        }
    return device_id, None


@app.route("/api/users", methods=["POST"])
def create_user() -> Tuple[Dict[str, int] | Dict[str, str], int]:
    """Create a new user on the Control iD device.

    Expects JSON with at least ``registration`` and ``name`` fields.
    Additional fields are passed directly to the device (e.g. ``password``,
    ``user_type_id``).
    """
    data = request.get_json(silent=True) or {}
    registration = data.get("registration")
    name = data.get("name")
    if not registration or not name:
        return {
            "error": "Campos obrigatórios 'registration' e 'name' faltando."
        }, 400
    try:
        # Create user on the device and record mapping
        device_id = client.create_user(registration=registration, name=name, **{
            k: v for k, v in data.items()
            if k not in {"registration", "name"}
        })
        user_map[registration] = device_id
        return {
            "registration": registration,
            "device_user_id": device_id,
        }, 201
    except ControlIDError as exc:
        return {"error": str(exc)}, 400


@app.route("/api/users/<registration>", methods=["PUT"])
def update_user(registration: str) -> Tuple[Dict[str, str], int]:
    """Update an existing user.

    Accepts JSON with fields to update (e.g. ``name``, ``password``).
    """
    device_id, error = lookup_user(registration)
    if error:
        return error, 404
    data = request.get_json(silent=True) or {}
    if not data:
        return {"error": "Nenhum campo para atualizar fornecido."}, 400
    try:
        client.update_user(device_id, **data)
        return {"detail": "Usuário atualizado com sucesso."}, 200
    except ControlIDError as exc:
        return {"error": str(exc)}, 400


@app.route("/api/users/<registration>", methods=["DELETE"])
def delete_user(registration: str) -> Tuple[Dict[str, str], int]:
    """Delete a user locally and on the device."""
    device_id, error = lookup_user(registration)
    if error:
        return error, 404
    try:
        client.delete_user(device_id)
        # remove local mapping
        user_map.pop(registration, None)
        return {"detail": "Usuário removido com sucesso."}, 200
    except ControlIDError as exc:
        return {"error": str(exc)}, 400


@app.route("/api/users/<registration>/image", methods=["POST"])
def set_user_image(registration: str) -> Tuple[Dict[str, str], int]:
    """Upload a facial image for the user.

    Expects a multipart/form-data request with a file field called ``file``.
    """
    device_id, error = lookup_user(registration)
    if error:
        return error, 404
    file = request.files.get("file")
    if not file:
        return {"error": "Arquivo de imagem não enviado. Use campo 'file'."}, 400
    data = file.read()
    if not data:
        return {"error": "Conteúdo do arquivo vazio."}, 400
    try:
        client.set_user_image(device_id, data)
        return {"detail": "Imagem enviada com sucesso."}, 200
    except ControlIDError as exc:
        return {"error": str(exc)}, 400


@app.route("/api/users", methods=["GET"])
def list_users() -> Tuple[Dict[str, int], int]:
    """List local users and their corresponding device IDs."""
    return {"users": user_map}, 200


if __name__ == "__main__":
    # Use environment variable HOST and PORT if provided
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port)