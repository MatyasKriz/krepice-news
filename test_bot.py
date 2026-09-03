import re
from bot import parse_list, parse_post

LIST = '''
<div class="table-col card">
  <span class="date">01.09.2026</span> <span class="time">10:45<i class="space">&nbsp;</i>hod</span>
  <h3><a href="/obec/9LKmaG-2NL1X/hlaseni/tJpCREHd3od_">01 09</a></h3>
  <p class="block-2line">pohodov&eacute; zp&iacute;v&aacute;n&iacute; 5.9.2026</p>
</div>
<div class="table-col card">
  <span class="date">31.08.2026</span> <span class="time">10:45<i class="space">&nbsp;</i>hod</span>
  <h3><a href="/obec/9LKmaG-2NL1X/hlaseni/JGFW5DHzEUY4">31 08</a></h3>
  <p class="block-2line">Druhé</p>
</div>'''
POST = '''<source src="/data/hlasenie_prilohy/hy2ceKwUZPvv.mp3" type="audio/mpeg">
<source src="/data/hlasenie_prilohy/M3GTp8lNI7n0.mp3" type="audio/mpeg">
<source src="/data/hlasenie_prilohy/hy2ceKwUZPvv.mp3" type="audio/mpeg">'''

assert parse_list(LIST) == [
    {"id": "tJpCREHd3od_", "date": "01.09.2026", "time": "10:45", "title": "pohodové zpívání 5.9.2026"},
    {"id": "JGFW5DHzEUY4", "date": "31.08.2026", "time": "10:45", "title": "Druhé"},
]
assert parse_post(POST) == ["hy2ceKwUZPvv", "M3GTp8lNI7n0"]
print("ok")

from bot import chunk
short = "Byl nalezen klíček. Je k vyzvednutí na obecním úřadě."
assert chunk(short) == [short]
long = " ".join(f"Věta číslo {i} má nějaký obsah." for i in range(30))
parts = chunk(long)
assert len(parts) > 1 and all(len(p) <= 300 for p in parts), parts
assert parts[0].endswith(f"(1/{len(parts)})") and parts[-1].endswith(f"({len(parts)}/{len(parts)})")
assert " ".join(re.sub(r" \(\d+/\d+\)$", "", p) for p in parts) == long
print("chunk ok")

from bot import fix
assert fix("napište na jan.novak zavináč seznam.cz nebo") == "napište na jan.novak@seznam.cz nebo"
assert fix("e-mailu v pohospaní zavináče-e-mail.cz. Nově") == "e-mailu v pohospaní@e-mail.cz. Nově"
assert fix("info zavináč obec tečka cz") == "info@obec.cz"
assert fix("Vstupné dobrovolné.") == "Vstupné dobrovolné."  # untouched
print("fix ok")

import datetime as dt
from bot import next_run
D = dt.datetime(2026, 9, 3)
assert next_run(D.replace(hour=10, minute=2)) == D.replace(hour=10, minute=3)
assert next_run(D.replace(hour=10, minute=3)) == D.replace(hour=11, minute=3)
assert next_run(D.replace(hour=22, minute=30)) == D.replace(hour=6, minute=3) + dt.timedelta(days=1)
assert next_run(D.replace(hour=3, minute=0)) == D.replace(hour=6, minute=3)
assert next_run(D.replace(hour=5, minute=10)) == D.replace(hour=6, minute=3)
print("next_run ok")
