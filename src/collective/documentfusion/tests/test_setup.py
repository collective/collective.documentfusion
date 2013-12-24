# -*- coding: utf-8 -*-
"""Setup/installation tests for this package."""

from collective.documentfusion.testing import IntegrationTestCase
from plone import api


class TestInstall(IntegrationTestCase):
    """Test installation of collective.documentfusion into Plone."""

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if collective.documentfusion is installed with portal_quickinstaller."""
        self.assertTrue(self.installer.isProductInstalled('collective.documentfusion'))

    def test_uninstall(self):
        """Test if collective.documentfusion is cleanly uninstalled."""
        self.installer.uninstallProducts(['collective.documentfusion'])
        self.assertFalse(self.installer.isProductInstalled('collective.documentfusion'))

    # browserlayer.xml
    def test_browserlayer(self):
        """Test that ICollectiveDocumentfusionLayer is registered."""
        from collective.documentfusion.interfaces import ICollectiveDocumentfusionLayer
        from plone.browserlayer import utils
        self.assertIn(ICollectiveDocumentfusionLayer, utils.registered_layers())
