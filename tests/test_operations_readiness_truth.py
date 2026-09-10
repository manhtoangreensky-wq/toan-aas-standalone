"""Only an explicit successful configuration response proves disabled state."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_operations_configuration_distinguishes_unknown_disabled_enabled():
    source = (ROOT / 'static/portal/integration.js').read_text(encoding='utf-8')
    start = source.find('function operationsConfigurationState(')
    assert start >= 0, 'Missing explicit configuration-state projection'
    end = source.index('\n  function ', start + 10)
    script = source[start:end] + '''
const inputs = [{}, {ok:false,data:{flags:{autopilot_enabled:false}}},
{ok:true,data:{flags:{}}}, {ok:true,data:{flags:{autopilot_enabled:"false"}}},
{ok:true,data:{flags:{autopilot_enabled:false}}},
{ok:true,data:{flags:{autopilot_enabled:true}}}];
process.stdout.write(JSON.stringify(inputs.map(operationsConfigurationState)));
'''
    result = subprocess.run([shutil.which('node'), '-e', script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == ['unknown', 'unknown', 'unknown', 'unknown', 'disabled', 'enabled']


def test_operations_guard_does_not_mislabel_disabled_as_permission_denied():
    source = (ROOT / 'static/portal/portal.js').read_text(encoding='utf-8')
    start = source.index('function renderOperationsAdmin(page, context)')
    end = source.index('function automationMonitorStateLabel', start)
    script = '''
const adminOperationsText = key => key;
const safeText = value => value;
const renderHero = () => '';
''' + source[start:end] + '''
const states = ['disabled', 'unknown', 'enabled'].map(operationsConfigurationState =>
renderOperationsAdmin({}, {operationsConfigurationState, operationsAdminReadState:'guarded'}));
process.stdout.write(JSON.stringify(states));
'''
    result = subprocess.run([shutil.which('node'), '-e', script], capture_output=True, text=True, check=True)
    disabled, unknown, enabled = json.loads(result.stdout)
    assert 'disabled.title' in disabled
    assert 'unavailable.title' in unknown and 'unavailable.title' in enabled
    assert all('guard.title' not in markup for markup in (disabled, unknown, enabled))
