import subprocess
import sys
import unittest
from pathlib import Path


class DeploymentConfigurationTests(unittest.TestCase):
    def test_production_settings_load(self):
        repo_root = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--settings=config.settings.production"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"Production startup check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )

    def test_api_domain_in_allowed_hosts_and_csrf(self):
        repo_root = Path(__file__).resolve().parent
        code = (
            "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings.production'; "
            "from django.conf import settings; "
            "assert 'api.magnivelinternational.org' in settings.ALLOWED_HOSTS, f'api.magnivelinternational.org missing in ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}'; "
            "assert 'https://api.magnivelinternational.org' in settings.CSRF_TRUSTED_ORIGINS, f'https://api.magnivelinternational.org missing in CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}'; "
            "assert 'https://magnivelinternational.org' in settings.CORS_ALLOWED_ORIGINS, f'frontend missing in CORS: {settings.CORS_ALLOWED_ORIGINS}';"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Domain configuration assertion failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
