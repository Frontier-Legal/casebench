"""Six decisions in three languages and two layouts, and what two models read in each.

The German decision states its ruling first (Tenor), the others last, so nothing may assume
where a ruling sits. Model B disagrees on purpose: another outcome for tr-2, an extra statute
for en-1. Model A's facts for en-2 give the ruling away.
"""

DECISIONS = {
    "tr-1": (
        "TR",
        "Yargıtay 9. Hukuk Dairesi",
        "appellate",
        "2024-03-12",
        "Davacı işçi feshin geçersiz olduğunu ileri sürmüştür. 4857 sayılı İş Kanunu m. 18 "
        "uyarınca fesih geçerli sebebe dayanmalıdır. Yargıtay 9. HD E. 2019/1 K. 2020/2 "
        "kararı da bu yöndedir. HÜKÜM: Kararın bozulmasına.",
    ),
    "tr-2": (
        "TR",
        "Yargıtay Hukuk Genel Kurulu",
        "supreme",
        "2025-06-01",
        "Davacı kıdem tazminatı istemiştir. 1475 sayılı Kanun m. 14 uygulanır. "
        "HGK E. 2018/5 K. 2019/6 kararı emsaldir. HÜKÜM: Kararın onanmasına.",
    ),
    "tr-3": (
        "TR",
        "İstanbul 3. İş Mahkemesi",
        "first_instance",
        "2022-01-01",
        "Davacı ücret alacağını talep etmiştir. 4857 sayılı İş Kanunu m. 32 ücretin "
        "ödenmesini düzenler. HÜKÜM: Davanın kabulüne.",
    ),
    "de-1": (
        "DE",
        "Bundesgerichtshof",
        "supreme",
        "2025-02-01",
        "Tenor: Die Revision wird zurückgewiesen. Tatbestand: Die Klägerin verlangt "
        "Schadensersatz. Entscheidungsgründe: Nach § 626 BGB war die Kündigung wirksam, "
        "wie schon BGH VI ZR 1/19 entschieden hat.",
    ),
    "en-1": (
        "GB",
        "Court of Appeal",
        "appellate",
        "2023-05-05",
        "The employee says the dismissal was unfair. Section 98 of the Employment Rights "
        "Act 1996 governs fairness, and section 94 gives the right not to be unfairly "
        "dismissed. Following Polkey v AE Dayton Services [1987] UKHL 8, the appeal is "
        "allowed.",
    ),
    "en-2": (
        "GB",
        "Employment Tribunal",
        "first_instance",
        "2025-09-09",
        "The claimant sought holiday pay. Regulation 13 of the Working Time Regulations "
        "1998 applies. The claim is dismissed.",
    ),
}


def reading(outcome, outcome_quote, statutes, precedents, facts):
    return {
        "outcome": {"label": outcome, "quote": outcome_quote},
        "statutes": [{"citation": c, "quote": q} for c, q in statutes],
        "precedents": [{"citation": c, "quote": q} for c, q in precedents],
        "facts": facts,
    }


MODEL_A = {
    "tr-1": reading(
        "reversed",
        "HÜKÜM: Kararın bozulmasına.",
        [("4857/18", "4857 sayılı İş Kanunu m. 18")],
        [("Yargıtay 9. HD E. 2019/1 K. 2020/2", "Yargıtay 9. HD E. 2019/1 K. 2020/2")],
        "İşçi, feshin geçersizliğini ve işe iadesini istiyor.",
    ),
    "tr-2": reading(
        "upheld",
        "HÜKÜM: Kararın onanmasına.",
        [("1475/14", "1475 sayılı Kanun m. 14")],
        [("HGK E. 2018/5 K. 2019/6", "HGK E. 2018/5 K. 2019/6")],
        "İşçi kıdem tazminatı istiyor.",
    ),
    "tr-3": reading(
        "granted",
        "HÜKÜM: Davanın kabulüne.",
        [("4857/32", "4857 sayılı İş Kanunu m. 32")],
        [],
        "İşçi ödenmeyen ücretini istiyor.",
    ),
    "de-1": reading(
        "dismissed",
        "Die Revision wird zurückgewiesen.",
        [("§ 626 BGB", "§ 626 BGB")],
        [("BGH VI ZR 1/19", "BGH VI ZR 1/19")],
        "Die Klägerin verlangt Schadensersatz nach einer Kündigung.",
    ),
    "en-1": reading(
        "reversed",
        "the appeal is allowed",
        [("ERA 1996 s 98", "Section 98 of the Employment Rights Act 1996")],
        [
            (
                "Polkey v AE Dayton Services [1987] UKHL 8",
                "Polkey v AE Dayton Services [1987] UKHL 8",
            )
        ],
        "An employee challenges a dismissal as unfair.",
    ),
    "en-2": reading(
        "rejected",
        "The claim is dismissed.",
        [("WTR 1998 reg 13", "Regulation 13 of the Working Time Regulations 1998")],
        [],
        "The claimant sought holiday pay. The claim is dismissed.",
    ),
}

MODEL_B = {
    **MODEL_A,
    "tr-2": {
        **MODEL_A["tr-2"],
        "outcome": {"label": "reversed", "quote": "HÜKÜM: Kararın onanmasına."},
    },
    "en-1": {
        **MODEL_A["en-1"],
        "statutes": MODEL_A["en-1"]["statutes"]
        + [
            {
                "citation": "ERA 1996 s 94",
                "quote": "section 94 gives the right not to be unfairly dismissed",
            }
        ],
    },
}
