import logging
import sys
import unittest

from qualname import qualname

from . import core


varsnap_logger = logging.getLogger(core.__name__)
varsnap_logger.handlers = []
varsnap_logger.disabled = True
varsnap_logger.propagate = False

test_logger = logging.getLogger(__name__)
test_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
test_logger.addHandler(handler)


class TestVarSnap(unittest.TestCase):
    def test_varsnap(self):
        results = []
        for consumer in core.CONSUMERS:
            consumer_name = qualname(consumer.target_func)
            test_logger.info("Running VarSnap tests for %s" % consumer_name)
            consumer.last_snap_id = None
            result = consumer.consume()
            if not result:
                continue
            results.append(result)
        if not results:
            raise unittest.case.SkipTest('No Snaps found')
        results = [x[1] for x in results if not x[0]]
        if not results:
            self.assertTrue(True)
            return
        result_log = "\n\n".join(results)
        self.assertTrue(False, result_log)
