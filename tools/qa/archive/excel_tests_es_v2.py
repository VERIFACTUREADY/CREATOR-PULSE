"""Pruebas de la hoja 05_ECONOMIA_UNITARIA.xlsx (auditoría V2, C-04).
Necesita LibreOffice (soffice) para recalcular. Uso: python3 tools/qa/excel_tests.py
Escribe qa/reports/archive-excel-tests-es-v2.json."""
import json, os, shutil, subprocess, sys, tempfile
from openpyxl import load_workbook

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
SRC = os.path.join(REPO, 'docs/archive/05_ECONOMIA_UNITARIA_ES_V2.xlsx')

def recalc(path):
    tmpd = tempfile.mkdtemp()
    subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'xlsx:Calc MS Excel 2007 XML', '--outdir', tmpd, path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    out = os.path.join(tmpd, os.path.basename(path))
    return load_workbook(out, data_only=True)

def scenario(edits):
    tmpd = tempfile.mkdtemp(); p = os.path.join(tmpd, 'caso.xlsx')
    shutil.copy(SRC, p)
    wb = load_workbook(p); ws = wb['Escenarios']
    for ref, v in edits.items(): ws[ref] = v
    wb.save(p)
    return recalc(p)['Escenarios']

results = []
def check(name, cond, detail):
    results.append({'prueba': name, 'ok': bool(cond), 'detalle': detail}); print(('OK  ' if cond else 'FAIL') + ' ' + name + ' → ' + str(detail))

# 1. Reproduce los informes con las hipótesis
e = scenario({})
vals = [round(e.cell(21, j).value, 2) for j in range(2, 7)]
check('Hipótesis reproducen 0,56/7,04/11,54/11,03/7,14', vals == [0.56, 7.04, 11.54, 11.03, 7.14], vals)
check('REAL vacía = DATOS INCOMPLETOS', e['G13'].value == 'DATOS INCOMPLETOS' and e['G21'].value == 'DATOS INCOMPLETOS', (e['G13'].value, e['G21'].value))
check('Ningún veredicto dice «rentable»', all('rentable' not in str(e.cell(22, j).value).lower() for j in range(2, 8)), [e.cell(22, j).value for j in range(2, 8)])

# 2. Caso del fallo V1: REAL con 1 de 5 partidas
e = scenario({'G4': 29.90, 'G7': 8, 'G15': 2.5, 'G16': 0, 'G17': 0})
v1 = round(29.90 / 1.21 - 8 - 2.5 - (29.90 * 0.029 + 0.30), 2)
check('REAL con 1/5 partidas → DATOS INCOMPLETOS (V1 habría dado margen)', e['G13'].value == 'DATOS INCOMPLETOS' and e['G21'].value == 'DATOS INCOMPLETOS',
      {'V2': e['G21'].value, 'V1_habria_calculado': v1})

# 3. Hipótesis con desglose parcial
e = scenario({'C7': 5})
check('Hipótesis con desglose parcial → DATOS INCOMPLETOS', e['C13'].value == 'DATOS INCOMPLETOS' and e['C21'].value == 'DATOS INCOMPLETOS', e['C21'].value)

# 4. REAL completo (valores de prueba que suman 14 €)
e = scenario({'G4': 29.90, 'G7': 8, 'G8': 4, 'G9': 1, 'G10': 0.5, 'G11': 0.5, 'G15': 2.5, 'G16': 0, 'G17': 0})
check('REAL completo calcula (prueba = 7,04 €)', e['G13'].value == 'COMPLETO' and round(e['G21'].value, 2) == 7.04, (e['G13'].value, e['G21'].value, e['G22'].value))

# 5. Un 0 explícito cuenta como dato; una celda vacía no
e = scenario({'G4': 29.90, 'G7': 8, 'G8': 4, 'G9': 0, 'G10': 0, 'G11': 0, 'G15': 2.5, 'G16': 0, 'G17': 0})
check('0 explícito es dato válido', e['G13'].value == 'COMPLETO', e['G13'].value)

os.makedirs(os.path.join(REPO, 'qa/reports'), exist_ok=True)
json.dump(results, open(os.path.join(REPO, 'qa/reports/archive-excel-tests-es-v2.json'), 'w'), indent=2, ensure_ascii=False)
sys.exit(0 if all(r['ok'] for r in results) else 1)
