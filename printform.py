"""Печатная форма 058/у — HTML, открывается в браузере и печатается Ctrl+P."""
from html import escape

import db


def fmt_date(value):
    """ISO -> ДД.ММ.ГГГГ для печати."""
    try:
        y, m, d = str(value).split("-")
        return f"{d}.{m}.{y}"
    except (ValueError, AttributeError):
        return value


def _row(label, value):
    return f'<div class="fld"><span class="lbl">{escape(label)}</span>' \
           f'<span class="val">{escape(value or "—")}</span></div>'


def _teeth_row(teeth, order):
    cells = "".join(
        f'<td><div class="tn">{t}</div><div class="ts">{escape(teeth.get(t) or "")}</div></td>'
        for t in order)
    return f"<tr>{cells}</tr>"


def render(patient, card, teeth, visits):
    p, c = dict(patient), dict(card)
    body = [
        f'<h1>Медицинская карта стоматологического больного (включая санацию) '
        f'№ {escape(c.get("card_no") or "___")}</h1>',
        '<p class="sub">форма № 058/у, утверждена приказом и.о. МЗ РК № ҚР ДСМ-175/2020 от 30 октября 2020 года</p>',
        _row("Дата", fmt_date(c.get("open_date"))),
        '<h2>Паспортная часть</h2>',
        _row("1. ИИН", p.get("iin")),
        _row("2. Фамилия, имя, отчество (при его наличии)", p.get("fio")),
        _row("3. Дата рождения", fmt_date(p.get("birth_date"))),
        _row("4. Пол", p.get("sex")),
        _row("6. Национальность", p.get("nationality")),
        _row("7. Житель", p.get("locality")),
        _row("8. Адрес проживания", p.get("address")),
        _row("9. Место работы / учёбы", p.get("workplace")),
        _row("Должность", p.get("position")),
        _row("Образование", p.get("education")),
        _row("10. Страховая компания, № полиса", p.get("insurance")),
        '<h2>Клиническая часть</h2>',
    ]
    for key, label in db.CARD_TEXT_FIELDS:
        if key == "plan":
            body.append('<h2>Осмотр полости рта, состояние зубов</h2>')
            body.append(
                '<table class="teeth">'
                + _teeth_row(teeth, db.UPPER) + _teeth_row(teeth, db.LOWER)
                + '</table>'
                '<p class="legend">O — зуб отсутствует, R — корень зуба, C — кариес, P — пульпит, '
                'Pt — периодонтит, П — пломба, A — патология пародонта, K — коронка, И — искусственный зуб</p>'
                '<h2>19. Дневниковые записи</h2>'
                + (''.join(
                    f'<div class="visit"><b>{escape(fmt_date(v["visit_date"]) or "")}</b> — '
                    f'{escape(v["doctor"] or "")}<br>'
                    f'<i>{escape(v["diagnosis"] or "")}</i><br>'
                    f'{escape(v["text"] or "").replace(chr(10), "<br>")}</div>'
                    for v in visits) or '<p class="val">— записей нет —</p>'))
        body.append(_row(label, c.get(key)))
    body.append('<div class="sign">Лечащий врач ______________________ '
                f'{escape(c.get("doctor") or "")}</div>')
    body.append('<div class="sign">Заведующий отделением ______________________ '
                f'{escape(c.get("head_doctor") or "")}</div>')

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Форма 058/у — {escape(p.get('fio') or '')}</title>
<style>
 body{{font-family:"Times New Roman",serif;font-size:12pt;color:#000;background:#fff;
      max-width:19cm;margin:0 auto;padding:1.5cm 1cm}}
 h1{{font-size:14pt;text-align:center;margin:0 0 4px}}
 h2{{font-size:12pt;margin:18px 0 6px;border-bottom:1px solid #000;padding-bottom:2px}}
 .sub{{text-align:center;font-size:9pt;margin:0 0 16px}}
 .fld{{margin:5px 0;line-height:1.5}}
 .lbl{{font-weight:bold}} .lbl::after{{content:": "}}
 .val{{border-bottom:1px dotted #666}}
 table.teeth{{border-collapse:collapse;margin:8px auto;width:100%}}
 table.teeth td{{border:1px solid #000;text-align:center;padding:2px 0;width:6.25%}}
 .tn{{font-size:8pt;color:#444}} .ts{{font-weight:bold;min-height:14px}}
 .legend{{font-size:8.5pt;font-style:italic}}
 .visit{{border-left:3px solid #000;padding:4px 10px;margin:8px 0}}
 .sign{{margin-top:22px}}
 @media print{{body{{padding:0}}}}
</style></head><body>{''.join(body)}</body></html>"""
