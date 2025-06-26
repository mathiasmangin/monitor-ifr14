import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# ----------------------------
# Funções de cálculo
# ----------------------------
def calcular_ifr(df, periodo=14):
    delta = df['Close'].diff()
    ganhos = delta.clip(lower=0)
    perdas = -delta.clip(upper=0)
    media_ganhos = ganhos.rolling(periodo).mean()
    media_perdas = perdas.rolling(periodo).mean()
    rs = media_ganhos / media_perdas
    return 100 - (100 / (1 + rs))

def candle_reversao(df):
    corpo = abs(df['Close'].astype(float) - df['Open'].astype(float))
    
    min_open_close = df[['Open', 'Close']].min(axis=1)
    if isinstance(min_open_close, pd.DataFrame):
        min_open_close = min_open_close.iloc[:, 0]
    else:
        min_open_close = min_open_close.squeeze()
    
    sombra_inferior = min_open_close.astype(float) - df['Low'].astype(float)
    
    resultado = (sombra_inferior > corpo) & (corpo > 0)
    
    return pd.Series(resultado.values, index=df.index)

def enviar_email(mensagem):
    # Configure com seus dados reais
    remetente = "SEU_EMAIL@gmail.com"
    senha = "SUA_SENHA_DE_APP"
    destinatario = "DESTINATARIO@gmail.com"
    try:
        msg = MIMEText(mensagem, 'plain', 'utf-8')
        msg['Subject'] = f'Alerta IFR 14 - {datetime.today().date()}'
        msg['From'] = remetente
        msg['To'] = destinatario

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remetente, senha)
            smtp.send_message(msg)
        return True
    except Exception as e:
        return False

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="Alerta IFR 14", layout="wide")
st.title("📈 Monitor de Ações - IFR 14 + Gráfico + E-mail")

acoes = st.multiselect("Selecione as ações da B3 para monitorar:", 
                       ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'WEGE3.SA', 'BBDC4.SA'],
                       default=['PETR4.SA', 'VALE3.SA'])

mostrar_grafico = st.checkbox("📉 Mostrar gráfico de Preço + IFR", value=True)

if st.button("🔍 Atualizar Alertas"):

    alertas = []
    tabela_resultados = []
    graficos = {}

    for acao in acoes:
        df = yf.download(acao, period="3mo", interval="1d")
        if df.empty:
            continue

        df['RSI_14'] = calcular_ifr(df)
        df['MME21'] = df['Close'].ewm(span=21).mean()
        df['Media_Volume_20'] = df['Volume'].rolling(20).mean()
        df['Candle_Reversao'] = candle_reversao(df)

        ult = df.iloc[-1]
        penult = df.iloc[-2]

        cond_ifr = ult['RSI_14'] < 30 and penult['RSI_14'] >= 30
        cond_mme = ult['Close'] >= ult['MME21']
        cond_volume = ult['Volume'] >= ult['Media_Volume_20']
        cond_candle = ult['Candle_Reversao']

        if cond_ifr and cond_mme and cond_volume and cond_candle:
            alertas.append(f"🔔 {acao} | IFR: {ult['RSI_14']:.2f} | Preço: R${ult['Close']:.2f}")

        tabela_resultados.append({
            'Ação': acao,
            'Preço': round(ult['Close'], 2),
            'IFR 14': round(ult['RSI_14'], 2),
            'MME21': round(ult['MME21'], 2),
            'Volume OK': '✅' if cond_volume else '',
            'Reversão?': '✅' if cond_candle else '',
            'Alerta?': '✅' if cond_ifr and cond_mme and cond_volume and cond_candle else ''
        })

        if mostrar_grafico:
            graficos[acao] = df[['Close', 'RSI_14']].dropna().tail(30)

    st.subheader("📊 Resultados:")
    df_resultados = pd.DataFrame(tabela_resultados)
    st.dataframe(df_resultados, use_container_width=True)

    if alertas:
        st.success("✅ Alertas de possível compra encontrados:")
        for alerta in alertas:
            st.write(alerta)

        if st.button("📧 Enviar alertas por e-mail"):
            corpo = "\n".join(alertas)
            enviado = enviar_email(corpo)
            if enviado:
                st.success("E-mail enviado com sucesso!")
            else:
                st.error("Erro ao enviar o e-mail. Verifique configurações.")
    else:
        st.warning("Nenhum alerta detectado com os critérios atuais.")

    if mostrar_grafico and graficos:
        st.subheader("📉 Gráficos de Preço e IFR 14 (últimos 30 dias)")
        for acao, dados in graficos.items():
            st.write(f"**{acao}**")
            fig, ax1 = plt.subplots()
            ax2 = ax1.twinx()
            ax1.plot(dados.index, dados['Close'], color='blue', label='Preço')
            ax2.plot(dados.index, dados['RSI_14'], color='green', label='IFR 14')
            ax1.set_ylabel('Preço', color='blue')
            ax2.set_ylabel('IFR 14', color='green')
            st.pyplot(fig)

st.caption("Desenvolvido com 💻 por ChatGPT + Streamlit")
