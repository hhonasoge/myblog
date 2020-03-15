import os
import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # type: ignore

from varsnap import core, TestVarSnap


def add(x, y):
    return x + y


null = open(os.devnull, 'w')


class TestResult(unittest.runner.TextTestResult):
    def __init__(self, *args, **kwargs):
        super(TestResult, self).__init__(*args, **kwargs)
        self.successes = []

    def addSuccess(self, test):
        super(TestResult, self).addSuccess(test)
        self.successes.append(test)


class TestAssertGenerator(unittest.TestCase):
    def setUp(self):
        core.CONSUMERS = []

    def tearDown(self):
        core.CONSUMERS = []

    def run_test_case(self, test_case):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case)
        runner = unittest.TextTestRunner(stream=null, resultclass=TestResult)
        return runner.run(suite)

    @patch('varsnap.core.Consumer.consume')
    def test_generate(self, mock_consume):
        core.Consumer(add)
        mock_consume.return_value = (True, '')
        result = self.run_test_case(TestVarSnap)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)
        self.assertEqual(len(result.successes), 1)

    @patch('varsnap.core.Consumer.consume')
    def test_generate_failure(self, mock_consume):
        core.Consumer(add)
        mock_consume.return_value = (False, '')
        result = self.run_test_case(TestVarSnap)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 0)
        self.assertEqual(len(result.successes), 0)

    @patch('varsnap.core.Consumer.consume')
    def test_generate_skipped(self, mock_consume):
        core.Consumer(add)
        mock_consume.return_value = None
        result = self.run_test_case(TestVarSnap)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(len(result.successes), 0)
