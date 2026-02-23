import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Dashboard Hiper", layout="wide")

# =========================
# USUÁRIOS AUTORIZADOS
# =========================
USUARIOS = {
    "admin": "Senha@741852",
    "ana.hiper": "Hiper@26",
    "suzan.hiper": "Hiper#26",
    "vilson.hiper": "Hiper@26"

}

# =========================
# FUNÇÃO DE LOGIN
# =========================
def login(usuario, senha):
    return usuario in USUARIOS and USUARIOS[usuario] == senha

# =========================
# FUNÇÃO PARA REGISTRAR LOG DE ACESSO NO GOOGLE SHEETS
# =========================
# =========================
# FUNÇÃO PARA REGISTRAR LOG DE ACESSO NO GOOGLE SHEETS
# =========================
def registrar_log(usuario, acao="LOGIN"):
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        gc = gspread.authorize(creds)
        sh = gc.open("Log acessos DashHiper")

        try:
            ws = sh.worksheet("Página1")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="Página1", rows=1000, cols=5)

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Não é possível capturar IP/User-Agent no Streamlit Cloud diretamente
        ip = "cloud"  
        user_agent = "desconhecido"

        ws.append_row([data_hora, usuario, ip, user_agent, acao])

    except Exception as e:
        st.error(f"Erro ao registrar log de acesso: {e}")


# =========================
# SESSÃO
# =========================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# =========================
# FORMULÁRIO DE LOGIN
# =========================
if not st.session_state["logado"]:
    st.title("🔐 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    entrar = st.button("Entrar")

    if entrar:
        if login(usuario, senha):
            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario

            if "log_registrado" not in st.session_state:
                registrar_log(usuario, "LOGIN")
                st.session_state["log_registrado"] = True

            st.success(f"Bem-vindo(a), {usuario}!")

# =========================
# DASHBOARD - APENAS SE LOGADO
# =========================
if st.session_state["logado"]:
    st.title("📊 Dashboard Hiper")
    st.button("Logout", on_click=lambda: st.session_state.update({"logado": False}))

    # =========================
    # CAMINHO BASE
    # =========================
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

    pastas = {
        "Acordos": "acordos",
        "Discados": "discados",
        "Importações": "importacoes",
        "Pagamentos": "pagamentos"
    }

    # =========================
    # FUNÇÕES DE LEITURA
    # =========================
    def ler_arquivo(caminho):
        ext = os.path.splitext(caminho)[1].lower()
        if ext == ".xlsx":
            return pd.read_excel(caminho)
        elif ext == ".xls":
            return pd.read_excel(caminho, engine="xlrd")
        elif ext in [".csv", ".txt"]:
            return pd.read_csv(caminho, sep=";", encoding="latin-1")
        else:
            return None

    def ler_pasta(caminho_pasta):
        if not os.path.exists(caminho_pasta):
            return pd.DataFrame()
        arquivos = os.listdir(caminho_pasta)
        dfs = []
        for arquivo in arquivos:
            caminho = os.path.join(caminho_pasta, arquivo)
            df = ler_arquivo(caminho)
            if df is not None:
                df["ARQUIVO_ORIGEM"] = arquivo
                dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    @st.cache_data
    def carregar_dados():
        dados = {}
        for nome, pasta in pastas.items():
            caminho = os.path.join(BASE_PATH, pasta)
            dados[nome] = ler_pasta(caminho)
        return dados

    dados = carregar_dados()

    # =========================
    # EXIBIÇÃO POR ABAS
    # =========================
    abas = st.tabs(list(dados.keys()))

    for aba, nome in zip(abas, dados.keys()):
        with aba:
            df = dados[nome]

            # PADRONIZAÇÃO DE COLUNAS
            df.columns = (
                df.columns
                .str.strip()
                .str.upper()
                .str.replace(" ", "_")
                .str.replace(".", "", regex=False)
            )

            st.subheader(nome)

            if df.empty:
                st.warning("Nenhum dado encontrado.")
                continue

            # =========================
            # ABA ACORDOS
            # =========================
            if nome == "Acordos":

                st.markdown("### 📑 Acordos")

                if df.empty:
                    st.warning("Nenhum acordo encontrado na pasta.")
                    st.stop()

                # -------------------------
                # Padronização de datas
                # -------------------------
                col_vencto = "VENCTO" if "VENCTO" in df.columns else None
                col_data_acordo = "DATA_INC_ACORDO" if "DATA_INC_ACORDO" in df.columns else None

                if col_vencto:
                    df[col_vencto] = pd.to_datetime(df[col_vencto], errors="coerce")

                if col_data_acordo:
                    df[col_data_acordo] = pd.to_datetime(df[col_data_acordo], errors="coerce")

                # -------------------------
                # Filtros
                # -------------------------
                st.markdown("### 🔎 Filtros")

                f1, f2, f3 = st.columns(3)
                f4, f5 = st.columns(2)

                with f1:
                    nome_cliente = st.text_input(
                        "Nome do cliente",
                        key="ac_nome"
                    )

                with f2:
                    parcela = st.multiselect(
                        "Parcela",
                        sorted(df["PARCELA"].dropna().unique()),
                        key="ac_parcela"
                    )

                with f3:
                    plano = st.multiselect(
                        "Plano",
                        sorted(df["PLANO"].dropna().unique()),
                        key="ac_plano"
                    )

                with f4:
                    if col_vencto:
                        vencto_range = st.date_input(
                            "Vencimento",
                            value=(df[col_vencto].min(), df[col_vencto].max()),
                            key="ac_vencto"
                        )

                with f5:
                    if col_data_acordo:
                        data_acordo_range = st.date_input(
                            "Data do acordo",
                            value=(df[col_data_acordo].min(), df[col_data_acordo].max()),
                            key="ac_data"
                        )

                # -------------------------
                # Aplicação dos filtros
                # -------------------------
                df_filtrado = df.copy()

                if nome_cliente:
                    df_filtrado = df_filtrado[
                        df_filtrado["NOME_DO_CLIENTE"]
                        .str.contains(nome_cliente, case=False, na=False)
                    ]

                if parcela:
                    df_filtrado = df_filtrado[df_filtrado["PARCELA"].isin(parcela)]

                if plano:
                    df_filtrado = df_filtrado[df_filtrado["PLANO"].isin(plano)]

                if col_vencto and isinstance(vencto_range, tuple):
                    df_filtrado = df_filtrado[
                        (df_filtrado[col_vencto] >= pd.to_datetime(vencto_range[0])) &
                        (df_filtrado[col_vencto] <= pd.to_datetime(vencto_range[1]))
                    ]

                if col_data_acordo and isinstance(data_acordo_range, tuple):
                    df_filtrado = df_filtrado[
                        (df_filtrado[col_data_acordo] >= pd.to_datetime(data_acordo_range[0])) &
                        (df_filtrado[col_data_acordo] <= pd.to_datetime(data_acordo_range[1]))
                    ]

                # -------------------------
                # Seleção das colunas visíveis
                # -------------------------
                colunas_visiveis = [
                    "NOME_DO_CLIENTE",
                    "PARCELA",
                    "PLANO",
                    "VENCTO",
                    "VLR_PARCELA",
                    "TOTAL_ABERTO_ACORDO",
                    "DATA_INC_ACORDO"
                ]

                colunas_visiveis = [c for c in colunas_visiveis if c in df_filtrado.columns]

                df_exibicao = df_filtrado[colunas_visiveis]

                # -------------------------
                # Tabela de acordos
                # -------------------------
                st.markdown("### 📋 Detalhamento dos acordos")
                st.dataframe(df_exibicao, use_container_width=True)

                # -------------------------
                # Calendário de vencimentos
                # -------------------------
                if col_vencto and "VLR_PARCELA" in df_filtrado.columns and not df_filtrado.empty:

                    st.markdown("### 📅 Calendário de vencimentos")

                    df_sum = (
                        df_filtrado
                        .groupby(col_vencto)["VLR_PARCELA"]
                        .sum()
                        .reset_index(name="TOTAL_VLR")
                    )

                    df_count = (
                        df_filtrado
                        .groupby(col_vencto)
                        .size()
                        .reset_index(name="QTDE_ACORDOS")
                    )

                    df_count["TOTAL_VLR"] = df_sum["TOTAL_VLR"]

                    start_date = df_count[col_vencto].min()
                    end_date = df_count[col_vencto].max()

                    start_date -= timedelta(days=start_date.weekday())
                    end_date += timedelta(days=(6 - end_date.weekday()))

                    all_dates = pd.date_range(start_date, end_date)

                    count_dict = dict(zip(df_count[col_vencto], df_count["QTDE_ACORDOS"]))
                    value_dict = dict(zip(df_count[col_vencto], df_count["TOTAL_VLR"]))

                    cell_values = [
                        (d, count_dict.get(d, 0), value_dict.get(d, 0))
                        for d in all_dates
                    ]

                    weeks = [cell_values[i:i + 7] for i in range(0, len(cell_values), 7)]

                    calendar_df = pd.DataFrame(
                        [
                            [
                                f"{day.day:02d}/{day.month:02d} ({q} | {v:,.2f})"
                                for (day, q, v) in week
                            ]
                            for week in weeks
                        ],
                        columns=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                    )

                    st.dataframe(calendar_df, use_container_width=True)


            # =========================
            # ABA DISCADOS
            # =========================
            if nome == "Discados":
                st.markdown("### 📊 Frequência de status e qualificação por número")
                if "NUMBER" not in df.columns or "READABLE_STATUS_TEXT" not in df.columns:
                    st.warning("As colunas NUMBER ou READABLE_STATUS_TEXT não foram encontradas.")
                else:
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        filter_number = st.text_input("Número")
                    with col_f2:
                        cpf_col = "MAILING_DATADATACLIENTE_-_CPF" if "MAILING_DATADATACLIENTE_-_CPF" in df.columns else None
                        filter_cpf = st.text_input("CPF") if cpf_col else None
                    with col_f3:
                        filter_qual = st.multiselect("Qualificação", sorted(df["QUALIFICATION"].dropna().unique())) if "QUALIFICATION" in df.columns else None

                    df_filtrado = df.copy()
                    if filter_number:
                        df_filtrado = df_filtrado[df_filtrado["NUMBER"].astype(str).str.contains(filter_number, case=False, na=False)]
                    if filter_cpf and cpf_col:
                        df_filtrado = df_filtrado[df_filtrado[cpf_col].astype(str).str.contains(filter_cpf, case=False, na=False)]
                    if filter_qual and "QUALIFICATION" in df_filtrado.columns:
                        df_filtrado = df_filtrado[df_filtrado["QUALIFICATION"].isin(filter_qual)]

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Registros", len(df_filtrado))
                    col2.metric("Colunas", df_filtrado.shape[1])
                    col3.metric("Arquivos", df_filtrado["ARQUIVO_ORIGEM"].nunique() if "ARQUIVO_ORIGEM" in df_filtrado.columns else 0)

                    st.dataframe(df_filtrado, use_container_width=True)

                    def map_status(status):
                        status_lower = str(status).lower()
                        if "caixa postal" in status_lower:
                            return "Caixa Postal"
                        elif "não atendida" in status_lower or "nao atendida" in status_lower:
                            return "Nao Atendida"
                        else:
                            return status

                    df_filtrado["STATUS_NORMALIZADO"] = df_filtrado["READABLE_STATUS_TEXT"].apply(map_status)

                    st.markdown("### 📈 Distribuição por status e qualificação")
                    col_graf_status, col_graf_qual = st.columns([2,2])
                    status_counts = df_filtrado["STATUS_NORMALIZADO"].value_counts().reset_index()
                    status_counts.columns = ["Status","Quantidade"]

                    with col_graf_status:
                        st.plotly_chart(
                            px.pie(status_counts, names="Status", values="Quantidade", hole=0.3,
                                   color_discrete_sequence=px.colors.qualitative.Pastel, title="Status dos Discados"),
                            use_container_width=True
                        )
                        st.dataframe(status_counts, use_container_width=True)

                    if "QUALIFICATION" in df_filtrado.columns:
                        df_qual = df_filtrado[~df_filtrado["QUALIFICATION"].astype(str).str.contains("-", na=False)]
                        if not df_qual.empty:
                            qual_counts = df_qual["QUALIFICATION"].value_counts().reset_index()
                            qual_counts.columns = ["Qualificação","Quantidade"]
                            with col_graf_qual:
                                st.plotly_chart(
                                    px.pie(qual_counts, names="Qualificação", values="Quantidade", hole=0.3,
                                           color_discrete_sequence=px.colors.qualitative.Set3, title="Distribuição de Qualificação"),
                                    use_container_width=True
                                )
                                st.dataframe(qual_counts, use_container_width=True)

            # =========================
            # ABA IMPORTAÇÕES
            # =========================
            if nome == "Importações":
                st.markdown("### 📊 Métricas Gerais")

                qtd_total = df.dropna(how='all').shape[0]
                if "VALOR" in df.columns:
                    df["VALOR"] = pd.to_numeric(df["VALOR"].astype(str).str.replace(",", "."), errors="coerce")
                    valor_total = df["VALOR"].sum()
                else:
                    valor_total = 0
                ticket_medio = valor_total / qtd_total if qtd_total else 0
                col1, col2, col3 = st.columns(3)
                col1.metric("Quantidade total", qtd_total)
                col2.metric("Valor total", f"R$ {valor_total:,.2f}")
                col3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

                colunas_desejadas = [
                    "NOME_DEVEDOR","CPF","BAIRRO","CIDADE",
                    "NÚMERO_FONE","CONTRATO","DATA_CONTRATO",
                    "NOME_FILIAL","VENCIMENTO","VALOR"
                ]
                df_importacoes = df.loc[:, df.columns.intersection(colunas_desejadas)]
                st.dataframe(df_importacoes, use_container_width=True)

                col_filial, col_cidade = st.columns(2)
                if "NOME_FILIAL" in df_importacoes.columns:
                    tabela_filial = df_importacoes.groupby("NOME_FILIAL").agg(
                        QTDE_CLIENTES=("NOME_DEVEDOR","nunique"),
                        VALOR_TOTAL=("VALOR","sum")
                    ).reset_index().sort_values(by="VALOR_TOTAL", ascending=False)
                    with col_filial:
                        st.markdown("### 📊 Clientes e valor por Filial")
                        st.dataframe(tabela_filial, use_container_width=True)

                if "CIDADE" in df_importacoes.columns:
                    tabela_cidade = df_importacoes.groupby("CIDADE").agg(
                        QTDE_CLIENTES=("NOME_DEVEDOR","nunique"),
                        VALOR_TOTAL=("VALOR","sum")
                    ).reset_index().sort_values(by="VALOR_TOTAL", ascending=False)
                    with col_cidade:
                        st.markdown("### 📊 Clientes e valor por Cidade")
                        st.dataframe(tabela_cidade, use_container_width=True)
            # =========================
            # ABA PAGAMENTOS
            # =========================
            if nome == "Pagamentos":
                st.markdown("### 💰 Pagamentos")

                if df.empty:
                    st.warning("Nenhum pagamento encontrado.")
                else:
                    # -------------------------
                    # Padronizações importantes
                    # -------------------------
                    col_data = next((c for c in df.columns if "DATA" in c), None)
                    col_valor = next((c for c in df.columns if "VALOR" in c), None)
                    col_cpf = next((c for c in df.columns if "CPF" in c), None)
                    col_nome = next((c for c in df.columns if "NOME" in c), None)
                    col_forma = next((c for c in df.columns if "FORMA" in c or "MEIO" in c), None)

                    if col_data:
                        df[col_data] = pd.to_datetime(df[col_data], errors="coerce")

                    if col_valor:
                        df[col_valor] = (
                            df[col_valor]
                            .astype(str)
                            .str.replace(".", "", regex=False)
                            .str.replace(",", ".", regex=False)
                        )
                        df[col_valor] = pd.to_numeric(df[col_valor], errors="coerce")

                    # -------------------------
                    # KPIs
                    # -------------------------
                    qtd_pagamentos = df.shape[0]
                    valor_total = df[col_valor].sum() if col_valor else 0
                    ticket_medio = valor_total / qtd_pagamentos if qtd_pagamentos else 0

                    k1, k2, k3 = st.columns(3)
                    k1.metric("Quantidade de Pagamentos", qtd_pagamentos)
                    k2.metric("Valor Total Pago", f"R$ {valor_total:,.2f}")
                    k3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")

                    # -------------------------
                    # Filtros
                    # -------------------------
                    st.markdown("### 🔎 Filtros")

                    f1, f2, f3, f4 = st.columns(4)

                    with f1:
                        filtro_nome = (
                            st.text_input("Nome do cliente", key="pag_nome")
                            if col_nome else None
                        )

                    with f2:
                        filtro_cpf = (
                            st.text_input("CPF", key="pag_cpf")
                            if col_cpf else None
                        )

                    with f3:
                        filtro_forma = (
                            st.multiselect(
                                "Forma de pagamento",
                                sorted(df[col_forma].dropna().unique()),
                                key="pag_forma"
                            ) if col_forma else None
                        )

                    with f4:
                        if col_data:
                            periodo = st.date_input(
                                "Período",
                                value=(df[col_data].min(), df[col_data].max()),
                                key="pag_periodo"
                            )

                    # -------------------------
                    # Aplicação dos filtros
                    # -------------------------
                    df_filtrado = df.copy()

                    if filtro_nome and col_nome:
                        df_filtrado = df_filtrado[
                            df_filtrado[col_nome].str.contains(filtro_nome, case=False, na=False)
                        ]

                    if filtro_cpf and col_cpf:
                        df_filtrado = df_filtrado[
                            df_filtrado[col_cpf].astype(str).str.contains(filtro_cpf, na=False)
                        ]

                    if filtro_forma and col_forma:
                        df_filtrado = df_filtrado[df_filtrado[col_forma].isin(filtro_forma)]

                    if col_data and isinstance(periodo, tuple) and len(periodo) == 2:
                        df_filtrado = df_filtrado[
                            (df_filtrado[col_data] >= pd.to_datetime(periodo[0])) &
                            (df_filtrado[col_data] <= pd.to_datetime(periodo[1]))
                        ]

                    # -------------------------
                    # COLUNAS VISÍVEIS (PADRÃO)
                    # -------------------------
                    COLUNAS_VISIVEIS = [
                        "CODIGO",
                        "CLIENTE",
                        "CONTRATO",
                        "PARCELA",
                        "DT_PGTO",
                        "PRINCIPAL",
                        "VALOR RECEBIDO",
                        "ST",
                        "DIAS_ATRASO",
                        "CPF/CNPJ",
                        "FILIAL",
                        "UF",
                        "PLANO_ACORDO",
                        "VENC_ORIGINAL",
                        "DATA_DO_ACORDO"
                    ]

                    mapa_colunas = {
                        "CODIGO": ["CODIGO", "ID"],
                        "CLIENTE": ["CLIENTE", "NOME", "NOME_CLIENTE", "NOME_DO_CLIENTE"],
                        "CONTRATO": ["CONTRATO"],
                        "PARCELA": ["PARCELA"],
                        "DT_PGTO": ["DT_PGTO", "DATA_PAGAMENTO", "DATA"],
                        "PRINCIPAL": ["PRINCIPAL"],
                        "VALOR RECEBIDO": ["VALOR RECEBIDO", "VALOR_PAGO", "VALOR"],
                        "ST": ["ST", "STATUS"],
                        "DIAS_ATRASO": ["DIAS_ATRASO", "ATRASO"],
                        "CPF/CNPJ": ["CPF/CNPJ", "CPF"],
                        "FILIAL": ["FILIAL", "NOME_FILIAL"],
                        "UF": ["UF", "ESTADO"],
                        "PLANO_ACORDO": ["PLANO_ACORDO", "PLANO"],
                        "VENC_ORIGINAL": ["VENC_ORIGINAL", "VENCIMENTO"],
                        "DATA_DO_ACORDO": ["DATA_DO_ACORDO", "DATA_ACORDO"]
                    }

                    df_visivel = df_filtrado.copy()

                    for col_padrao, possiveis in mapa_colunas.items():
                        for c in possiveis:
                            if c in df_visivel.columns:
                                df_visivel = df_visivel.rename(columns={c: col_padrao})
                                break

                    df_visivel = df_visivel.loc[
                        :, [c for c in COLUNAS_VISIVEIS if c in df_visivel.columns]
                    ]

                    # -------------------------
                    # Tabela detalhada (FINAL)
                    # -------------------------
                    st.markdown("### 📋 Detalhamento dos pagamentos")
                    st.dataframe(df_visivel, use_container_width=True)

                    # -------------------------
                    # Gráfico de pagamentos por data
                    # -------------------------
                    if col_data and col_valor and not df_filtrado.empty:
                        st.markdown("### 📈 Pagamentos por data")

                        pagamentos_dia = (
                            df_filtrado
                            .groupby(df_filtrado[col_data].dt.date)[col_valor]
                            .sum()
                            .reset_index()
                        )

                        pagamentos_dia.columns = ["DATA", "VALOR_PAGO"]

                        st.plotly_chart(
                            px.bar(
                                pagamentos_dia,
                                x="DATA",
                                y="VALOR_PAGO",
                                labels={"DATA": "Data", "VALOR_PAGO": "Valor Pago"},
                                title="Total pago por dia"
                            ),
                            use_container_width=True
                        )

                    # -------------------------
                    # Ranking por forma de pagamento
                    # -------------------------
                    if col_forma and col_valor and not df_filtrado.empty:
                        st.markdown("### 🏆 Valor pago por forma de pagamento")

                        tabela_forma = (
                            df_filtrado
                            .groupby(col_forma)[col_valor]
                            .sum()
                            .reset_index(name="VALOR_TOTAL")
                            .sort_values(by="VALOR_TOTAL", ascending=False)
                        )

                        st.dataframe(tabela_forma, use_container_width=True)
