#!/usr/bin/env python3
"""Check fail-closed launcher guards without USB or reboot."""
import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

source = Path(__file__).with_name('run-tablet.py')
spec = importlib.util.spec_from_file_location('tablet_launcher', source)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
argv = [str(source), '--from-android', '--skip-poc']
with patch.object(sys, 'argv', argv), patch.object(launcher, 'sha', return_value='0'*64), patch.object(launcher, 'run') as calls:
    try:
        launcher.main()
    except RuntimeError as error:
        assert 'hash' in str(error)
    else:
        raise AssertionError('Accepted a bad hash')
    calls.assert_not_called()
with patch.object(sys, 'argv', argv), patch.object(launcher, 'run', side_effect=['WRONG_TABLET', 'uid=0(root)']) as calls:
    try:
        launcher.main()
    except RuntimeError as error:
        assert 'No reboot sent' in str(error)
    else:
        raise AssertionError('Accepted a wrong tablet')
    assert len(calls.call_args_list) == 2
    assert all('reboot' not in x.args[0] for x in calls.call_args_list)
print('LAUNCHER_GUARDS_SELF_TEST_OK; no USB accessed')
