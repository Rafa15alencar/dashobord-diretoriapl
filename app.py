from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo-paulo-lopes.jpg"
BRAND_NAVY = "#173247"
BRAND_GOLD = "#A58D51"
BRAND_PALETTE = [BRAND_GOLD, BRAND_NAVY, "#C6B783", "#7C6A43", "#526A78"]
SHEET_ID = "1raJj7FIbFLnlueNpM3xCurOvo6dXW9aAHEIPqrsOjY0"
SHEETS_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?"
)
MONTH_SHEETS = {
    "SETEMBRO": "PROPOSTAS SETEMBRO",
    "OUTUBRO": "CONTRATOS OUTUBRO",
    "NOVEMBRO": "CONTRATOS NOVEMBRO",
    "DEZEMBRO": "CONTRATOS DEZEMBRO",
}
MONTH_ORDER = list(MONTH_SHEETS)
CONTRACT_COLUMNS = [
    "MES",
    "QTDE",
    "DATA_LEAD",
    "DATA_FECHAMENTO",
    "CLIENTE",
    "PRODUTO",
    "CAMPANHA",
    "ENTRADA",
    "QTDE_PARCELAS",
    "VALOR_PARCELA",
    "VALOR_CONTRATO",
    "ENTRADA_PAGA",
]

st.set_page_config(
    page_title="Paulo Lopes Advogados | Painel Comercial",
    page_icon="⚖️",
    layout="wide",
)


def parse_number(value: object) -> float:
    text = str(value).strip().replace("R$", "").replace("%", "").replace(" ", "")
    text = text.replace("\u00a0", "").replace("\u2212", "-")
    if not text:
        return 0.0

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError as error:
        raise ValueError(f"Valor numérico inválido recebido da planilha: {value!r}") from error


def read_sheet(sheet_name: str) -> pd.DataFrame:
    query = urlencode({"tqx": "out:csv", "sheet": sheet_name})
    response = requests.get(
        f"{SHEETS_CSV_URL}{query}",
        timeout=30,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "text/csv" not in content_type.lower():
        raise ValueError(
            "O Google Sheets não retornou CSV. Confirme se a planilha está "
            "compartilhada com acesso de leitor para qualquer pessoa com o link."
        )

    try:
        return pd.read_csv(
            BytesIO(response.content),
            header=None,
            dtype=str,
            keep_default_na=False,
        )
    except pd.errors.ParserError as error:
        raise ValueError(
            f"Não foi possível interpretar a aba {sheet_name!r} como CSV."
        ) from error


@st.cache_data(ttl=300, show_spinner=False)
def load_google_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    result = read_sheet("RESULTADO")
    if result.shape[0] < 11 or result.shape[1] < 9:
        raise ValueError(
            "A aba RESULTADO não contém a estrutura esperada para o painel."
        )

    summary_rows = result.iloc[1:5]
    target_rows = result.iloc[7:11]
    summary = {}
    for _, row in summary_rows.iterrows():
        month = row.iloc[0].strip().upper()
        if month not in MONTH_SHEETS:
            raise ValueError(f"Mês inesperado na aba RESULTADO: {month!r}")

        summary[month] = {
            "MES": month,
            "LEADS_RECEBIDOS": parse_number(row.iloc[1]),
            "CONTRATOS_FECHADOS": parse_number(row.iloc[2]),
            "VALOR_CONTRATOS": parse_number(row.iloc[6]),
            "ENTRADAS": parse_number(row.iloc[7]),
            "RECORRENCIA": parse_number(row.iloc[8]),
        }

    for _, row in target_rows.iterrows():
        month = row.iloc[0].strip().upper()
        if month not in summary:
            raise ValueError(f"Mês inesperado nas metas da aba RESULTADO: {month!r}")
        summary[month]["META"] = parse_number(row.iloc[6])

    if set(summary) != set(MONTH_ORDER) or any(
        "META" not in summary[month] for month in MONTH_ORDER
    ):
        raise ValueError("Não foi possível carregar todos os meses e metas do painel.")

    summary_df = pd.DataFrame([summary[month] for month in MONTH_ORDER])
    summary_df["CONVERSAO"] = summary_df.apply(
        lambda row: (
            row["CONTRATOS_FECHADOS"] / row["LEADS_RECEBIDOS"]
            if row["LEADS_RECEBIDOS"]
            else 0.0
        ),
        axis=1,
    )
    summary_df["REALIZADO_PERCENTUAL"] = summary_df.apply(
        lambda row: row["ENTRADAS"] / row["META"] if row["META"] else 0.0,
        axis=1,
    )
    summary_df["DIFERENCA_META"] = summary_df["ENTRADAS"] - summary_df["META"]

    contract_rows = []
    for month, sheet_name in MONTH_SHEETS.items():
        sheet = read_sheet(sheet_name)
        if sheet.shape[0] <= 8 or sheet.shape[1] <= 23:
            continue

        for _, row in sheet.iloc[8:].iterrows():
            name = row.iloc[3].strip() if len(row) > 3 else ""
            if not name:
                continue

            entry = parse_number(row.iloc[19])
            installments = parse_number(row.iloc[20])
            installment_value = parse_number(row.iloc[21])
            contract_rows.append(
                {
                    "MES": month,
                    "QTDE": row.iloc[0],
                    "DATA_LEAD": row.iloc[1],
                    "DATA_FECHAMENTO": row.iloc[2],
                    "CLIENTE": name,
                    "PRODUTO": row.iloc[4].strip(),
                    "CAMPANHA": row.iloc[13].strip(),
                    "ENTRADA": entry,
                    "QTDE_PARCELAS": installments,
                    "VALOR_PARCELA": installment_value,
                    "VALOR_CONTRATO": entry + installments * installment_value,
                    "ENTRADA_PAGA": row.iloc[23].strip(),
                }
            )

    contracts_df = pd.DataFrame(contract_rows, columns=CONTRACT_COLUMNS)
    fetched_at = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S")
    return summary_df, contracts_df, fetched_at


logo_column, title_column, refresh_column = st.columns(
    [1.35, 4.65, 1.7], vertical_alignment="center"
)
with logo_column:
    st.image(str(LOGO_PATH), width=165)
with title_column:
    st.title("Painel de Resultados Comerciais")
    st.caption("Paulo Lopes Advogados • Acompanhamento comercial 2026")
with refresh_column:
    refresh = st.button("Atualizar Dados", type="primary", width="stretch")
if refresh:
    load_google_data.clear()
    st.rerun()

try:
    with st.spinner("Carregando dados atualizados do Google Sheets..."):
        summary, contracts, fetched_at = load_google_data()
except (requests.RequestException, ValueError) as error:
    st.error(
        "Não foi possível carregar os dados do Google Sheets. Verifique a conexão "
        "e se a planilha está compartilhada como leitor para qualquer pessoa com "
        f"o link. Detalhes: {error}"
    )
    st.stop()

summary["MES"] = pd.Categorical(
    summary["MES"], categories=MONTH_ORDER, ordered=True
)
summary = summary.sort_values("MES")
st.caption(f"Fonte: Google Sheets • Atualizado em {fetched_at}")

total_contracts = int(summary["CONTRATOS_FECHADOS"].sum())
total_leads = int(summary["LEADS_RECEBIDOS"].sum())
total_value = float(summary["VALOR_CONTRATOS"].sum())

cards = st.columns(4)
cards[0].metric("Leads recebidos", f"{total_leads:,}".replace(",", "."))
cards[1].metric("Contratos fechados", f"{total_contracts:,}".replace(",", "."))
cards[2].metric(
    "Valor contratado",
    f"R$ {total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
)
cards[3].metric(
    "Taxa de conversão",
    f"{(total_contracts / total_leads * 100 if total_leads else 0):.1f}%",
)

st.divider()

left, right = st.columns(2)

with left:
    fig_contracts = px.bar(
        summary,
        x="MES",
        y="CONTRATOS_FECHADOS",
        text="CONTRATOS_FECHADOS",
        title="Contratos fechados por mês",
        labels={"MES": "Mês", "CONTRATOS_FECHADOS": "Contratos"},
    )
    fig_contracts.update_traces(textposition="outside")
    fig_contracts.update_traces(marker_color=BRAND_GOLD, textfont_color=BRAND_NAVY)
    fig_contracts.update_layout(showlegend=False)
    st.plotly_chart(fig_contracts, width="stretch")

with right:
    fig_value = px.bar(
        summary,
        x="MES",
        y=["ENTRADAS", "RECORRENCIA"],
        title="Composição dos valores",
        labels={"value": "Valor (R$)", "variable": "Tipo", "MES": "Mês"},
        barmode="group",
        color_discrete_map={"ENTRADAS": BRAND_GOLD, "RECORRENCIA": BRAND_NAVY},
    )
    st.plotly_chart(fig_value, width="stretch")

left, right = st.columns(2)

with left:
    fig_target = px.bar(
        summary,
        x="MES",
        y=["META", "ENTRADAS"],
        title="Meta versus entradas realizadas",
        labels={"value": "Valor (R$)", "variable": "Indicador", "MES": "Mês"},
        barmode="group",
        color_discrete_map={"META": "#D8D0BC", "ENTRADAS": BRAND_GOLD},
    )
    st.plotly_chart(fig_target, width="stretch")

with right:
    if contracts.empty:
        st.info("Não há linhas de contratos disponíveis.")
    else:
        products = contracts.groupby("PRODUTO", dropna=False).size().reset_index(name="CONTRATOS")
        products = products[products["PRODUTO"].astype(str).str.strip() != ""]
        fig_products = px.pie(
            products,
            names="PRODUTO",
            values="CONTRATOS",
            title="Contratos por produto",
            color_discrete_sequence=BRAND_PALETTE,
        )
        st.plotly_chart(fig_products, width="stretch")

st.subheader("Resumo mensal")
display_summary = summary[
    [
        "MES",
        "LEADS_RECEBIDOS",
        "CONTRATOS_FECHADOS",
        "CONVERSAO",
        "VALOR_CONTRATOS",
        "ENTRADAS",
        "RECORRENCIA",
        "META",
        "REALIZADO_PERCENTUAL",
        "DIFERENCA_META",
    ]
].copy()
display_summary["CONVERSAO"] = display_summary["CONVERSAO"].map(
    lambda value: f"{value:.1%}"
)
display_summary["REALIZADO_PERCENTUAL"] = display_summary[
    "REALIZADO_PERCENTUAL"
].map(lambda value: f"{value:.1%}")
currency_columns = [
    "VALOR_CONTRATOS",
    "ENTRADAS",
    "RECORRENCIA",
    "META",
    "DIFERENCA_META",
]
for column in currency_columns:
    display_summary[column] = display_summary[column].map(
        lambda value: f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
st.dataframe(display_summary, width="stretch", hide_index=True)

with st.expander("Ver contratos"):
    st.dataframe(contracts, width="stretch", hide_index=True)
