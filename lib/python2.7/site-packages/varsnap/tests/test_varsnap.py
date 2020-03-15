import json
import logging
import os
import sys
import unittest
try:
    from unittest.mock import patch
    from unittest.mock import MagicMock
except ImportError:
    from mock import patch  # type: ignore
    from mock import MagicMock

from varsnap import core
from varsnap.__version__ import __version__


logger = logging.getLogger(core.__name__)
logger.disabled = True


class EnvVar(unittest.TestCase):
    def setUp(self):
        self.orig_varsnap = os.environ.get(core.ENV_VARSNAP, '')
        self.orig_env = os.environ.get(core.ENV_ENV, '')
        self.orig_producer_token = os.environ.get(core.ENV_PRODUCER_TOKEN, '')
        self.orig_consumer_token = os.environ.get(core.ENV_CONSUMER_TOKEN, '')
        core.CONSUMERS = []
        core.PRODUCERS = []

    def tearDown(self):
        os.environ[core.ENV_VARSNAP] = self.orig_varsnap
        os.environ[core.ENV_ENV] = self.orig_env
        os.environ[core.ENV_PRODUCER_TOKEN] = self.orig_producer_token
        os.environ[core.ENV_CONSUMER_TOKEN] = self.orig_consumer_token


class TestEnvVar(EnvVar):
    def test_env_var(self):
        os.environ[core.ENV_VARSNAP] = 'true'
        env = core.env_var(core.ENV_VARSNAP)
        self.assertEqual(env, 'true')

    def test_downcases_env_var(self):
        os.environ[core.ENV_VARSNAP] = 'TRUE'
        env = core.env_var(core.ENV_VARSNAP)
        self.assertEqual(env, 'true')

    def test_unset_var(self):
        del os.environ[core.ENV_VARSNAP]
        env = core.env_var(core.ENV_VARSNAP)
        self.assertEqual(env, '')


class TestEqual(EnvVar):
    def test_primitives(self):
        self.assertTrue(core.equal(1, 1))
        self.assertFalse(core.equal(1, '1'))
        self.assertTrue(core.equal('asdf', 'asdf'))

    def test_iterables(self):
        self.assertTrue(core.equal([1, 2, 3], [1, 2, 3]))
        self.assertTrue(core.equal({1: 'a', 2: 'b'}, {1: 'a', 2: 'b'}))
        self.assertFalse(core.equal([1, 2], [1, 2, 3]))
        self.assertFalse(core.equal({1: 2}, {1: 3}))
        self.assertFalse(core.equal({1: 2}, {2: 2}))

    def test_objects(self):
        class X():
            def __init__(self, x):
                self.x = x
        self.assertTrue(core.equal(X('asdf'), X('asdf')))
        self.assertFalse(core.equal(X('asdf'), X('qwer')))
        self.assertTrue(core.equal(X(X('asdf')), X(X('asdf'))))


class TestGetSignature(unittest.TestCase):
    def assertEqualVersion(self, signature, expected):
        self.assertEqual(signature, expected % __version__)

    def test_standalone_func(self):
        signature = core.get_signature(core.env_var)
        self.assertEqualVersion(signature, 'python.%s.env_var')

    def test_class_func(self):
        signature = core.get_signature(core.Producer.serialize)
        self.assertEqualVersion(signature, 'python.%s.Producer.serialize')

    def test_instance_func(self):
        signature = core.get_signature(core.Producer.__init__)
        self.assertEqualVersion(signature, 'python.%s.Producer.__init__')


class TestProducer(EnvVar):
    def setUp(self):
        super(TestProducer, self).setUp()
        os.environ[core.ENV_VARSNAP] = 'true'
        os.environ[core.ENV_ENV] = 'production'
        os.environ[core.ENV_PRODUCER_TOKEN] = 'asdf'

        self.producer = core.Producer(core.env_var)

    def test_init(self):
        target_func = MagicMock()
        producer = core.Producer(target_func)
        self.assertEqual(producer.target_func, target_func)
        self.assertIn(producer, core.PRODUCERS)

    def test_is_enabled(self):
        self.assertTrue(core.Producer.is_enabled())

        os.environ[core.ENV_VARSNAP] = 'false'
        self.assertFalse(core.Producer.is_enabled())
        os.environ[core.ENV_VARSNAP] = 'true'

        os.environ[core.ENV_ENV] = 'development'
        self.assertFalse(core.Producer.is_enabled())
        os.environ[core.ENV_ENV] = 'production'

        os.environ[core.ENV_PRODUCER_TOKEN] = ''
        self.assertFalse(core.Producer.is_enabled())
        os.environ[core.ENV_PRODUCER_TOKEN] = 'asdf'

    def test_serialize(self):
        data = core.Producer.serialize('abcd')
        self.assertGreater(len(data), 0)

    @patch('requests.post')
    def test_produce_not_enabled(self, mock_post):
        os.environ[core.ENV_VARSNAP] = 'false'
        self.producer.produce('a', 'b', 'c')
        self.assertFalse(mock_post.called)

    @patch('requests.post')
    def test_produce(self, mock_post):
        self.producer.produce('a', 'b', 'c')
        self.assertEqual(mock_post.call_args[0][0], core.PRODUCE_SNAP_URL)
        data = mock_post.call_args[1]['data']
        self.assertEqual(data['producer_token'], 'asdf')
        self.assertEqual(data['signature'], core.get_signature(core.env_var))
        self.assertIn('inputs', data)
        self.assertIn('prod_outputs', data)


class TestConsumer(EnvVar):
    def setUp(self):
        super(TestConsumer, self).setUp()
        os.environ[core.ENV_VARSNAP] = 'true'
        os.environ[core.ENV_ENV] = 'development'
        os.environ[core.ENV_CONSUMER_TOKEN] = 'asdf'

        self.target_func = MagicMock()
        self.consumer = core.Consumer(self.target_func)

    def test_init(self):
        target_func = MagicMock()
        consumer = core.Consumer(target_func)
        self.assertEqual(consumer.target_func, target_func)
        self.assertIn(consumer, core.CONSUMERS)

    def test_is_enabled(self):
        self.assertTrue(core.Consumer.is_enabled())

        os.environ[core.ENV_VARSNAP] = 'false'
        self.assertFalse(core.Consumer.is_enabled())
        os.environ[core.ENV_VARSNAP] = 'true'

        os.environ[core.ENV_ENV] = 'production'
        self.assertFalse(core.Consumer.is_enabled())
        os.environ[core.ENV_ENV] = 'development'

        os.environ[core.ENV_CONSUMER_TOKEN] = ''
        self.assertFalse(core.Consumer.is_enabled())
        os.environ[core.ENV_CONSUMER_TOKEN] = 'asdf'

    def test_deserialize(self):
        data = core.Producer.serialize('abcd')
        output = core.Consumer.deserialize(data)
        self.assertEqual(output, 'abcd')

        data = core.Producer.serialize(EnvVar)
        output = core.Consumer.deserialize(data)
        self.assertEqual(output, EnvVar)

    def test_deserialize_known_error(self):
        with self.assertRaises(core.DeserializeError):
            core.Consumer.deserialize('abcd')

    @patch('pickle.loads')
    def test_deserialize_unknown_error(self, mock_loads):
        mock_loads.side_effect = MemoryError('asdf')
        with self.assertRaises(MemoryError):
            core.Consumer.deserialize('abcd')

    @patch('requests.post')
    def test_consume_not_enabled(self, mock_post):
        os.environ[core.ENV_VARSNAP] = 'false'
        self.consumer.consume_watch()
        self.assertFalse(mock_post.called)

    @patch('varsnap.core.qualname')
    @patch('requests.post')
    def test_consume_empty(self, mock_post, mock_qualname):
        mock_qualname.return_value = 'magicmock'
        mock_post.return_value = MagicMock(content='')
        self.consumer.consume()
        self.assertFalse(self.target_func.called)

    @patch('varsnap.core.qualname')
    @patch('requests.post')
    def test_consume(self, mock_post, mock_qualname):
        mock_qualname.return_value = 'magicmock'
        inputs = {
            'args': (2,),
            'kwargs': {},
            'globals': {},
        }
        data = {
            'results': [{
                'id': 'abcd',
                'inputs': core.Producer.serialize(inputs),
                'prod_outputs': core.Producer.serialize((4,)),
            }],
            'status': 'ok',
        }
        data = json.dumps(data)
        mock_post.return_value = MagicMock(content=data)
        self.target_func.return_value = (4,)
        self.consumer.consume()
        self.assertEqual(self.target_func.call_count, 1)
        self.assertEqual(self.target_func.call_args[0][0], 2)
        snap_consume_request = mock_post.mock_calls[0][2]['data']
        self.assertEqual(snap_consume_request['consumer_token'], 'asdf')
        signature = core.get_signature(core.env_var)
        self.assertEqual(snap_consume_request['signature'], signature)
        trial_produce_request = mock_post.mock_calls[1][2]['data']
        self.assertEqual(trial_produce_request['consumer_token'], 'asdf')
        self.assertEqual(trial_produce_request['snap_id'], 'abcd')
        dev_outputs = core.Producer.serialize((4,))
        self.assertEqual(trial_produce_request['dev_outputs'], dev_outputs)
        self.assertEqual(trial_produce_request['matches'], True)

    @patch('varsnap.core.qualname')
    @patch('requests.post')
    def test_consume_deduplicates(self, mock_post, mock_qualname):
        mock_qualname.return_value = 'magicmock'
        inputs = {
            'args': (2,),
            'kwargs': {},
            'globals': {},
        }
        data = {
            'results': [{
                'id': 'abcd',
                'inputs': core.Producer.serialize(inputs),
                'prod_outputs': core.Producer.serialize((4,)),
            }],
            'status': 'ok',
        }
        data = json.dumps(data)
        mock_post.side_effect = [
            MagicMock(content=data),
            MagicMock(content=data),
        ]
        self.target_func.return_value = (4,)
        with self.assertRaises(StopIteration):
            self.consumer.consume_watch()
        self.assertEqual(self.target_func.call_count, 1)

    @patch('varsnap.core.qualname')
    @patch('requests.post')
    def test_consume_catches_exceptions(self, mock_post, mock_qualname):
        mock_qualname.return_value = 'magicmock'
        inputs = {
            'args': (2,),
            'kwargs': {},
            'globals': {},
        }
        data = {
            'results': [{
                'id': 'abcd',
                'inputs': core.Producer.serialize(inputs),
                'prod_outputs': core.Producer.serialize((4,)),
            }],
            'status': 'ok',
        }
        data = json.dumps(data)
        mock_post.side_effect = [
            MagicMock(content=data),
            MagicMock(content=json.dumps({'status': 'ok'})),
        ]
        self.target_func.side_effect = ValueError('asdf')
        self.consumer.consume()
        self.assertEqual(self.target_func.call_count, 1)


class TestVarsnap(EnvVar):
    @patch('requests.post')
    def test_no_op(self, mock_post):
        os.environ[core.ENV_VARSNAP] = 'false'
        mock_func = MagicMock()
        mock_func.__name__ = 'mock_func'
        mock_func = core.varsnap(mock_func)
        mock_func(1)
        self.assertFalse(mock_post.called)

    @patch('varsnap.core.Consumer.consume_watch')
    @patch('varsnap.core.Producer.produce')
    def test_consume(self, mock_produce, mock_consume):
        if sys.version_info.major < 3:
            # TODO remove this
            return
        mock_func = MagicMock()
        mock_func.__name__ = 'mock_func'
        mock_func.return_value = 2
        varsnap_mock_func = core.varsnap(mock_func)
        result = varsnap_mock_func(1)
        self.assertEqual(result, 2)
        self.assertEqual(mock_func.call_count, 1)
        self.assertEqual(mock_consume.call_count, 0)
        self.assertEqual(mock_produce.call_count, 1)
        self.assertEqual(mock_produce.call_args[0][2], 2)

    @patch('varsnap.core.Consumer.consume_watch')
    @patch('varsnap.core.Producer.produce')
    def test_consume_exception(self, mock_produce, mock_consume):
        if sys.version_info.major < 3:
            # TODO remove this
            return
        mock_func = MagicMock()
        mock_func.__name__ = 'mock_func'
        mock_func.side_effect = ValueError('asdf')
        varsnap_mock_func = core.varsnap(mock_func)
        with self.assertRaises(ValueError):
            varsnap_mock_func(1)
        self.assertEqual(mock_func.call_count, 1)
        self.assertEqual(mock_consume.call_count, 0)
        self.assertEqual(mock_produce.call_count, 1)
        self.assertEqual(str(mock_produce.call_args[0][2]), 'asdf')

    @patch('varsnap.core.Consumer.consume_watch')
    @patch('varsnap.core.Producer.produce')
    def test_func_name(self, mock_produce, mock_consume):
        varsnap_func = core.varsnap(core.Producer.serialize)
        self.assertEqual(varsnap_func.__name__, 'serialize')
