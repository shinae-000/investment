import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import json

# 페이지 설정
st.set_page_config(page_title="주식 수급/가치 분석기", layout="wide")

st.title("📈 주식 수급 및 기술적 분석 대시보드")
st.sidebar.header("설정")

# 1. 종목 검색 함수
def get_stock_info(search_term):
    if search_term.isdigit() and len(search_term) == 6:
        return search_term, f"Code:{search_term}"
    url = f"https://ac.finance.naver.com/ac?q={search_term}&q_enc=utf-8&st=111&frm=stock&r_format=json&r_enc=utf-8&r_unicode=1&t_koreng=1"
    try:
        data = requests.get(url).json()
        items = data['items'][0]
        if items: return items[0][0][0], items[0][1][0]
    except: return None, None

# 2. UI 구성
target_name = st.sidebar.text_input("종목명 또는 코드 입력", value="큐리옥스바이오시스템즈")
months = st.sidebar.slider("분석 기간 (개월)", 1, 12, 6)

code, name = get_stock_info(target_name)

if code:
    st.subheader(f"🔍 {name} ({code}) 분석 결과")
    
    # 데이터 수집 (네이버 증권 크롤링)
    pages = months * 4
    df_list = []
    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/item/frgn.naver?code={code}&page={page}"
        tables = pd.read_html(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text)
        if len(tables) > 2:
            df_list.append(tables[2].dropna())
        else: break
    
    df = pd.concat(df_list).reset_index(drop=True)
    df.columns = ['날짜', '종가', '전일비', '등락률', '거래량', '기관순매매량', '외국인순매매량', '외국인보유주수', '외국인보유율']
    df['날짜'] = pd.to_datetime(df['날짜'])
    df = df.sort_values('날짜')
    
    # 지표 계산
    df['개인순매매량'] = -(df['외국인순매매량'] + df['기관순매매량'])
    df['MA20'] = df['종가'].rolling(20).mean()
    df['Upper'] = df['MA20'] + (df['종가'].rolling(20).std() * 2)
    df['Lower'] = df['MA20'] - (df['종가'].rolling(20).std() * 2)
    df['외인누적'] = df['외국인순매매량'].cumsum()
    df['기관누적'] = df['기관순매매량'].cumsum()
    df['개인누적'] = df['개인순매매량'].cumsum()
    
    plot_df = df.tail(months * 20)

    # 그래프 시각화
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        ax1.plot(plot_df['날짜'], plot_df['종가'], color='black', label='Price')
        ax1.fill_between(plot_df['날짜'], plot_df['Lower'], plot_df['Upper'], color='gray', alpha=0.1)
        ax1.legend()
        
        ax2.plot(plot_df['날짜'], plot_df['외인누적'], label='Foreign', color='blue')
        ax2.plot(plot_df['날짜'], plot_df['기관누적'], label='Inst.', color='green')
        ax2.plot(plot_df['날짜'], plot_df['개인누적'], label='Retail', color='red', linestyle='--')
        ax2.axhline(0, color='black', linewidth=0.5)
        ax2.legend()
        st.pyplot(fig)

    with col2:
        st.info("### 🤖 AI 분석 리포트")
        last_p = plot_df['종가'].iloc[-1]
        if last_p >= plot_df['Upper'].iloc[-1]:
            st.warning("⚠️ **단기 과열 상태**: 주가가 볼린저 밴드 상단을 이탈했습니다.")
        elif last_p <= plot_df['Lower'].iloc[-1]:
            st.success("✅ **과매도 구간**: 기술적 반등 가능성이 높은 자리입니다.")
        else:
            st.write("📊 현재 주가는 적정 범위 내에서 움직이고 있습니다.")
            
        if plot_df['외인누적'].iloc[-1] > plot_df['외인누적'].iloc[-5]:
            st.write("📈 **외국인 매집**: 최근 5일간 외국인의 순매수세가 강화되고 있습니다.")
else:
    st.error("종목을 찾을 수 없습니다.")
