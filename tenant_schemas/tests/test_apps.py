from django.apps import apps
from django.core.checks import Critical, Error, Warning
from django.test import TestCase
from django.test.utils import modify_settings, override_settings

from tenant_schemas.apps import best_practice
from tenant_schemas.utils import get_tenant_model


class AppConfigTests(TestCase):

    maxDiff = None

    def assertBestPractice(self, expected):
        actual = best_practice(apps.get_app_configs())
        self.assertEqual(expected, actual)

    @override_settings()
    def test_unset_tenant_apps(self):
        from django.conf import settings
        del settings.TENANT_APPS
        self.assertBestPractice([
            Critical('TENANT_APPS setting not set'),
        ])

    @override_settings()
    def test_unset_tenant_model(self):
        from django.conf import settings
        del settings.TENANT_MODEL
        self.assertBestPractice([
            Critical('TENANT_MODEL setting not set'),
        ])

    @override_settings()
    def test_unset_shared_apps(self):
        from django.conf import settings
        del settings.SHARED_APPS
        self.assertBestPractice([
            Critical('SHARED_APPS setting not set'),
        ])

    @override_settings(DATABASE_ROUTERS=())
    def test_database_routers(self):
        self.assertBestPractice([
            Critical("DATABASE_ROUTERS setting must contain "
                     "'tenant_schemas.routers.TenantSyncRouter'."),
        ])

    @override_settings(INSTALLED_APPS=[
        'dts_test_app',
        'customers',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'tenant_schemas',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ])
    def test_tenant_schemas_before_django_installed_apps(self):
        self.assertBestPractice([
            Warning("You should put 'tenant_schemas' before any django "
                    "core applications in INSTALLED_APPS.",
                    obj="django.conf.settings",
                    hint="This is necessary to overwrite built-in django "
                         "management commands with their schema-aware "
                         "implementations."),
        ])

    @override_settings(INSTALLED_APPS=[
        'dts_test_app',
        'customers',
        'tenant_schemas',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ])
    def test_tenant_schemas_after_custom_apps_in_installed_apps(self):
        self.assertBestPractice([])

    @override_settings(TENANT_APPS=())
    def test_tenant_apps_empty(self):
        self.assertBestPractice([
            Error("TENANT_APPS is empty.",
                  hint="Maybe you don't need this app?"),
            Error("You have INSTALLED_APPS that are not in either of "
                  "TENANT_APPS or SHARED_APPS",
                  hint=['dts_test_app']),
        ])

    @override_settings(PG_EXTRA_SEARCH_PATHS=['public', 'demo1', 'demo2'])
    def test_public_schema_on_extra_search_paths(self):
        TenantModel = get_tenant_model()
        TenantModel.objects.create(
            schema_name='demo1', domain_url='demo1.example.com')
        TenantModel.objects.create(
            schema_name='demo2', domain_url='demo2.example.com')
        self.assertBestPractice([
            Critical("public can not be included on PG_EXTRA_SEARCH_PATHS."),
            Critical("Do not include tenant schemas (demo1, demo2) on PG_EXTRA_SEARCH_PATHS."),
        ])

    @override_settings(SHARED_APPS=(), INSTALLED_APPS=(
        'tenant_schemas',
        'dts_test_app',
        'django.contrib.contenttypes',
    ))
    @modify_settings(TENANT_APPS={
        'append': 'django.contrib.contenttypes',
    })
    def test_shared_apps_empty(self):
        self.assertBestPractice([
            Warning("SHARED_APPS is empty."),
            Error("You have INSTALLED_APPS that are not in either of "
                  "TENANT_APPS or SHARED_APPS",
                  hint=['tenant_schemas']),
        ])

    @override_settings(TENANT_APPS=(
        'dts_test_app',
        'django.contrib.flatpages',
    ))
    def test_tenant_app_missing_from_install_apps(self):
        self.assertBestPractice([
            Error("You have TENANT_APPS that are not in INSTALLED_APPS",
                  hint=['django.contrib.flatpages']),
        ])

    @modify_settings(SHARED_APPS={
        'append': 'django.contrib.flatpages',
    })
    def test_shared_app_missing_from_install_apps(self):
        self.assertBestPractice([
            Error("You have SHARED_APPS that are not in INSTALLED_APPS",
                  hint=['django.contrib.flatpages']),
        ])

    @modify_settings(INSTALLED_APPS={
        'append': 'django.contrib.humanize',
    })
    def test_installed_app_missing_from_shared_and_tenant_apps(self):
        self.assertBestPractice([
            Error("You have INSTALLED_APPS that are not in either of "
                  "TENANT_APPS or SHARED_APPS",
                  hint=['django.contrib.humanize']),
        ])
