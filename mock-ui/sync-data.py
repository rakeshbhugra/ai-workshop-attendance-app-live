"""Generate the file-compatible browser dataset from the mock JSON."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
data = json.loads((root / 'mock-data.json').read_text())
(root / 'mock-data.js').write_text('window.MOCK_DATA = ' + json.dumps(data, indent=2) + ';\n')
print('Updated mock-data.js from mock-data.json')
