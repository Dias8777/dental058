"""МИС для стоматологии — MVP. Форма 058/у РК."""
import os
from datetime import date, datetime

import streamlit as st

import db
import printform

st.set_page_config(page_title="Мед. карты — форма 058/у", page_icon="🦷", layout="wide")
db.init()

SEX = ["мужской", "женский"]
LOCALITY = ["город", "село"]
FILE_KINDS = ["Фото", "3D / КЛКТ снимок", "Рентген", "Документ", "Другое"]


def _d(value, fallback=None):
    """Строка ISO -> date для виджетов."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def gate():
    """Простейшая защита паролем. Пароль берётся из st.secrets или env APP_PASSWORD."""
    try:
        pwd = os.environ.get("APP_PASSWORD") or st.secrets.get("APP_PASSWORD", "")
    except Exception:  # secrets.toml отсутствует — локальный запуск без пароля
        pwd = os.environ.get("APP_PASSWORD", "")
    if not pwd or st.session_state.get("auth"):
        return True
    st.title("🦷 Мед. карты — форма 058/у")
    with st.form("gate"):
        entered = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти", type="primary"):
            if entered == pwd:
                st.session_state.auth = True
                st.rerun()
            st.error("Неверный пароль")
    st.caption("Демоверсия. Не вводите реальные данные пациентов.")
    return False


def sidebar():
    st.sidebar.title("🦷 Картотека")
    search = st.sidebar.text_input("Поиск", placeholder="ФИО, ИИН или телефон")
    patients = db.list_patients(search)

    if st.sidebar.button("➕ Новый пациент", use_container_width=True, type="primary"):
        st.session_state.pid = None
        st.session_state.tab = "new"

    st.sidebar.caption(f"Найдено: {len(patients)}")
    for p in patients:
        label = f"{p['fio']}  ·  {p['birth_date'] or '—'}"
        if st.sidebar.button(label, key=f"p{p['id']}", use_container_width=True):
            st.session_state.pid = p["id"]
            st.session_state.pop("tab", None)
    return patients


def patient_form(patient):
    """Паспортная часть — пункты 1-10 формы."""
    p = dict(patient) if patient else {}
    with st.form("patient"):
        c1, c2, c3 = st.columns(3)
        p["fio"] = c1.text_input("2. ФИО *", p.get("fio", ""))
        p["iin"] = c2.text_input("1. ИИН", p.get("iin", ""), max_chars=12)
        p["phone"] = c3.text_input("Телефон", p.get("phone", ""))

        c1, c2, c3, c4 = st.columns(4)
        bd = c1.date_input("3. Дата рождения", _d(p.get("birth_date"), date(1990, 1, 1)),
                           min_value=date(1900, 1, 1), max_value=date.today(), format="DD.MM.YYYY")
        p["birth_date"] = bd.isoformat()
        age = date.today().year - bd.year - ((date.today().month, date.today().day) < (bd.month, bd.day))
        c2.metric("5. Возраст", age)
        p["sex"] = c3.selectbox("4. Пол", SEX, index=SEX.index(p["sex"]) if p.get("sex") in SEX else 0)
        p["nationality"] = c4.text_input("6. Национальность", p.get("nationality", ""))

        c1, c2 = st.columns([1, 3])
        p["locality"] = c1.selectbox("7. Житель", LOCALITY,
                                     index=LOCALITY.index(p["locality"]) if p.get("locality") in LOCALITY else 0)
        p["address"] = c2.text_input("8. Адрес (область, район, город, улица, дом, кв.)", p.get("address", ""))

        c1, c2, c3 = st.columns(3)
        p["workplace"] = c1.text_input("9. Место работы / учёбы", p.get("workplace", ""))
        p["position"] = c2.text_input("Должность", p.get("position", ""))
        p["education"] = c3.text_input("Образование", p.get("education", ""))
        p["insurance"] = st.text_input("10. Страховая компания, № полиса", p.get("insurance", ""))

        if st.form_submit_button("💾 Сохранить пациента", type="primary"):
            if not p["fio"].strip():
                st.error("ФИО обязательно")
            else:
                st.session_state.pid = db.save_patient(patient["id"] if patient else None, p)
                st.session_state.pop("tab", None)
                st.success("Сохранено")
                st.rerun()


def teeth_chart(card):
    """Зубная формула: выбираем состояние-«кисть», затем кликаем по зубам."""
    teeth = db.get_teeth(card["id"])
    states = list(db.TOOTH_STATES)
    labels = {s: (f"{s} — {db.TOOTH_STATES[s][0]}" if s else "здоров") for s in states}

    st.caption("Выберите состояние, затем нажимайте на зубы")
    brush = st.radio("Состояние", states, format_func=lambda s: labels[s],
                     horizontal=True, label_visibility="collapsed")

    def row(order):
        cols = st.columns(16, gap="small")
        for col, t in zip(cols, order):
            cur = teeth.get(t, "")
            color = db.TOOTH_STATES.get(cur, ("", "#fff"))[1]
            col.markdown(
                f"<div style='text-align:center;font-size:11px;color:#888'>{t}</div>"
                f"<div style='text-align:center;background:{color};color:"
                f"{'#000' if cur in ('', 'C') else '#fff'};border:1px solid #bbb;"
                f"border-radius:4px;padding:6px 0;font-weight:700;min-height:30px'>{cur or '·'}</div>",
                unsafe_allow_html=True)
            if col.button("✎", key=f"t{card['id']}_{t}", use_container_width=True):
                db.set_tooth(card["id"], t, brush)
                st.rerun()

    st.markdown("**Верхняя челюсть**")
    row(db.UPPER)
    st.markdown("**Нижняя челюсть**")
    row(db.LOWER)

    used = {s for s in teeth.values() if s}
    if used:
        st.caption(" · ".join(f"**{s}** — {db.TOOTH_STATES[s][0]}" for s in states if s in used))


def card_form(card):
    """Клиническая часть — пункты 11-22."""
    c = dict(card)
    with st.form("card"):
        c1, c2 = st.columns(2)
        c["card_no"] = c1.text_input("№ карты", c.get("card_no", ""))
        c["open_date"] = c2.date_input("Дата", _d(c.get("open_date"), date.today()),
                                       format="DD.MM.YYYY").isoformat()
        for key, label in db.CARD_TEXT_FIELDS:
            short = key in ("diagnosis", "bite")
            c[key] = (st.text_input(label, c.get(key) or "") if short
                      else st.text_area(label, c.get(key) or "", height=80))
        c1, c2 = st.columns(2)
        c["doctor"] = c1.text_input("Лечащий врач", c.get("doctor", ""))
        c["head_doctor"] = c2.text_input("Заведующий отделением", c.get("head_doctor", ""))
        if st.form_submit_button("💾 Сохранить карту", type="primary"):
            db.save_card(card["id"], c)
            st.success("Карта сохранена")
            st.rerun()


def visits_tab(card):
    """П.19 — каждый приём добавляет запись, карта живёт во времени."""
    with st.expander("➕ Добавить приём", expanded=True):
        with st.form("visit", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 2, 2])
            v_date = c1.date_input("Дата приёма", date.today(), format="DD.MM.YYYY")
            v_diag = c2.text_input("Диагноз")
            v_doc = c3.text_input("Врач", card["doctor"] or "")
            v_text = st.text_area("Что проделано (услуги, препараты, зубы)", height=100)
            if st.form_submit_button("Добавить запись", type="primary"):
                if v_text.strip():
                    db.add_visit(card["id"], {"visit_date": v_date.isoformat(), "text": v_text,
                                              "diagnosis": v_diag, "doctor": v_doc})
                    st.rerun()
                else:
                    st.error("Опишите, что было проделано")

    visits = db.list_visits(card["id"])
    st.caption(f"Записей: {len(visits)}")
    for v in visits:
        with st.container(border=True):
            c1, c2 = st.columns([10, 1])
            c1.markdown(f"**{v['visit_date']}** · {v['doctor'] or '—'}"
                        + (f"  \n_{v['diagnosis']}_" if v["diagnosis"] else ""))
            c1.write(v["text"])
            if c2.button("🗑", key=f"dv{v['id']}"):
                db.delete_visit(v["id"])
                st.rerun()


def files_tab(patient):
    with st.form("upload", clear_on_submit=True):
        up = st.file_uploader("Фото, 3D-снимки, рентген, документы",
                              accept_multiple_files=True)
        c1, c2 = st.columns([1, 2])
        kind = c1.selectbox("Тип", FILE_KINDS)
        note = c2.text_input("Примечание (дата съёмки, зуб и т.п.)")
        if st.form_submit_button("⬆️ Загрузить", type="primary") and up:
            for f in up:
                db.add_file(patient["id"], f, kind, note)
            st.rerun()

    rows = db.list_files(patient["id"])
    st.caption(f"Файлов: {len(rows)}")
    for f in rows:
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 2, 1])
            c1.markdown(f"**{f['filename']}**  \n{f['kind']} · {f['size'] / 1e6:.1f} МБ"
                        + (f" · {f['note']}" if f["note"] else ""))
            path = db.file_path(f)
            if os.path.exists(path):
                if f["filename"].lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    c1.image(path, width=280)
                with open(path, "rb") as fh:
                    c2.download_button("⬇️ Скачать", fh.read(), file_name=f["filename"],
                                       key=f"dl{f['id']}", use_container_width=True)
            else:
                c2.warning("нет файла")
            if c3.button("🗑", key=f"df{f['id']}"):
                db.delete_file(f["id"])
                st.rerun()


def print_tab(patient, card):
    html = printform.render(patient, card, db.get_teeth(card["id"]), db.list_visits(card["id"]))
    st.download_button("⬇️ Скачать форму 058/у (HTML → печать через Ctrl+P)", html,
                       file_name=f"058u_{patient['fio'].replace(' ', '_')}.html",
                       mime="text/html", type="primary")
    st.components.v1.html(html, height=900, scrolling=True)


def main():
    if not gate():
        return
    sidebar()
    pid = st.session_state.get("pid")

    if st.session_state.get("tab") == "new" or pid is None:
        st.title("Новый пациент" if st.session_state.get("tab") == "new" else "Мед. карты — форма 058/у")
        if st.session_state.get("tab") != "new":
            st.info("Выберите пациента слева или создайте нового.")
            return
        patient_form(None)
        return

    patient = db.get_patient(pid)
    if patient is None:
        st.session_state.pid = None
        st.rerun()
    card = db.get_or_create_card(pid)

    st.title(patient["fio"])
    st.caption(f"ИИН {patient['iin'] or '—'} · {patient['birth_date'] or '—'} · "
               f"{patient['sex'] or '—'} · карта № {card['card_no'] or '—'}")

    t1, t2, t3, t4, t5, t6 = st.tabs(
        ["👤 Пациент", "📋 Карта 058/у", "🦷 Зубная формула", "📅 Приёмы", "📎 Файлы", "🖨 Печать"])
    with t1:
        patient_form(patient)
    with t2:
        card_form(card)
    with t3:
        teeth_chart(card)
    with t4:
        visits_tab(card)
    with t5:
        files_tab(patient)
    with t6:
        print_tab(patient, card)


main()
