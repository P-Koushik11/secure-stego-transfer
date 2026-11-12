import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

import app as backend


PASSWORD = "correct horse battery"


class ImageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.store = tempfile.TemporaryDirectory()
        self.original_store = backend.STORE
        backend.STORE = Path(self.store.name)
        self.client = backend.app.test_client()

    def tearDown(self):
        backend.STORE = self.original_store
        self.store.cleanup()

    def make_cover(self, image_format="PNG"):
        image = Image.new("RGB", (128, 128), (90, 130, 170))
        output = BytesIO()
        image.save(output, format=image_format)
        return output.getvalue()

    def create_transfer(self, filename, content, content_type):
        response = self.client.post(
            "/api/send",
            data={
                "secret_file": (BytesIO(content), filename, content_type),
                "cover_image": (BytesIO(self.make_cover()), "cover.png", "image/png"),
                "password": PASSWORD,
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()

    def recover_image(self, image_bytes, password=PASSWORD, filename="stego.png"):
        return self.client.post(
            "/api/receive-image",
            data={
                "stego_image": (BytesIO(image_bytes), filename),
                "password": password,
            },
            content_type="multipart/form-data",
        )

    def test_image_recovery_supports_file_types_without_consuming_transfer(self):
        for filename, content, content_type in (
            ("notes.txt", b"secret text", "text/plain"),
            ("report.pdf", b"%PDF-1.7\nexample", "application/pdf"),
        ):
            with self.subTest(filename=filename):
                transfer = self.create_transfer(filename, content, content_type)
                image_response = self.client.get(
                    f"/api/transfer-image/{transfer['transfer_code']}"
                )
                self.assertEqual(image_response.status_code, 200)
                image_bytes=image_response.get_data()
                image_response.close()
                self.assertTrue(image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

                files_before = set(backend.STORE.iterdir())
                recovered = self.recover_image(image_bytes)
                self.assertEqual(recovered.status_code, 200)
                self.assertEqual(recovered.data, content)
                self.assertIn(filename, recovered.headers["Content-Disposition"])
                self.assertTrue(
                    recovered.headers["Content-Type"].startswith(content_type)
                )
                self.assertEqual(set(backend.STORE.iterdir()), files_before)

                # The separate image recovery does not consume the legacy code transfer.
                code_recovery = self.client.post(
                    "/api/receive",
                    json={
                        "transfer_code": transfer["transfer_code"],
                        "password": PASSWORD,
                    },
                )
                self.assertEqual(code_recovery.status_code, 200)
                self.assertEqual(code_recovery.data, content)
                self.assertTrue(transfer["receiver_url"].endswith(
                    f"/receive?code={transfer['transfer_code']}"
                ))
                self.assertTrue(transfer["qr_code_data_url"].startswith("data:image/png;base64,"))

    def test_image_recovery_rejects_wrong_password_and_invalid_images(self):
        origin = backend.ORIGINS[0]
        preflight = self.client.options(
            "/api/receive-image",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight.headers["Access-Control-Allow-Origin"], origin)
        allowed_methods = preflight.headers["Access-Control-Allow-Methods"]
        self.assertIn("POST", allowed_methods)
        self.assertIn("OPTIONS", allowed_methods)
        allowed_headers = preflight.headers["Access-Control-Allow-Headers"].lower()
        self.assertIn("content-type", allowed_headers)
        self.assertIn("authorization", allowed_headers)

        transfer = self.create_transfer("notes.txt", b"private", "text/plain")
        image_response = self.client.get(
            f"/api/transfer-image/{transfer['transfer_code']}"
        )
        stego_png = image_response.get_data()
        image_response.close()

        wrong_password = self.recover_image(stego_png, password="wrong password")
        self.assertEqual(wrong_password.status_code, 400)
        self.assertNotIn(b"private", wrong_password.data)
        self.assertNotIn(b"wrong password", wrong_password.data)

        ordinary_png = self.recover_image(self.make_cover())
        self.assertEqual(ordinary_png.status_code, 400)
        self.assertIn(b"Could not recover the file", ordinary_png.data)

        jpeg_named_png = self.recover_image(
            self.make_cover("JPEG"), filename="stego.png"
        )
        self.assertEqual(jpeg_named_png.status_code, 400)
        self.assertIn(b"Unsupported image format", jpeg_named_png.data)

        corrupted = self.recover_image(b"\x89PNG\r\n\x1a\nbroken")
        self.assertEqual(corrupted.status_code, 400)
        self.assertNotIn(b"Traceback", corrupted.data)

    def test_image_recovery_enforces_upload_size_limit(self):
        response = self.recover_image(b"x" * (backend.MAX_STEGO_IMAGE_MB * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
