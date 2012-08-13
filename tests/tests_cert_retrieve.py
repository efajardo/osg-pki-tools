"""Test cert-retrieve script"""

import PKIClientTestCase

class CertRetrieveTests(PKIClientTestCase.PKIClientTestCase):

    command = "osg-cert-retrieve"

    def test_help(self):
        """Test running with -h to get help"""
        result = self.run_script(self.command, "-h")
        self.assertTrue("Usage:" in result.stdout,
                        self.run_error_msg(result))