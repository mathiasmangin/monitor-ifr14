
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

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
    corpo = abs(df['Close'] - df['Open'])
    sombra_inferior = df[['Open', 'Close']].min(axis=1) - df['Low']
    return (sombra_inferior > corpo) & (corpo > 0)

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="Alerta IFR 14", layout="wide")
st.title("📈 Monitor de Ações - Alerta por IFR 14 (Brasil)")

acoes = st.multiselect("Selecione as ações da B3 para monitorar:", 
                       ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'WEGE3.SA', 'BBDC4.SA'],
                       default=['PETR4.SA', 'VALE3.SA'])

if st.button("🔍 Atualizar Alertas"):

    alertas = []
    tabela_resultados = []

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

    st.subheader("📊 Resultados:")
    df_resultados = pd.DataFrame(tabela_resultados)
    st.dataframe(df_resultados, use_container_width=True)

    if alertas:
        st.success("✅ Alertas de possível compra encontrados:")
        for alerta in alertas:
            st.write(alerta)
    else:
        st.warning("Nenhum alerta detectado com os critérios atuais.")

st.caption("Desenvolvido com 💻 por ChatGPT + Streamlit")
