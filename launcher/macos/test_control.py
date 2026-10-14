import unittest
from unittest.mock import patch
import control

class ControlTests(unittest.TestCase):
    def test_exact_script_and_arguments(self):
        argv=['/usr/local/bin/node','/example/terminal/start.mjs']
        self.assertTrue(control.matching('node '+argv[1],argv))
        for bad in ['node '+argv[1]+' --check','python3 '+argv[1], 'node /other/start.mjs', 'sh -c "node '+argv[1]+'"']:
            self.assertFalse(control.matching(bad,argv))
    def test_existing_service_is_not_restarted(self):
        with patch.object(control,'matches',return_value=[(12,'node x')]), patch.object(control,'listening',return_value=True), patch.object(control.subprocess,'Popen') as spawn:
            self.assertIn('already running',control.start_one('Terminal host',['node','x']));spawn.assert_not_called()
    def test_uncertain_listener_is_not_duplicated(self):
        with patch.object(control,'matches',return_value=[(12,'node x')]), patch.object(control,'listening',return_value=False), patch.object(control.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'no duplicate'):control.start_one('Terminal host',['node','x'])
            spawn.assert_not_called()
    def test_duplicate_detection_does_not_signal(self):
        with patch.object(control,'matches',return_value=[(12,'node x'),(13,'node x')]),patch.object(control.os,'kill') as kill:
            with self.assertRaisesRegex(RuntimeError,'multiple'):control.stop_one('Terminal host',['node','x'])
            kill.assert_not_called()
    def test_stopping_rechecks_identity(self):
        with patch.object(control,'matches',return_value=[(12,'node x')]),patch.object(control,'inventory',return_value=[(12,'unrelated')]),patch.object(control.os,'kill') as kill:
            self.assertIn('changed',control.stop_one('Terminal host',['node','x']));kill.assert_not_called()
    def test_stopping_signals_only_exact_pid(self):
        with patch.object(control,'matches',return_value=[(12,'node x')]),patch.object(control,'inventory',side_effect=[[(12,'node x')],[]]),patch.object(control.os,'kill') as kill:
            self.assertIn('stopped',control.stop_one('Terminal host',['node','x']));kill.assert_called_once_with(12,control.signal.SIGINT)

if __name__=='__main__':unittest.main()
