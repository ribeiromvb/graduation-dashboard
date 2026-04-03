import base64
import io
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Graduation Report",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme / CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* overall background */
[data-testid="stAppViewContainer"] { background: #f4f6fb; }
[data-testid="stHeader"]           { background: transparent; }

/* card containers */
.card {
    background: white;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    height: 100%;
}
.card-title {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .6px;
    color: #1f3864;
    margin-bottom: 12px;
    border-bottom: 2px solid #e8eef6;
    padding-bottom: 8px;
}

/* metric tiles */
.metric-tile {
    background: #1f3864;
    border-radius: 10px;
    padding: 18px 22px;
    color: white;
    text-align: center;
}
.metric-tile .value { font-size: 34px; font-weight: 700; line-height: 1.1; }
.metric-tile .label { font-size: 12px; opacity: .8; margin-top: 4px; }

/* page header / banner */
.banner {
    background: #000000;
    border-radius: 10px;
    padding: 0;
    margin-bottom: 8px;
    display: flex;
    align-items: stretch;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,.25);
}
.banner-text {
    padding: 14px 24px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-end;
    text-align: right;
    flex: 1;
}
.banner-text .dept {
    font-size: 19px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: .3px;
    line-height: 1.2;
}
.banner-divider { display: none; }
.banner-logo {
    background: #000000;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.banner-logo img {
    height: 72px;
    width: auto;
    display: block;
}
/* report title below banner */
.report-title {
    text-align: center;
    font-size: 26px;
    font-weight: 700;
    color: #1f3864;
    margin: 10px 0 20px 0;
    letter-spacing: .2px;
}

/* table styling */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #1f3864; color: white; padding: 8px 12px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: .4px; }
td { padding: 7px 12px; border-bottom: 1px solid #f0f2f7; color: #333; }
tr:last-child td { font-weight: 700; background: #d9e2f0; }
tr:hover td { background: #f7f9fd; }

/* tracking table */
.track-table { font-size: 14px; }
.track-table th { background: #1f3864; text-align: center; }
.track-table td { text-align: center; font-weight: 700; }
.track-table td.cohort-label { font-weight: 700; text-align: center; background: #d9e2f0; }
.track-table tr:last-child td { background: white; }
.track-table tr:last-child td.cohort-label { background: #d9e2f0; }
.track-table tr:last-child td.track-diagonal { background: #f9d0c0; }
.track-pct  { font-size: 13px; color: #2e75b6; font-weight: 700; }
.track-null { color: #bbb; font-style: italic; }
.track-empty    { background: #d9e2f0; }
.track-diagonal { background: #f9d0c0; }

/* chart title (no box) */
.chart-title {
    text-align: center;
    font-size: 16px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .6px;
    color: #1f3864;
    margin-top: 24px;
    margin-bottom: 4px;
}

div[data-testid="stTabs"] button { font-size: 14px; font-weight: 600; color: #1f3864 !important; }
div[data-testid="stTabs"] button:hover { color: #2e75b6 !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #1f3864 !important; border-bottom: 3px solid #1f3864; }

/* sidebar export button */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background-color: #2e75b6 !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background-color: #1f3864 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    path = Path(__file__).parent / "data" / "data.json"
    with open(path) as f:
        return json.load(f)

data = load_data()
semesters = data["semesters"]
history_raw = data["completion_history"]

# ── Shared colors ─────────────────────────────────────────────────────────────
NAVY   = "#1f3864"
BLUE   = "#2e75b6"
LTBLUE = "#a9c4e0"
GREEN  = "#70ad47"
ORANGE = "#ffc000"
RED    = "#c00000"
GRAY   = "#d0d0d0"

# ── PDF export ────────────────────────────────────────────────────────────────
def build_pdf(sem, semester_key, term_label, history_raw, logo_path):
    """Generate a 3-page graduation report PDF. Returns bytes."""
    from fpdf import FPDF

    def rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def fig_png(fig, w=800, h=350):
        buf = io.BytesIO()
        fig.write_image(buf, format='png', width=w, height=h, scale=2)
        buf.seek(0)
        return buf

    M  = 12
    UW = 279 - 2*M   # 255mm usable (landscape Letter)
    CN = rgb(NAVY)
    G3 = 4
    G2 = 4

    pdf = FPDF(orientation='L', unit='mm', format='Letter')
    pdf.set_auto_page_break(auto=False)

    # ── shared helpers ─────────────────────────────────────────────────────────
    def draw_banner():
        y = pdf.get_y()
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(M, y, UW, 18, style='F')
        pdf.image(str(logo_path), x=M+2, y=y+1, h=16)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(M, y)
        pdf.cell(UW-3, 18, 'Student Records & Registration', align='R')
        pdf.set_y(y + 20)

    def draw_titles(section):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*CN)
        pdf.set_x(M)
        pdf.cell(UW, 7, f'Credential Application Tracking - {term_label}', align='C', ln=True)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_x(M)
        pdf.cell(UW, 5, section.upper(), align='C', ln=True)
        pdf.ln(2)

    def draw_tiles(tiles):
        TW = (UW - (len(tiles)-1)*3) / len(tiles)
        TH = 16
        y  = pdf.get_y()
        for i, (val, lbl) in enumerate(tiles):
            x = M + i*(TW+3)
            pdf.set_fill_color(*CN)
            pdf.rect(x, y, TW, TH, style='F')
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.set_xy(x, y+1.5)
            pdf.cell(TW, 6, str(val), align='C')
            pdf.set_font('Helvetica', '', 7)
            pdf.set_xy(x, y+8.5)
            pdf.cell(TW, 5, str(lbl), align='C')
        pdf.set_y(y + TH + 3)

    def ctitle(text, x, w):
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*CN)
        pdf.set_xy(x, pdf.get_y())
        pdf.cell(w, 5, text.upper(), align='C')

    def card_table(x, y, w, title, hdrs, rows, ratios=None):
        ROW_H = 5.5
        HDR_H = 6
        TTL_H = 8
        if ratios is None:
            ratios = [1/len(hdrs)] * len(hdrs)
        cws = [r*(w-4) for r in ratios]
        total_h = TTL_H + HDR_H + len(rows)*ROW_H + 2
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(220, 220, 220)
        pdf.rect(x, y, w, total_h, style='FD')
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*CN)
        pdf.set_xy(x+2, y+1.5)
        pdf.cell(w-4, 5, title.upper(), border='B')
        hx = x+2
        pdf.set_fill_color(*CN)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 7.5)
        for ht, cw in zip(hdrs, cws):
            pdf.set_xy(hx, y+TTL_H)
            pdf.cell(cw, HDR_H, ht, fill=True)
            hx += cw
        for ri, row in enumerate(rows):
            ry = y + TTL_H + HDR_H + ri*ROW_H
            rx = x+2
            is_tot = ri == len(rows)-1
            if is_tot:
                pdf.set_fill_color(*rgb('#d9e2f0'))
                pdf.set_font('Helvetica', 'B', 7.5)
            elif ri % 2 == 0:
                pdf.set_fill_color(255, 255, 255)
                pdf.set_font('Helvetica', '', 7.5)
            else:
                pdf.set_fill_color(247, 249, 253)
                pdf.set_font('Helvetica', '', 7.5)
            pdf.set_text_color(51, 51, 51)
            for cv, cw in zip(row, cws):
                pdf.set_xy(rx, ry)
                pdf.cell(cw, ROW_H, str(cv), fill=True)
                rx += cw
        return total_h

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — Credential Overview
    # ═══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    draw_banner()
    draw_titles('Credential Overview')

    app_sum     = sem["application_summary"]
    total_apps  = app_sum["Applications"]
    total_grad  = app_sum["Graduated"]
    grad_rate   = total_grad / total_apps
    total_creds = sum(sem["credential_types"].values())

    draw_tiles([
        (f"{total_apps:,}",            f"{semester_key} Total Applications"),
        (f"{total_creds:,}",           f"{semester_key} Credentials Awarded"),
        (f"{grad_rate:.1%}",           f"{semester_key} Graduation Rate"),
        (f"{app_sum['Incomplete']:,}", f"{semester_key} Incomplete"),
    ])

    CW3 = (UW - 2*G3) / 3
    CH  = 52
    cy  = pdf.get_y()
    xs  = [M, M+CW3+G3, M+2*(CW3+G3)]

    cred   = sem["credential_types"]
    counts = list(app_sum.values())

    fig_cred = go.Figure(go.Pie(
        labels=list(cred.keys()), values=list(cred.values()), hole=0.55,
        marker_colors=[NAVY, BLUE, LTBLUE], textposition="outside",
        texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
        textfont=dict(size=16, color="#333333"), automargin=True,
    ))
    fig_cred.update_layout(
        annotations=[dict(text=f"<b>{sum(cred.values()):,}</b><br>Awarded",
                          x=0.5, y=0.5, font_size=15, showarrow=False)],
        showlegend=False, margin=dict(t=30, b=30, l=15, r=15),
        height=380, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )

    fig_apps = go.Figure(go.Bar(
        x=counts, y=list(app_sum.keys()), orientation="h",
        marker_color=[NAVY, GREEN, ORANGE, RED],
        text=[f"<b>{v:,}</b>" for v in counts],
        textposition="outside", textfont=dict(size=15, color="#333333"),
    ))
    fig_apps.update_layout(
        xaxis=dict(visible=False, range=[0, max(counts)*1.45]),
        yaxis=dict(autorange="reversed",
                   ticktext=[f"<b>{c}</b>   " for c in app_sum.keys()],
                   tickvals=list(app_sum.keys()),
                   tickfont=dict(size=13, color="#333333")),
        bargap=0.35, margin=dict(t=20, b=20, l=130, r=20),
        height=300, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )
    fig_apps.add_annotation(
        x=app_sum["Other"]+700, y="Other",
        ax=max(counts)*0.50, ay=40, axref="x", ayref="pixel",
        text="<b>Includes:</b><br>• Withdraw<br>• Moved to new semester<br>• Rejected<br>• Duplicated",
        showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor="#666666",
        font=dict(size=11, color="#333333"), align="left",
        bgcolor="rgba(255,255,255,0.92)", bordercolor="#aaaaaa",
        borderwidth=1, borderpad=7,
    )

    hld = sem["holds"]
    fig_holds = go.Figure(go.Pie(
        labels=list(hld.keys()), values=list(hld.values()), hole=0.55,
        marker_colors=[GREEN, "#c0504d"], textposition="outside",
        texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
        textfont=dict(size=16, color="#333333"), automargin=True,
    ))
    fig_holds.update_layout(
        annotations=[dict(text=f"<b>{hld['Holds']:,}</b><br>with Holds",
                          x=0.5, y=0.5, font_size=15, showarrow=False)],
        showlegend=False, margin=dict(t=30, b=30, l=15, r=15),
        height=380, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )

    CH_PDF = round(CW3 * (500/700), 1)  # consistent height for all charts
    for i, (fig, title) in enumerate([
        (fig_cred,  'Awarded by Credential Type'),
        (fig_apps,  f'{term_label} Degree Applications'),
        (fig_holds, 'Graduated with Holds'),
    ]):
        ctitle(title, xs[i], CW3)
        pdf.image(fig_png(fig, w=700, h=500), x=xs[i], y=cy+5, w=CW3, h=CH_PDF)

    pdf.set_y(cy + 5 + CH_PDF + 6)

    ty = pdf.get_y()
    TW2 = (UW - G2) / 2

    reasons  = sem["incomplete_reasons"]
    tot_inc  = sum(reasons.values())
    inc_rows = [[c, str(n), f"{n/tot_inc:.1%}"] for c, n in reasons.items()]
    inc_rows.append(["Total", str(tot_inc), "100.0%"])
    card_table(M, ty, TW2, f"{term_label} Incomplete Reasons",
               ["Category", "Count", "Rate"], inc_rows, [0.6, 0.2, 0.2])

    codes     = sem["hold_codes"]
    tot_holds = sum(codes.values())
    hold_rows = [[c, str(n), f"{n/tot_holds:.1%}"] for c, n in codes.items()]
    hold_rows.append(["Total", str(tot_holds), "100.0%"])
    card_table(M+TW2+G2, ty, TW2, f"{term_label} Graduates with Holds",
               ["Hold Code", "Count", "Rate"], hold_rows, [0.6, 0.2, 0.2])

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Certificate Award Details
    # ═══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    draw_banner()
    draw_titles('Certificate Award Details')

    ca          = sem["certificate_auto_award"]
    auto_day    = ca["auto_day"]
    auto_onln   = ca["auto_onln"]
    stu_applied = ca["student_applied"]
    cert_inc    = ca["incomplete"]
    auto_tot    = auto_day + auto_onln
    cert_tot    = auto_tot + stu_applied
    auto_rate   = auto_tot / cert_tot

    draw_tiles([
        (f"{cert_tot:,}",      f"{semester_key} Certificates Awarded"),
        (f"{auto_tot:,}",      f"{semester_key} Auto-Awarded"),
        (f"{auto_rate:.1%}",   f"{semester_key} Auto-Award Rate"),
        (f"{cert_inc:,}",      f"{semester_key} Incomplete"),
    ])

    d_lbl = ["Auto-Award (DAY)", "Auto-Award (ONLN)", "Student-Applied"]
    d_val = [auto_day, auto_onln, stu_applied]

    fig_donut = go.Figure(go.Pie(
        labels=d_lbl, values=d_val, hole=0.55,
        marker_colors=[NAVY, BLUE, GREEN], textposition="outside",
        texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
        textfont=dict(size=16, color="#333333"), automargin=True,
    ))
    fig_donut.update_layout(
        annotations=[dict(text=f"<b>{cert_tot:,}</b><br>Awarded",
                          x=0.5, y=0.5, font_size=15, showarrow=False)],
        showlegend=False, margin=dict(t=30, b=30, l=15, r=15),
        height=380, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )

    fig_cbar = go.Figure(go.Bar(
        x=d_val, y=d_lbl, orientation="h",
        marker_color=[NAVY, BLUE, GREEN],
        text=[f"<b>{v:,}</b>" for v in d_val],
        textposition="outside", textfont=dict(size=15, color="#333333"),
    ))
    fig_cbar.update_layout(
        xaxis=dict(visible=False, range=[0, max(d_val)*1.45]),
        yaxis=dict(autorange="reversed",
                   ticktext=[f"<b>{l}</b>   " for l in d_lbl],
                   tickvals=d_lbl,
                   tickfont=dict(size=12, color="#333333")),
        bargap=0.35, margin=dict(t=20, b=20, l=180, r=20),
        height=300, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )

    cert_y = pdf.get_y()
    CCW    = (UW*0.65 - G3) / 2
    TW_c   = UW - 2*CCW - 2*G3

    ctitle('Award Source Breakdown', M, CCW)
    ctitle(f'{term_label} Certificate Awards', M+CCW+G3, CCW)
    CCH_PDF = round(CCW * (500/700), 1)
    pdf.image(fig_png(fig_donut, w=700, h=500), x=M,        y=cert_y+5, w=CCW, h=CCH_PDF)
    pdf.image(fig_png(fig_cbar,  w=700, h=500), x=M+CCW+G3, y=cert_y+5, w=CCW, h=CCH_PDF)

    tx = M + 2*CCW + 2*G3
    cert_bkdn = [
        ["Auto-Award (DAY)",  f"{auto_day:,}",  f"{auto_day/cert_tot:.1%}"],
        ["Auto-Award (ONLN)", f"{auto_onln:,}",  f"{auto_onln/cert_tot:.1%}"],
        ["Student-Applied",   f"{stu_applied:,}", f"{stu_applied/cert_tot:.1%}"],
        ["Total Awarded",     f"{cert_tot:,}",   "100.0%"],
    ]
    cert_th = card_table(tx, cert_y+5, TW_c, f"{term_label} Certificate Breakdown",
                         ["Category", "Count", "% Awarded"], cert_bkdn, [0.5, 0.25, 0.25])

    inc_y = cert_y + 5 + cert_th + 3
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(220, 220, 220)
    pdf.rect(tx, inc_y, TW_c, 13, style='FD')
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_text_color(*CN)
    pdf.set_xy(tx+2, inc_y+1.5)
    pdf.cell(TW_c-4, 4, 'INCOMPLETE (NOT AWARDED)', border='B')
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(51, 51, 51)
    pdf.set_xy(tx+2, inc_y+7)
    pdf.cell(TW_c-4, 5, f"{cert_inc:,} applications")

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — Graduation Rate History
    # ═══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    draw_banner()
    draw_titles('Graduation Rate - History')

    tracking = sem["tracking"]
    cohorts  = tracking["cohorts"]
    censuses = tracking["censuses"]
    cells    = tracking["cells"]

    col0w = 16
    colw  = (UW - 4 - col0w) / len(censuses)
    trk_rows_data = []
    for cohort in cohorts:
        cd  = cells.get(cohort, {})
        row = [cohort]
        for census in censuses:
            cv = cd.get(census)
            if cv is None:
                nt = (census=="SP25" and cohort!="FA25") or (cohort=="FA24" and census=="WI25")
                row.append("not tracked" if nt else "-")
            elif cv == "in progress":
                row.append("in progress")
            else:
                comp, appl = cv
                row.append((f"{comp:,} / {appl:,}", f"{comp/appl:.1%}"))
        trk_rows_data.append(row)

    TRK_TTL_H = 8
    TRK_HDR_H = 6
    TRK_ROW_H = 11
    trk_h = TRK_TTL_H + TRK_HDR_H + len(trk_rows_data)*TRK_ROW_H + 2
    trk_y = pdf.get_y()

    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(220, 220, 220)
    pdf.rect(M, trk_y, UW, trk_h, style='FD')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*CN)
    pdf.set_xy(M+2, trk_y+1.5)
    pdf.cell(UW-4, 5, 'APPLICATION TRACKING OVER 4 TERMS', border='B')

    hx = M+2
    pdf.set_fill_color(*CN)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    for htxt, cw in zip(["Cohort"]+censuses, [col0w]+[colw]*len(censuses)):
        pdf.set_xy(hx, trk_y+TRK_TTL_H)
        pdf.cell(cw, TRK_HDR_H, htxt, fill=True, align='C')
        hx += cw

    for ri, row_data in enumerate(trk_rows_data):
        ry         = trk_y + TRK_TTL_H + TRK_HDR_H + ri*TRK_ROW_H
        cohort_val = row_data[0]
        rx = M+2
        for ci, (cv, cw) in enumerate(zip(row_data, [col0w]+[colw]*len(censuses))):
            census_v = censuses[ci-1] if ci > 0 else None
            is_diag  = ci > 0 and cohort_val == census_v
            if ci == 0:
                pdf.set_fill_color(*rgb('#d9e2f0'))
                pdf.set_font('Helvetica', 'B', 8)
            elif is_diag:
                pdf.set_fill_color(*rgb('#f9d0c0'))
                pdf.set_font('Helvetica', 'B', 8)
            elif cv == "-":
                pdf.set_fill_color(*rgb('#d9e2f0'))
                pdf.set_font('Helvetica', '', 7)
            else:
                pdf.set_fill_color(255, 255, 255)
                pdf.set_font('Helvetica', '', 7.5)
            pdf.set_text_color(51, 51, 51)
            if isinstance(cv, tuple):
                line1, line2 = cv
                lh = TRK_ROW_H / 2
                pdf.set_xy(rx, ry)
                pdf.cell(cw, lh, line1, fill=True, align='C')
                pdf.set_font('Helvetica', 'B', 7.5)
                pdf.set_text_color(*rgb(BLUE))
                pdf.set_xy(rx, ry + lh)
                pdf.cell(cw, lh, line2, fill=True, align='C')
                pdf.set_text_color(51, 51, 51)
            else:
                pdf.set_xy(rx, ry)
                pdf.cell(cw, TRK_ROW_H, str(cv), fill=True, align='C')
            rx += cw

    pdf.set_y(trk_y + trk_h + 3)

    df = pd.DataFrame(history_raw)
    df["total"]           = df["completed"] + df["expired"]
    df["completion_rate"] = df["completed"] / df["total"]
    df["expired_rate"]    = df["expired"]   / df["total"]

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(
        x=df["term"], y=df["completed"], name="Completed",
        marker_color=BLUE,
        text=[f"{r:.1%}" for r in df["completion_rate"]],
        textposition="inside", textfont=dict(size=10, color="white"),
    ))
    fig_hist.add_trace(go.Bar(
        x=df["term"], y=df["expired"], name="Expired",
        marker_color=ORANGE,
        text=[f"{r:.1%}" for r in df["expired_rate"]],
        textposition="outside", textfont=dict(size=10, color="#333333"),
    ))
    fig_hist.update_layout(
        barmode="stack",
        yaxis=dict(gridcolor="#eef0f5", tickfont=dict(size=11, color="#333333")),
        xaxis=dict(tickangle=-45, tickfont=dict(size=11, color="#333333")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
                    font=dict(size=11, color="#333333")),
        showlegend=True,
        margin=dict(t=20, b=70, l=20, r=20),
        height=340, paper_bgcolor="white", font=dict(family="Segoe UI,sans-serif"),
    )

    hist_y = pdf.get_y()
    CHW    = UW * 0.60
    HTW    = UW - CHW - G3
    HIST_H = 60

    ctitle('Complete and Expired Rate History', M, CHW)
    pdf.image(fig_png(fig_hist, w=900, h=400), x=M, y=hist_y+5, w=CHW, h=round(CHW*(400/900), 1))

    hist_rows = []
    for _, r in df.iterrows():
        hist_rows.append([r['term'], f"{int(r['completed']):,}", f"{r['completion_rate']:.1%}",
                          f"{int(r['expired']):,}", f"{r['expired_rate']:.1%}"])
    tc = int(df["completed"].sum())
    te = int(df["expired"].sum())
    ta = int(df["total"].sum())
    hist_rows.append(["Total", f"{tc:,}", f"{tc/ta:.1%}", f"{te:,}", f"{te/ta:.1%}"])
    card_table(M+CHW+G3, hist_y, HTW, "Complete & Expired Rate History",
               ["Term", "Completed", "Rate", "Expired", "Exp. Rate"],
               hist_rows, [0.18, 0.22, 0.18, 0.22, 0.2])

    return bytes(pdf.output())


# ── Sidebar ───────────────────────────────────────────────────────────────────
_logo_path = Path(__file__).parent / "byui_logo.png"

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    semester_key = st.selectbox(
        "Semester",
        options=list(semesters.keys()),
        format_func=lambda k: semesters[k]["label"],
    )
    st.markdown("---")
    if st.button("📄 Generate PDF Report"):
        with st.spinner("Building PDF..."):
            _pdf_bytes = build_pdf(
                semesters[semester_key],
                semester_key,
                semesters[semester_key]["label"],
                data["completion_history"],
                _logo_path,
            )
        st.download_button(
            label="⬇️ Download PDF",
            data=_pdf_bytes,
            file_name=f"Graduation_Report_{semester_key}.pdf",
            mime="application/pdf",
        )

sem = semesters[semester_key]
term_label = sem["label"]

DONUT_HOLE = 0.55
CHART_MARGIN = dict(t=10, b=10, l=10, r=10)
CHART_HEIGHT = 280

def chart_layout(fig, height=CHART_HEIGHT):
    fig.update_layout(
        margin=CHART_MARGIN,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, sans-serif", size=12, color="#333333"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.3,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#333333"),
        ),
        showlegend=False,
    )
    return fig

# ── Banner ────────────────────────────────────────────────────────────────────
_logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()

st.markdown(f"""
<div class="banner">
  <div class="banner-logo">
    <img src="data:image/png;base64,{_logo_b64}" alt="BYU-Idaho logo">
  </div>
  <div class="banner-text">
    <span class="dept">Student Records &amp; Registration</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="report-title">Credential Application Tracking &mdash; {term_label}</div>', unsafe_allow_html=True)

# ── Metric tiles ──────────────────────────────────────────────────────────────
app_sum = sem["application_summary"]
total_apps  = app_sum["Applications"]
total_grad  = app_sum["Graduated"]
grad_rate   = total_grad / total_apps
total_creds = sum(sem["credential_types"].values())
holds_count = sem["holds"]["Holds"]

m1, m2, m3, m4 = st.columns(4)
for col, val, label in [
    (m1, f"{total_apps:,}",            f"{semester_key} Total Applications"),
    (m2, f"{total_creds:,}",           f"{semester_key} Credentials Awarded"),
    (m3, f"{grad_rate:.1%}",           f"{semester_key} Graduation Rate"),
    (m4, f"{app_sum['Incomplete']:,}", f"{semester_key} Incomplete"),
]:
    col.markdown(f"""
    <div class="metric-tile">
      <div class="value">{val}</div>
      <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab3, tab2 = st.tabs(["📊 Page 1 — Credential Tracking", "🎓 Page 2 — Certificate Details", "📈 Page 3 — Graduation Rate History"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="report-title">Credential Overview</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    # ── Chart 1: Awarded by Credential Type ───────────────────────────────────
    with c1:
        cred = sem["credential_types"]
        labels = list(cred.keys())
        values = list(cred.values())
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=DONUT_HOLE,
            marker_colors=[NAVY, BLUE, LTBLUE],
            textposition="outside",
            texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
            textfont=dict(size=13, color="#333333"),
            automargin=True,
        ))
        fig.update_layout(
            annotations=[dict(text=f"<b>{sum(values):,}</b><br>Awarded",
                              x=0.5, y=0.5, font_size=13, showarrow=False)],
            showlegend=False,
        )
        chart_layout(fig)
        st.markdown('<div class="chart-title">Awarded by Credential Type</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 2: Degree Applications ──────────────────────────────────────────
    with c2:
        categories = list(app_sum.keys())
        counts     = list(app_sum.values())
        colors     = [NAVY, GREEN, ORANGE, RED]
        fig = go.Figure(go.Bar(
            x=counts,
            y=categories,
            orientation="h",
            marker_color=colors,
            text=[f"<b>{v:,}</b>" for v in counts],
            textposition="outside",
            textfont=dict(size=12, color="#333333"),
        ))
        fig.update_layout(
            xaxis=dict(visible=False, range=[0, max(counts) * 1.18]),
            yaxis=dict(
                autorange="reversed",
                tickmode="array",
                tickvals=categories,
                ticktext=[f"<b>{c}</b>" for c in categories],
                tickfont=dict(size=13, color="#333333"),
            ),
            bargap=0.35,
        )
        other_count = app_sum["Other"]
        fig.add_annotation(
            x=other_count + 700, y="Other",
            ax=max(counts) * 0.50, ay=40,
            axref="x", ayref="pixel",
            text="<b>Includes:</b><br>• Withdraw<br>• Moved to new semester<br>• Rejected<br>• Duplicated",
            showarrow=True,
            arrowhead=2,
            arrowwidth=1.5,
            arrowcolor="#666666",
            font=dict(size=11, color="#333333"),
            align="left",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#aaaaaa",
            borderwidth=1,
            borderpad=7,
        )
        chart_layout(fig)
        st.markdown(f'<div class="chart-title">{term_label} Degree Applications</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 3: Graduated with Holds ────────────────────────────────────────
    with c3:
        hld = sem["holds"]
        fig = go.Figure(go.Pie(
            labels=list(hld.keys()),
            values=list(hld.values()),
            hole=DONUT_HOLE,
            marker_colors=[GREEN, "#c0504d"],
            textposition="outside",
            texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
            textfont=dict(size=13, color="#333333"),
            automargin=True,
        ))
        total_grads = sum(hld.values())
        hold_pct = hld["Holds"] / total_grads
        fig.update_layout(
            annotations=[dict(
                text=f"<b>{hld['Holds']:,}</b><br>with Holds",
                x=0.5, y=0.5, font_size=13, showarrow=False,
            )],
            showlegend=False,
        )
        chart_layout(fig)
        st.markdown('<div class="chart-title">Graduated with Holds</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tables row ────────────────────────────────────────────────────────────
    t1, t2 = st.columns(2)

    with t1:
        reasons = sem["incomplete_reasons"]
        total_inc = sum(reasons.values())
        rows_html = ""
        for cat, cnt in reasons.items():
            rows_html += f"<tr><td>{cat}</td><td>{cnt}</td><td>{cnt/total_inc:.1%}</td></tr>"
        rows_html += f"<tr><td>Total</td><td>{total_inc}</td><td>100.0%</td></tr>"
        st.markdown(f"""
        <div class="card">
          <div class="card-title">{term_label} Incomplete Reasons</div>
          <table>
            <thead><tr><th>Category</th><th>Count</th><th>Rate</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

    with t2:
        codes = sem["hold_codes"]
        total_holds = sum(codes.values())
        rows_html = ""
        for code, cnt in codes.items():
            rows_html += f"<tr><td>{code}</td><td>{cnt}</td><td>{cnt/total_holds:.1%}</td></tr>"
        rows_html += f"<tr><td>Total</td><td>{total_holds}</td><td>100.0%</td></tr>"
        st.markdown(f"""
        <div class="card">
          <div class="card-title">{term_label} Graduates with Holds</div>
          <table>
            <thead><tr><th>Hold Code</th><th>Count</th><th>Rate</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="report-title">Graduation Rate - History</div>', unsafe_allow_html=True)

    # ── Application Tracking over 4 Terms ────────────────────────────────────
    tracking = sem["tracking"]
    cohorts   = tracking["cohorts"]
    censuses  = tracking["censuses"]
    cells     = tracking["cells"]

    header_html = "<tr><th>Cohort</th>" + "".join(
        f"<th><span style='font-size:16px'>{c}</span><br><small>Census Date</small></th>" for c in censuses
    ) + "</tr>"

    body_html = ""
    for cohort in cohorts:
        body_html += f'<tr><td class="cohort-label">{cohort}</td>'
        cohort_data = cells.get(cohort, {})
        for census in censuses:
            cell_val = cohort_data.get(census)
            if cell_val is None:
                not_tracked = (census == "SP25" and cohort != "FA25") or (cohort == "FA24" and census == "WI25")
                label = "not tracked" if not_tracked else "—"
                extra = " track-empty" if label == "—" else ""
                body_html += f'<td class="track-null{extra}">{label}</td>'
            elif cell_val == "in progress":
                body_html += '<td><span class="track-null">in progress</span></td>'
            else:
                comp, appl = cell_val
                pct = comp / appl
                diag = " track-diagonal" if cohort == census else ""
                body_html += (
                    f'<td class="{diag.strip()}">{comp:,}&nbsp;/&nbsp;{appl:,}<br>'
                    f'<span class="track-pct">{pct:.1%}</span></td>'
                )
        body_html += "</tr>"

    st.markdown(f"""
    <div class="card">
      <div class="card-title">Application Tracking over 4 Terms</div>
      <table class="track-table">
        <thead>{header_html}</thead>
        <tbody>{body_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Completion Rate History ───────────────────────────────────────────────
    df = pd.DataFrame(history_raw)
    df["total"]           = df["completed"] + df["expired"]
    df["completion_rate"] = df["completed"] / df["total"]
    df["expired_rate"]    = df["expired"]   / df["total"]

    lc, rc = st.columns([3, 2])

    with lc:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["term"], y=df["completed"],
            name="Completed",
            marker_color=BLUE,
            text=[f"{r:.1%}" for r in df["completion_rate"]],
            textposition="inside",
            textfont=dict(size=11, color="white"),
            hovertemplate="%{x}<br>Completed: %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=df["term"], y=df["expired"],
            name="Expired",
            marker_color=ORANGE,
            text=[f"{r:.1%}" for r in df["expired_rate"]],
            textposition="outside",
            textfont=dict(size=11, color="#333333"),
            hovertemplate="%{x}<br>Expired: %{y:,}<extra></extra>",
        ))
        fig.update_layout(
            barmode="stack",
            yaxis=dict(gridcolor="#eef0f5", tickfont=dict(size=12, color="#333333")),
            xaxis=dict(tickangle=-45, gridcolor="#eef0f5", tickfont=dict(size=12, color="#333333")),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5,
                        font=dict(size=12, color="#333333")),
            showlegend=True,
            hovermode="x unified",
        )
        chart_layout(fig, height=320)
        st.markdown('<div class="chart-title">Complete and Expired Rate History</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with rc:
        rows_html = ""
        for _, row_data in df.iterrows():
            rows_html += (
                f"<tr>"
                f"<td>{row_data['term']}</td>"
                f"<td>{int(row_data['completed']):,}</td>"
                f"<td>{row_data['completion_rate']:.1%}</td>"
                f"<td>{int(row_data['expired']):,}</td>"
                f"<td>{row_data['expired_rate']:.1%}</td>"
                f"</tr>"
            )
        total_comp = df["completed"].sum()
        total_exp  = df["expired"].sum()
        total_all  = df["total"].sum()
        rows_html += (
            f"<tr>"
            f"<td>Total</td>"
            f"<td>{total_comp:,}</td>"
            f"<td>{total_comp/total_all:.1%}</td>"
            f"<td>{total_exp:,}</td>"
            f"<td>{total_exp/total_all:.1%}</td>"
            f"</tr>"
        )
        st.markdown(f"""
        <div class="card">
          <div class="card-title">Complete and Expired Rate History<br><span style="font-size:11px; font-weight:400; text-transform:none; letter-spacing:0; color:#666;">as of report date</span></div>
          <div style="overflow-y:auto; max-height:310px;">
          <table>
            <thead><tr>
              <th>Term</th><th>Completed</th><th>Rate</th>
              <th>Expired</th><th>Exp. Rate</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="report-title">Certificate Award Details</div>', unsafe_allow_html=True)

    ca = sem["certificate_auto_award"]
    auto_day       = ca["auto_day"]
    auto_onln      = ca["auto_onln"]
    student_applied = ca["student_applied"]
    cert_incomplete = ca["incomplete"]
    auto_total     = auto_day + auto_onln
    cert_total     = auto_total + student_applied
    auto_rate      = auto_total / cert_total

    # ── Metric tiles ──────────────────────────────────────────────────────────
    ma, mb, mc, md = st.columns(4)
    for col, val, label in [
        (ma, f"{cert_total:,}",       f"{semester_key} Certificates Awarded"),
        (mb, f"{auto_total:,}",       f"{semester_key} Auto-Awarded"),
        (mc, f"{auto_rate:.1%}",      f"{semester_key} Auto-Award Rate"),
        (md, f"{cert_incomplete:,}",  f"{semester_key} Not Awarded"),
    ]:
        col.markdown(f"""
        <div class="metric-tile">
          <div class="value">{val}</div>
          <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    p3c1, p3c2, p3c3 = st.columns(3)

    # ── Chart 1: Donut — Award Source Breakdown ───────────────────────────────
    with p3c1:
        d_labels = ["Auto-Award (DAY)", "Auto-Award (ONLN)", "Student-Applied"]
        d_values = [auto_day, auto_onln, student_applied]
        fig = go.Figure(go.Pie(
            labels=d_labels,
            values=d_values,
            hole=DONUT_HOLE,
            marker_colors=[NAVY, BLUE, GREEN],
            textposition="outside",
            texttemplate="<b>%{label}</b><br><b>%{value:,} (%{percent})</b>",
            textfont=dict(size=12, color="#333333"),
            automargin=True,
        ))
        fig.update_layout(
            annotations=[dict(
                text=f"<b>{cert_total:,}</b><br>Awarded",
                x=0.5, y=0.5, font_size=13, showarrow=False,
            )],
            showlegend=False,
        )
        chart_layout(fig)
        st.markdown('<div class="chart-title">Award Source Breakdown</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 2: Horizontal Bar — Award Source ────────────────────────────────
    with p3c2:
        b_labels = ["Auto-Award (DAY)", "Auto-Award (ONLN)", "Student-Applied"]
        b_values = [auto_day, auto_onln, student_applied]
        b_colors = [NAVY, BLUE, GREEN]
        fig = go.Figure(go.Bar(
            x=b_values,
            y=b_labels,
            orientation="h",
            marker_color=b_colors,
            text=[f"<b>{v:,}</b>" for v in b_values],
            textposition="outside",
            textfont=dict(size=12, color="#333333"),
        ))
        fig.update_layout(
            xaxis=dict(visible=False, range=[0, max(b_values) * 1.22]),
            yaxis=dict(
                autorange="reversed",
                tickmode="array",
                tickvals=b_labels,
                ticktext=[f"<b>{l}</b>" for l in b_labels],
                tickfont=dict(size=12, color="#333333"),
            ),
            bargap=0.35,
        )
        chart_layout(fig)
        st.markdown(f'<div class="chart-title">{term_label} Certificate Awards</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Table: Breakdown ──────────────────────────────────────────────────────
    with p3c3:
        rows_html = ""
        for label_t, count in [
            ("Auto-Award (DAY)",  auto_day),
            ("Auto-Award (ONLN)", auto_onln),
            ("Student-Applied",   student_applied),
        ]:
            rows_html += f"<tr><td>{label_t}</td><td>{count:,}</td><td>{count/cert_total:.1%}</td></tr>"
        rows_html += f"<tr><td>Total Awarded</td><td>{cert_total:,}</td><td>100.0%</td></tr>"

        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card">
          <div class="card-title">{term_label} Certificate Breakdown</div>
          <table>
            <thead><tr><th>Category</th><th>Count</th><th>% of Awarded</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
          <br>
          <table>
            <thead><tr><th>Status</th><th>Count</th></tr></thead>
            <tbody>
              <tr><td>Incomplete (not awarded)</td><td>{cert_incomplete:,}</td></tr>
            </tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN TAB — Data Entry (hidden — re-add tab_admin to st.tabs() to restore)
# ──────────────────────────────────────────────────────────────────────────────
if False:  # noqa — tab hidden
    st.markdown('<div class="report-title">Data Entry — New Semester</div>', unsafe_allow_html=True)

    _pwd = st.text_input("Password", type="password", key="admin_pwd")
    _correct = st.secrets.get("ADMIN_PASSWORD", "byui_admin")

    if _pwd != _correct:
        st.info("Enter the admin password to access data entry.")
    else:
        st.success("Authenticated. Fill in the fields below and click **Generate data.json** at the bottom.")
        st.markdown("---")

        # ── Semester Info ──────────────────────────────────────────────────────
        st.subheader("1. Semester Info")
        _c1, _c2 = st.columns(2)
        _sem_key   = _c1.text_input("Semester Key",   placeholder="e.g. WI26", key="sk")
        _sem_label = _c2.text_input("Semester Label", placeholder="e.g. Winter 2026", key="sl")

        # ── Application Summary ────────────────────────────────────────────────
        st.subheader("2. Application Summary")
        _c1, _c2, _c3, _c4 = st.columns(4)
        _apps  = _c1.number_input("Applications", min_value=0, step=1, key="as_apps")
        _grad  = _c2.number_input("Graduated",    min_value=0, step=1, key="as_grad")
        _other = _c3.number_input("Other",         min_value=0, step=1, key="as_other")
        _inc   = _c4.number_input("Incomplete",    min_value=0, step=1, key="as_inc")

        # ── Credential Types ───────────────────────────────────────────────────
        st.subheader("3. Credential Types Awarded")
        _c1, _c2, _c3 = st.columns(3)
        _assoc = _c1.number_input("Associate",   min_value=0, step=1, key="ct_assoc")
        _bach  = _c2.number_input("Bachelor",    min_value=0, step=1, key="ct_bach")
        _cert  = _c3.number_input("Certificate", min_value=0, step=1, key="ct_cert")

        # ── Holds ──────────────────────────────────────────────────────────────
        st.subheader("4. Holds")
        _c1, _c2 = st.columns(2)
        _no_holds = _c1.number_input("No Holds", min_value=0, step=1, key="h_no")
        _holds    = _c2.number_input("Holds",    min_value=0, step=1, key="h_yes")

        # ── Incomplete Reasons ─────────────────────────────────────────────────
        st.subheader("5. Incomplete Reasons")
        st.caption("Fill only the rows you need — leave the rest blank.")
        _inc_reasons = {}
        for _i in range(6):
            _c1, _c2 = st.columns([3, 1])
            _r = _c1.text_input(f"Reason {_i+1}", placeholder="e.g. Missing Course", key=f"ir_name_{_i}")
            _n = _c2.number_input("Count", min_value=0, step=1, key=f"ir_cnt_{_i}")
            if _r.strip():
                _inc_reasons[_r.strip()] = int(_n)

        # ── Hold Codes ─────────────────────────────────────────────────────────
        st.subheader("6. Hold Codes")
        st.caption("Fill only the rows you need.")
        _hold_codes = {}
        for _i in range(5):
            _c1, _c2 = st.columns([3, 1])
            _code = _c1.text_input(f"Code {_i+1}", placeholder="e.g. PDUE", key=f"hc_code_{_i}")
            _cnt  = _c2.number_input("Count", min_value=0, step=1, key=f"hc_cnt_{_i}")
            if _code.strip():
                _hold_codes[_code.strip()] = int(_cnt)

        # ── Certificate Auto Award ─────────────────────────────────────────────
        st.subheader("7. Certificate Auto Award")
        _c1, _c2, _c3, _c4 = st.columns(4)
        _auto_day  = _c1.number_input("Auto Day",        min_value=0, step=1, key="ca_day")
        _auto_onln = _c2.number_input("Auto Online",     min_value=0, step=1, key="ca_onln")
        _stu_app   = _c3.number_input("Student Applied", min_value=0, step=1, key="ca_stu")
        _cert_inc  = _c4.number_input("Incomplete",      min_value=0, step=1, key="ca_inc")

        # ── Tracking Table ─────────────────────────────────────────────────────
        st.subheader("8. Application Tracking Table")
        st.caption("Enter cohorts (rows) left to right newest→oldest, and censuses (columns) same order.")

        _coh_cols = st.columns(4)
        _cohorts = [c.text_input(f"Cohort {i+1}", placeholder="e.g. WI26", key=f"coh_{i}")
                    for i, c in enumerate(_coh_cols)]

        _cen_cols = st.columns(5)
        _censuses = [c.text_input(f"Census {i+1}", placeholder="e.g. WI26", key=f"cen_{i}")
                     for i, c in enumerate(_cen_cols)]

        st.caption("For each cell: **—** = future/blank · **in progress** = currently open · **Numbers** = enter completed / applied")
        _cells = {}
        for _i, _coh in enumerate(_cohorts):
            if not _coh.strip():
                continue
            _cells[_coh] = {}
            _gcols = st.columns([1] + [2] * 5)
            _gcols[0].markdown(f"**{_coh}**")
            for _j, _cen in enumerate(_censuses):
                if not _cen.strip():
                    continue
                with _gcols[_j + 1]:
                    st.caption(_cen)
                    _status = st.selectbox(
                        "status", ["—", "in progress", "Numbers"],
                        key=f"st_{_i}_{_j}", label_visibility="collapsed"
                    )
                    if _status == "Numbers":
                        _comp = st.number_input("Completed", min_value=0, step=1, key=f"cp_{_i}_{_j}")
                        _appl = st.number_input("Applied",   min_value=0, step=1, key=f"ap_{_i}_{_j}")
                        _cells[_coh][_cen] = [int(_comp), int(_appl)]
                    elif _status == "in progress":
                        _cells[_coh][_cen] = "in progress"
                    # "—" → key not added → None when looked up

        # ── Completion History ─────────────────────────────────────────────────
        st.subheader("9. Completion History — Add New Term")
        st.caption("This adds a new row at the top of the history chart/table.")
        _c1, _c2, _c3 = st.columns(3)
        _hist_term = _c1.text_input("Term", placeholder="e.g. WI26", key="ht_term")
        _hist_comp = _c2.number_input("Completed", min_value=0, step=1, key="ht_comp")
        _hist_exp  = _c3.number_input("Expired",   min_value=0, step=1, key="ht_exp")

        # ── Generate ───────────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("Generate data.json", type="primary"):
            if not _sem_key.strip():
                st.error("Semester Key is required.")
            elif not _sem_label.strip():
                st.error("Semester Label is required.")
            else:
                _new_sem = {
                    "label": _sem_label.strip(),
                    "credential_types": {
                        "Associate":   int(_assoc),
                        "Bachelor":    int(_bach),
                        "Certificate": int(_cert),
                    },
                    "application_summary": {
                        "Applications": int(_apps),
                        "Graduated":    int(_grad),
                        "Other":        int(_other),
                        "Incomplete":   int(_inc),
                    },
                    "holds": {
                        "No Holds": int(_no_holds),
                        "Holds":    int(_holds),
                    },
                    "incomplete_reasons":    _inc_reasons,
                    "hold_codes":            _hold_codes,
                    "certificate_auto_award": {
                        "auto_day":        int(_auto_day),
                        "auto_onln":       int(_auto_onln),
                        "student_applied": int(_stu_app),
                        "incomplete":      int(_cert_inc),
                    },
                    "tracking": {
                        "cohorts":  [c for c in _cohorts  if c.strip()],
                        "censuses": [c for c in _censuses if c.strip()],
                        "cells":    _cells,
                    },
                }

                _new_data = {
                    "semesters": dict(data["semesters"]),
                    "completion_history": list(data["completion_history"]),
                }
                _new_data["semesters"][_sem_key.strip()] = _new_sem

                if _hist_term.strip():
                    _new_data["completion_history"].insert(
                        0, {"term": _hist_term.strip(), "completed": int(_hist_comp), "expired": int(_hist_exp)}
                    )

                _json_out = json.dumps(_new_data, indent=2)
                st.download_button(
                    label="⬇️ Download data.json",
                    data=_json_out,
                    file_name="data.json",
                    mime="application/json",
                    type="primary",
                )
                st.info("**Next steps:** Replace `data/data.json` in your repo with this file, then push to GitHub. The app will update automatically.")
