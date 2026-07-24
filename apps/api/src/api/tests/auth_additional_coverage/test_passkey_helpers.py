"""Passkey Helpers auth coverage tests."""

import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from api.auth.passkeys import WebAuthnPasskey


class TestPasskeyHelpers:
    def test_base64url_round_trip(self):
        raw = b"goblin-passkey"
        encoded = WebAuthnPasskey.encode_base64url(raw)

        assert WebAuthnPasskey.decode_base64url(encoded) == raw

    def test_parse_authenticator_data_variants(self):
        with pytest.raises(ValueError, match="too short"):
            WebAuthnPasskey.parse_authenticator_data(b"short")

        rp_id_hash = b"\x01" * 32
        flags = b"\x05"
        sign_count = (7).to_bytes(4, byteorder="big")
        aaguid = b"\x02" * 16
        credential_id = b"cred-123"
        cred_len = len(credential_id).to_bytes(2, byteorder="big")
        public_key = b"\x04" + b"\x03" * 64
        payload = rp_id_hash + flags + sign_count + aaguid + cred_len + credential_id + public_key

        parsed = WebAuthnPasskey.parse_authenticator_data(payload)

        assert parsed["flags"] == 5
        assert parsed["sign_count"] == 7
        assert parsed["attested_credential_data"]["aaguid"] == aaguid.hex()
        assert parsed["attested_credential_data"]["credential_id"] == credential_id

    def test_parse_authenticator_data_without_attested_data(self):
        payload = b"\x01" * 32 + b"\x05" + (7).to_bytes(4, byteorder="big")

        parsed = WebAuthnPasskey.parse_authenticator_data(payload)

        assert parsed["attested_credential_data"] is None

    def test_parse_cose_public_key_success(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_numbers = private_key.public_key().public_numbers()
        cose_key = (
            b"\x04" + public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
        )

        parsed = WebAuthnPasskey.parse_cose_public_key(cose_key)

        assert parsed.public_numbers().x == public_numbers.x
        assert parsed.public_numbers().y == public_numbers.y

    def test_parse_cose_public_key_invalid(self):
        with pytest.raises(ValueError, match="Unsupported"):
            WebAuthnPasskey.parse_cose_public_key(b"invalid")

    def test_verify_signature_true_and_false(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        authenticator_data = b"auth-data"
        client_data_json = b'{"type":"webauthn.get"}'
        signed_data = authenticator_data + __import__("hashlib").sha256(client_data_json).digest()
        signature = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))

        assert (
            WebAuthnPasskey.verify_signature(
                public_key, signature, authenticator_data, client_data_json
            )
            is True
        )
        assert (
            WebAuthnPasskey.verify_signature(
                public_key, b"bad-signature", authenticator_data, client_data_json
            )
            is False
        )

    def test_verify_signature_generic_exception(self):
        class _BrokenPublicKey:
            def verify(self, *_args, **_kwargs):
                raise RuntimeError("boom")

        assert (
            WebAuthnPasskey.verify_signature(
                _BrokenPublicKey(),
                b"sig",
                b"auth",
                b'{"type":"webauthn.get"}',
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_verify_passkey_authentication_paths(self, monkeypatch):
        challenge = "challenge-123"
        origin = "https://goblin.example"
        client_data = {
            "challenge": WebAuthnPasskey.encode_base64url(challenge.encode()),
            "origin": origin,
            "type": "webauthn.get",
        }
        client_data_json = json.dumps(client_data).encode()
        encoded_client_data = WebAuthnPasskey.encode_base64url(client_data_json)
        encoded_auth_data = WebAuthnPasskey.encode_base64url(b"a" * 37)
        encoded_signature = WebAuthnPasskey.encode_base64url(b"signature")
        encoded_public_key = WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64)

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: {"flags": 1}),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_cose_public_key",
            staticmethod(lambda _data: object()),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "verify_signature",
            staticmethod(lambda *_args: True),
        )

        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=encoded_public_key,
                authenticator_data_b64=encoded_auth_data,
                client_data_json_b64=encoded_client_data,
                signature_b64=encoded_signature,
                challenge=challenge,
                origin=origin,
            )
            is True
        )

        bad_origin = dict(client_data, origin="https://other.example")
        bad_origin_b64 = WebAuthnPasskey.encode_base64url(json.dumps(bad_origin).encode())
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=encoded_public_key,
                authenticator_data_b64=encoded_auth_data,
                client_data_json_b64=bad_origin_b64,
                signature_b64=encoded_signature,
                challenge=challenge,
                origin=origin,
            )
            is False
        )

        assert WebAuthnPasskey.generate_challenge()

    @pytest.mark.asyncio
    async def test_verify_passkey_authentication_rejects_challenge_type_and_errors(
        self, monkeypatch
    ):
        challenge = "challenge-123"
        origin = "https://goblin.example"
        client_data = {
            "challenge": WebAuthnPasskey.encode_base64url(challenge.encode()),
            "origin": origin,
            "type": "webauthn.get",
        }

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: {"flags": 1}),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_cose_public_key",
            staticmethod(lambda _data: object()),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "verify_signature",
            staticmethod(lambda *_args: True),
        )

        wrong_challenge = dict(client_data, challenge=WebAuthnPasskey.encode_base64url(b"other"))
        wrong_type = dict(client_data, type="webauthn.create")

        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(wrong_challenge).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(wrong_type).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: (_ for _ in ()).throw(RuntimeError("bad auth data"))),
        )
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(client_data).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )
