"""Этап 2: проверка таблицы языковых пар hreflang.csv (спецификация, раздел 3)."""
from structure_map import WAVE_ORDER, card_url, is_page, url_errors

HREFLANG_COLUMNS = ["entity_id", "template", "lang", "page_id", "url", "wave", "status", "in_hreflang",
                    "switch_to"]
LAUNCH_CLUSTERS = 84


def check_hreflang(header: list[str], hl: list[dict], maps: dict[str, list[dict]], cards: list[dict],
                   launch_clusters: int = LAUNCH_CLUSTERS) -> list[str]:
    if header != HREFLANG_COLUMNS:
        return [f"hreflang: колонки {header}, ожидалось {HREFLANG_COLUMNS}"]
    errs: list[str] = []
    by_id = {lang: {r["id"]: r for r in rows} for lang, rows in maps.items()}
    by_entity: dict[tuple[str, str], dict] = {}
    urls = {"en": {}, "es": {}}
    per_page: dict[str, int] = {}
    for h in hl:
        lang, pid, ent = h["lang"], h["page_id"], h["entity_id"]
        if lang not in by_id:
            errs.append(f"{ent}: неизвестный lang {lang}")
            continue
        row = by_id[lang].get(pid)
        if not row or not is_page(row):
            errs.append(f"{ent}: page_id {pid} не страница карты {lang}")
            continue
        if "{" in row["url"]:
            expected = {row["entity_id"].replace("{card_id}", c["card_id"]): card_url(row["url"], c) for c in cards}
            if ent not in expected:
                errs.append(f"{ent}: entity_id не из шаблона {row['entity_id']} строки {pid} или карты нет в cards.csv")
            elif h["url"] != expected[ent]:
                errs.append(f"{ent}: url {h['url']} не как шаблон {pid}, развёрнутый по карте: {expected[ent]}")
        else:
            if ent != row["entity_id"]:
                errs.append(f"{ent}: entity_id не как в карте у {pid} ({row['entity_id'] or '—'})")
            if h["url"] != row["url"]:
                errs.append(f"{ent}: url {h['url']} не как в карте у {pid} ({row['url'] or '—'})")
        if (ent, lang) in by_entity:
            errs.append(f"{ent}: две строки на язык {lang}")
        by_entity[(ent, lang)] = h
        per_page[pid] = per_page.get(pid, 0) + 1
        errs += [f"{ent}: {e}" for e in url_errors(h["url"], lang)]
        if "{" in h["url"] or "#" in h["url"]:
            errs.append(f"{ent}: адрес не развёрнут: {h['url']}")
        if h["wave"] != row["wave"]:
            errs.append(f"{ent}: wave {h['wave']} не как в карте ({row['wave']})")
        if h["template"] != row["page_type"]:
            errs.append(f"{ent}: template {h['template']} не как page_type карты")
        if h["status"] not in ("planned", "published"):
            errs.append(f"{ent}: неизвестный status {h['status']}")
        if h["in_hreflang"] not in ("yes", "no"):
            errs.append(f"{ent}: in_hreflang должно быть yes или no")
        urls[lang][h["url"]] = h
    for (ent, lang), h in by_entity.items():
        other = "es" if lang == "en" else "en"
        pair = by_entity.get((ent, other))
        w = WAVE_ORDER[h["wave"]]
        if h["in_hreflang"] == "yes":
            if h["status"] != "published" or not pair or pair["status"] != "published":
                errs.append(f"{ent} ({lang}): в hreflang без опубликованной пары")
        target = urls[other].get(h["switch_to"])
        if not target:
            errs.append(f"{ent} ({lang}): switch_to {h['switch_to'] or '—'} не адрес из таблицы {other}")
        elif WAVE_ORDER[target["wave"]] > w:
            errs.append(f"{ent} ({lang}): switch_to ведёт на страницу более поздней волны")
        if pair and WAVE_ORDER[pair["wave"]] <= w and h["switch_to"] != pair["url"]:
            errs.append(f"{ent} ({lang}): switch_to должен вести на пару {pair['url']}")
    for lang, rows in maps.items():
        for r in rows:
            if is_page(r) and r["entity_id"] and WAVE_ORDER[r["wave"]] <= 1:
                need = len(cards) if "{" in r["url"] else 1
                if per_page.get(r["id"], 0) != need:
                    errs.append(f"{r['id']}: в hreflang {per_page.get(r['id'], 0)} строк, нужно {need}")
    launch = {e for (e, l), h in by_entity.items() if l == "en" and h["wave"] == "запуск"
              and by_entity.get((e, "es"), {}).get("wave") == "запуск"}
    if len(launch) != launch_clusters:
        errs.append(f"кластеров запуска {len(launch)}, ожидалось {launch_clusters}")
    return errs
