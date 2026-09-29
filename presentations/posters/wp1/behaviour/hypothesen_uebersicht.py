"""One-page overview: each WP1 hypothesis, its current verdict, and its figure."""
import textwrap
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

D = "/Users/simonknogler/Downloads/CDT_Publikationsabbildungen"
INK, INK2, MUTED, RULE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
mpl.rcParams.update({"font.family": "sans-serif",
                     "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "pdf.fonttype": 42})
# verdict badge: status colour + label (never colour alone); label ink chosen by fill luminance
BADGE = {"ok": ("#0ca30c", "white"), "partial": ("#fab219", INK),
         "none": ("#898781", "white"), "confound": ("#ec835a", INK)}

rows = [
    ("VORAUSSETZUNG", "Manipulation greift", "ok", "erfüllt",
     ["Medium-Trials: 0,70–0,72 in allen vier Zellen (Ziel 70,7 %)",
      "Cue-Lernen: 0,95 vs. 0,47 bei 0°, 0,94 vs. 0,50 bei 90°",
      "Schwierigkeitsstufen trennen sich: 0,49 / 0,71 / 0,97"],
     "fig2_manipulation_checks.png"),
    ("H1a · Zwischenbericht", "Erwartung verschiebt das Erleben, nicht die Leistung", "ok", "gestützt",
     ["Cue-Effekt Agency: F(1,11) = 6,44, p = .028, ηp² = .37",
      "Konfidenz: F(1,11) = 10,27, p = .008, ηp² = .48",
      "Genauigkeit: F(1,11) = 0,57, p = .47 – unverändert"],
     "fig3_expectation_by_rotation.png"),
    ("H1b · Antrag", "Stärkerer Erwartungseffekt im regularitätsbasierten Modus (90°)", "partial",
     "Richtung stimmt · n.s.",
     ["90°: Agency +0,51 (p = .035), Konfidenz +0,26 (p = .046)",
      "0°: kein Effekt (−0,07 / −0,06), kein Einbruch",
      "Interaktion: Agency p = .082, Konfidenz p = .110",
      "dz = 0,55: für 80 % Power braucht es ca. 28 Personen"],
     "fig4_cue_effect_per_participant.png"),
    ("H2 · Antrag", "Metakognition besser bei 90° (meta-d′)", "none", "kein Hinweis",
     ["M-Ratio 0,76 (0°) vs. 0,77 (90°)",
      "Δ log M = −0,02 [−0,36; +0,31], P(Δ > 0) = .45",
      "Spricht weder für noch gegen H2"],
     "fig6_metacognition.png"),
    ("H3 · P3 · Antrag", "Verletzung hoher Erwartung wirkt stärker, v. a. bei 0°", "confound",
     "nicht interpretierbar",
     ["Asymmetrie groß und bei 0° größer (+2,50 vs. +1,87)",
      "Aber: objektive Kontrollschritte ungleich (0,36 vs. 0,21)",
      "Trennbar nur mit inkongruenten Trials – gibt es in v1 nicht"],
     "fig5_violation_asymmetry.png"),
]

fig = plt.figure(figsize=(8.27, 11.69))
H = [0.8] + [2.05] * len(rows) + [0.3]
gs = fig.add_gridspec(len(H), 2, height_ratios=H, width_ratios=[0.33, 0.67],
                      left=0.05, right=0.97, top=0.975, bottom=0.015, hspace=0.14, wspace=0.03)

hd = fig.add_subplot(gs[0, :]); hd.axis("off")
hd.text(0, 0.80, "CDT · Arbeitspaket 1 — Hypothesen-Übersicht", fontsize=15, fontweight="bold",
        color=INK, transform=hd.transAxes, va="top")
hd.text(0, 0.36, "Stand 15.09.2026 · N = 12 eingeschlossen (13 erhoben, P13 per Lern-Check ausgeschlossen, "
        "P9 fehlt) · 11 × Design v1, 1 × v2 (P14)", fontsize=7.8, color=INK2, transform=hd.transAxes, va="top")
hd.text(0, 0.10, "Statistik: 2 × 2-ANOVA mit Messwiederholung auf Personenebene (Analyseplan des Antrags) · "
        "Abbildungen: Blau = 0°, Orange = 90°", fontsize=7.8, color=INK2, transform=hd.transAxes, va="top")

for i, (tag, title, kind, label, lines, img) in enumerate(rows, start=1):
    y_top = gs[i, 0].get_position(fig).y1
    fig.add_artist(plt.Line2D([0.05, 0.97], [y_top + 0.007] * 2, color=RULE, lw=0.8,
                              transform=fig.transFigure))
    ta = fig.add_subplot(gs[i, 0]); ta.axis("off")
    ta.text(0, 0.98, tag, fontsize=7.5, fontweight="bold", color=MUTED, va="top", transform=ta.transAxes)
    t = textwrap.fill(title, 33)
    ta.text(0, 0.88, t, fontsize=9.8, fontweight="bold", color=INK, va="top",
            transform=ta.transAxes, linespacing=1.25)
    y = 0.88 - 0.085 * (t.count("\n") + 1) - 0.05
    bg, fg = BADGE[kind]
    ta.text(0.012, y, label, fontsize=7.5, fontweight="bold", color=fg, va="top", transform=ta.transAxes,
            bbox=dict(boxstyle="round,pad=0.35", fc=bg, ec="none"))
    y -= 0.15
    for ln in lines:
        w = textwrap.fill(ln, 45)
        ta.text(0, y, w, fontsize=7.3, color=INK2, va="top", transform=ta.transAxes, linespacing=1.3)
        y -= 0.062 * (w.count("\n") + 1) + 0.03
    ia = fig.add_subplot(gs[i, 1]); ia.axis("off")
    ia.imshow(mpimg.imread(f"{D}/{img}"), interpolation="lanczos")

ft = fig.add_subplot(gs[-1, :]); ft.axis("off")
ft.text(0, 0.5, "Nicht enthalten: DDM-Hypothesen (HSSM-Fit steht aus) · Fig. 1 (Paradigma) muss neu "
        "gezeichnet werden · Details: stats.md, captions.md", fontsize=7, color=MUTED,
        transform=ft.transAxes, va="center")

fig.savefig(f"{D}/Hypothesen_Uebersicht.pdf")
fig.savefig(f"{D}/Hypothesen_Uebersicht.png", dpi=170)
print("wrote Hypothesen_Uebersicht.pdf/.png")
