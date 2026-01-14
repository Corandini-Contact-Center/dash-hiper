import streamlit as st
import pandas as pd
import os
import plotly.express as px
import datetime
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit as st

# =========================
# GOOGLE SHEETS - LOG ACESSOS
# =========================
SHEETS_CRED_PATH = r"C:\Users\Corandini\Documents\dash-hiper\credenciais.json"
SHEETS_NAME = "Log acessos DashHiper"
SHEETS_WORKSHEET = "Página1"


def registrar_log(usuario, acao="LOGIN"):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )

        gc = gspread.authorize(creds)
        sh = gc.open("Log acessos DashHiper")
        ws = sh.worksheet("Página1")

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ip = st.context.headers.get("X-Forwarded-For", "cloud")
        user_agent = st.context.headers.get("User-Agent", "desconhecido")

        ws.append_row([
            data_hora,
            usuario,
            ip,
            user_agent,
            acao
        ])

    except Exception as e:
        st.error(f"Erro ao registrar log de acesso: {e}")



# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Dashboard Hiper", layout="wide")

# =========================
# USUÁRIOS AUTORIZADOS
# =========================
USUARIOS = {
    "admin": "1234",
    "user1": "senha1"
}

# =========================
# FUNÇÃO DE LOGIN
# =========================
def login(usuario, senha):
    return usuario in USUARIOS and USUARIOS[usuario] == senha

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
            registrar_log(usuario, "LOGIN")
            st.success(f"Bem-vindo(a), {usuario}!")
        else:
            st.error("Usuário ou senha incorretos!")


import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

# =========================
# FUNÇÃO PARA REGISTRAR LOGIN
# =========================
def registrar_login(usuario):
    # Caminho para seu JSON de credenciais
    credenciais_path = r"C:\Users\Corandini\Documents\dash-hiper\credenciais.json"
    
    # Escopo para Google Sheets
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(credenciais_path, scopes=scope)
    
    # Abre a planilha
    gc = gspread.authorize(creds)
    sh = gc.open("log_acessos")  # Nome da planilha
    try:
        ws = sh.worksheet("acessos")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="acessos", rows=1000, cols=5)
    
    # Novo registro
    novo_registro = pd.DataFrame([{
        "usuario": usuario,
        "data_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # Lê dados existentes
    try:
        df_existente = pd.DataFrame(ws.get_all_records())
        df_atual = pd.concat([df_existente, novo_registro], ignore_index=True)
    except Exception:
        df_atual = novo_registro

    # Atualiza a planilha
    ws.clear()
    set_with_dataframe(ws, df_atual)



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
        "Importações": "importacoes"
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

    # =========================
    # CARREGA OS DADOS
    # =========================
    dados = carregar_dados()

    # =========================
    # EXIBIÇÃO POR ABAS
    # =========================
    abas = st.tabs(list(dados.keys()))

    for aba, nome in zip(abas, dados.keys()):
        with aba:
            df = dados[nome]

            # =========================
            # PADRONIZAÇÃO DE COLUNAS
            # =========================
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
                st.markdown("### 🔎 Filtros")

                col_vencto = next((c for c in df.columns if "VENCT" in c), None)
                col_data_acordo = next((c for c in df.columns if "INC" in c and "ACORD" in c), None)

                if col_vencto:
                    df[col_vencto] = pd.to_datetime(df[col_vencto], errors="coerce")
                if col_data_acordo:
                    df[col_data_acordo] = pd.to_datetime(df[col_data_acordo], errors="coerce")

                col_f1, col_f2, col_f3 = st.columns(3)
                col_f4, col_f5 = st.columns(2)

                with col_f1:
                    nome_cliente = st.text_input("Nome do cliente")

                with col_f2:
                    parcela = st.multiselect("Parcela", sorted(df["PARCELA"].dropna().unique()))

                with col_f3:
                    plano = st.multiselect("Plano", sorted(df["PLANO"].dropna().unique()))

                with col_f4:
                    if col_vencto:
                        vencto_range = st.date_input(
                            "Vencto",
                            value=(df[col_vencto].min(), df[col_vencto].max())
                        )

                with col_f5:
                    if col_data_acordo:
                        data_acordo_range = st.date_input(
                            "Data Inc. Acordo",
                            value=(df[col_data_acordo].min(), df[col_data_acordo].max())
                        )

                # =========================
                # APLICA FILTROS
                # =========================
                if nome_cliente:
                    df = df[df["NOME_DO_CLIENTE"].str.contains(nome_cliente, case=False, na=False)]
                if parcela:
                    df = df[df["PARCELA"].isin(parcela)]
                if plano:
                    df = df[df["PLANO"].isin(plano)]
                if col_vencto and len(vencto_range) == 2:
                    df = df[(df[col_vencto] >= pd.to_datetime(vencto_range[0])) &
                            (df[col_vencto] <= pd.to_datetime(vencto_range[1]))]
                if col_data_acordo and len(data_acordo_range) == 2:
                    df = df[(df[col_data_acordo] >= pd.to_datetime(data_acordo_range[0])) &
                            (df[col_data_acordo] <= pd.to_datetime(data_acordo_range[1]))]

                # =========================
                # CALENDÁRIO DE VENCIMENTOS
                # =========================
                if col_vencto:
                    st.markdown("### 📅 Calendário de vencimentos")

                    if "VLR_PARCELA" not in df.columns:
                        st.warning("Coluna VLR_PARCELA não encontrada!")
                    else:
                        df_sum = df.groupby(col_vencto)["VLR_PARCELA"].sum().reset_index(name="TOTAL_VLR")
                        df_count = df.groupby(col_vencto).size().reset_index(name="QTDE_ACORDOS")
                        df_count["TOTAL_VLR"] = df_sum["TOTAL_VLR"]

                        start_date = df_count[col_vencto].min()
                        end_date = df_count[col_vencto].max()
                        start_date -= datetime.timedelta(days=start_date.weekday())
                        end_date += datetime.timedelta(days=(6 - end_date.weekday()))

                        all_dates = pd.date_range(start_date, end_date)
                        count_dict = dict(zip(df_count[col_vencto], df_count["QTDE_ACORDOS"]))
                        value_dict = dict(zip(df_count[col_vencto], df_count["TOTAL_VLR"]))
                        cell_values = [(d, count_dict.get(d, 0), value_dict.get(d, 0)) for d in all_dates]
                        weeks = [cell_values[i:i+7] for i in range(0, len(cell_values), 7)]
                        calendar_df = pd.DataFrame(
                            data=[[f"{day.day:02d}/{day.month:02d} ({q} | {v:,.2f})" for (day, q, v) in week] for week in weeks],
                            columns=["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
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
                        filter_qual = st.multiselect(
                            "Qualificação",
                            sorted(df["QUALIFICATION"].dropna().unique())
                        ) if "QUALIFICATION" in df.columns else None

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
