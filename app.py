import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="로켓그로스 마진 대시보드", layout="wide")
st.title("🚀 쿠팡 로켓그로스 마진 분석 대시보드 (안정성 강화 버전)")

with st.sidebar:
    st.header("1. 데이터 업로드")
    uploaded_file = st.file_uploader("재고 건전성 리포트 (CSV) 업로드", type=['csv', 'xlsx'])
    
    st.divider()
    st.header("2. 일괄 비용 설정")
    add_vat = st.checkbox("수수료+보관료 합산 금액에 부가세(10%) 별도 가산", value=True)

if uploaded_file is not None:
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df_actual = pd.read_csv(uploaded_file)
        else:
            df_actual = pd.read_excel(uploaded_file)
            
        if '등록상품명' not in df_actual.columns:
            raise KeyError("파일 내에 '등록상품명' 컬럼이 존재하지 않습니다. 원본 엑셀 파일을 올려주세요.")

        df_filtered = df_actual.dropna(subset=['등록상품명', '옵션 ID']).copy()
        
        # 👉 [수정 1] 하드코딩 탈피: '매출'과 '판매수량' 관련 컬럼을 동적으로 찾기
        # '지난 30일'이라는 단어가 포함되거나, 가장 마지막에 위치한 관련 컬럼을 우선적으로 선택
        rev_cols = [c for c in df_filtered.columns if '매출' in str(c) or 'Unnamed: 11' in str(c)]
        qty_cols = [c for c in df_filtered.columns if '판매수량' in str(c) or 'Unnamed: 13' in str(c)]
        
        target_rev_col = rev_cols[-1] if rev_cols else None
        target_qty_col = qty_cols[-1] if qty_cols else None
        
        # 👉 [수정 2] 필요 컬럼 누락 시 친절한 경고 메시지 띄우기
        if not target_rev_col or not target_qty_col:
            st.warning("⚠️ 업로드하신 파일에서 '매출' 또는 '판매수량' 데이터를 찾을 수 없어, 자동 판매가 계산이 생략되었습니다.")
            df_filtered['자동_판매가'] = 0
        else:
            df_filtered[target_rev_col] = pd.to_numeric(df_filtered[target_rev_col], errors='coerce').fillna(0)
            df_filtered[target_qty_col] = pd.to_numeric(df_filtered[target_qty_col], errors='coerce').fillna(0)
            
            df_filtered['자동_판매가'] = np.where(
                df_filtered[target_qty_col] > 0, 
                df_filtered[target_rev_col] / df_filtered[target_qty_col], 
                0
            )

        # 누적보관료 찾기
        storage_col = [c for c in df_filtered.columns if '누적보관료' in str(c)]
        if storage_col:
            df_filtered['월 누적보관료'] = pd.to_numeric(df_filtered[storage_col[0]], errors='coerce').fillna(0)
        else:
            df_filtered['월 누적보관료'] = 0

        st.info("💡 '판매가'는 매출/수량 데이터를 통해 자동으로 계산되었습니다. 빈칸인 '매입원가'와 '수수료+보관료 합산' 금액만 입력해 주세요!")
        
        unique_items = df_filtered[['옵션 ID', '등록상품명', '자동_판매가', '월 누적보관료']].drop_duplicates().reset_index(drop=True)
        
        df_input = unique_items.copy()
        df_input['판매가'] = df_input['자동_판매가'].round(0).astype(int)
        df_input['매입원가'] = 0
        df_input['수수료_물류비_합산'] = 0
        
        edited_df = st.data_editor(
            df_input,
            column_config={
                "옵션 ID": st.column_config.TextColumn("옵션 ID", disabled=True),
                "등록상품명": st.column_config.TextColumn("상품명", disabled=True),
                "자동_판매가": None,
                "월 누적보관료": st.column_config.NumberColumn("이번달 총 누적보관료 (참고용)", format="%d 원", disabled=True),
                "판매가": st.column_config.NumberColumn("판매가 (원)", format="%d"),
                "매입원가": st.column_config.NumberColumn("매입원가 (원)", format="%d"),
                "수수료_물류비_합산": st.column_config.NumberColumn("수수료+개별물류비 (원)", format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        vat_mult = 1.1 if add_vat else 1.0
        edited_df['실제 부대비용'] = edited_df['수수료_물류비_합산'] * vat_mult
        
        edited_df['총 비용'] = edited_df['매입원가'] + edited_df['실제 부대비용']
        edited_df['마진액'] = edited_df['판매가'] - edited_df['총 비용']
        
        edited_df['마진율(%)'] = np.where(edited_df['판매가'] > 0, 
                                        (edited_df['마진액'] / edited_df['판매가']) * 100, 
                                        0).round(1)
        
        # 👉 [수정 5] 혼동 방지를 위해 ROAS 명칭 변경 (손익분기 ROAS)
        def calc_roas(row):
            if row['마진액'] > 0:
                return
