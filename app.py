import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="로켓그로스 마진 대시보드", layout="wide")
st.title("🚀 쿠팡 로켓그로스 마진 분석 대시보드")

with st.sidebar:
    st.header("📁 데이터 업로드")
    uploaded_file = st.file_uploader("재고 건전성 리포트 (CSV) 업로드", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_actual = pd.read_csv(uploaded_file)
        else:
            df_actual = pd.read_excel(uploaded_file)
            
        cols_to_keep = ['옵션 ID', '등록상품명', '이번달 누적보관료(전일자 기준)', '판매가능재고 (실시간 기준)']
        existing_cols = [col for col in cols_to_keep if col in df_actual.columns]
        df_filtered = df_actual[existing_cols].dropna(subset=['옵션 ID'])
        
        # 임시 마스터 DB (나중에는 사용자가 직접 입력/수정하도록 업그레이드 가능)
        np.random.seed(42)
        df_master = pd.DataFrame({
            '옵션 ID': df_filtered['옵션 ID'].unique(),
            '예상 판매가': np.random.randint(10000, 30000, size=len(df_filtered['옵션 ID'].unique())),
            '예상 매입원가': np.random.randint(3000, 8000, size=len(df_filtered['옵션 ID'].unique()))
        })
        
        df_merged = pd.merge(df_filtered, df_master, on='옵션 ID', how='left')
        df_merged['보관료'] = pd.to_numeric(df_merged.get('이번달 누적보관료(전일자 기준)', 0), errors='coerce').fillna(0)
        df_merged['임시 순이익'] = df_merged['예상 판매가'] - df_merged['예상 매입원가'] - df_merged['보관료']
        
        col1, col2, col3 = st.columns(3)
        col1.metric("분석 상품 수", f"{len(df_merged)} 개")
        col2.metric("총 보관료", f"{int(df_merged['보관료'].sum()):,} 원")
        col3.metric("총 예상 순이익", f"{int(df_merged['임시 순이익'].sum()):,} 원")
        
        st.divider()
        st.subheader("📝 마진 데이터베이스")
        st.dataframe(df_merged[['등록상품명', '예상 판매가', '예상 매입원가', '보관료', '임시 순이익']], use_container_width=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
else:
    st.info("👈 왼쪽 사이드바에서 파일을 업로드해 주세요.")
