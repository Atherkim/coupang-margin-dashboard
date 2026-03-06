import streamlit as st
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="로켓그로스 마진 대시보드", layout="wide")
st.title("🚀 쿠팡 로켓그로스 마진 분석 대시보드 (Pro 버전)")

# 사이드바 설정 (일괄 적용 메뉴)
with st.sidebar:
    st.header("1. 데이터 업로드")
    uploaded_file = st.file_uploader("재고 건전성 리포트 (CSV) 업로드", type=['csv', 'xlsx'])
    
    st.divider()
    st.header("2. 일괄 비용 설정")
    # 👉 [수정됨] 전체 상품에 한 번에 적용되는 수수료율 조절기
    global_commission_rate = st.number_input(
        "전체 상품 일괄 판매수수료율 (%)", 
        value=10.8, 
        step=0.1, 
        help="이곳에서 수수료율을 변경하면 아래 모든 상품의 마진이 즉시 다시 계산됩니다."
    )
    
    add_vat = st.checkbox(
        "수수료 및 보관료에 부가세(10%) 별도 가산하기", 
        value=True, 
        help="쿠팡은 보통 부가세 별도로 비용을 청구합니다. 체크 시 수수료와 보관료에 1.1이 곱해집니다."
    )

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_actual = pd.read_csv(uploaded_file)
        else:
            df_actual = pd.read_excel(uploaded_file)
            
        if '옵션 ID' in df_actual.columns and '등록상품명' in df_actual.columns:
            unique_items = df_actual[['옵션 ID', '등록상품명']].drop_duplicates().reset_index(drop=True)
        else:
            st.error("업로드한 파일에 '옵션 ID' 또는 '등록상품명' 열이 없습니다.")
            st.stop()
        
        st.info("💡 아래 표에서 '판매가', '매입원가', '예상 보관료'를 더블 클릭하여 직접 입력해 주세요. (한 번 입력하신 판매가와 원가는 유지됩니다)")
        
        # 사용자 입력용 데이터 뼈대 만들기 (수수료율 열은 표에서 제거됨)
        df_input = unique_items.copy()
        df_input['판매가'] = 0
        df_input['매입원가'] = 0
        df_input['예상 보관료'] = 0
        
        # st.data_editor를 통해 화면에서 직접 데이터 입력받기
        edited_df = st.data_editor(
            df_input,
            column_config={
                "옵션 ID": st.column_config.TextColumn("옵션 ID", disabled=True),
                "등록상품명": st.column_config.TextColumn("상품명", disabled=True),
                "판매가": st.column_config.NumberColumn("판매가(원)", format="%d"),
                "매입원가": st.column_config.NumberColumn("매입원가(원)", format="%d"),
                "예상 보관료": st.column_config.NumberColumn("예상 보관료(원)", format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 부가세 옵션에 따른 배수
        vat_mult = 1.1 if add_vat else 1.0
        
        # 👉 [수정됨] 사이드바에서 설정한 '전체 수수료율'을 모든 상품에 일괄 적용
        edited_df['실수수료'] = edited_df['판매가'] * (global_commission_rate / 100) * vat_mult
        edited_df['실보관료'] = edited_df['예상 보관료'] * vat_mult
        
        edited_df['총 비용'] = edited_df['매입원가'] + edited_df['실수수료'] + edited_df['실보관료']
        edited_df['마진액'] = edited_df['판매가'] - edited_df['총 비용']
        
        edited_df['마진율(%)'] = np.where(edited_df['판매가'] > 0, 
                                        (edited_df['마진액'] / edited_df['판매가']) * 100, 
                                        0).round(1)
        
        # 목표 ROAS
        def calc_roas(row):
            if row['마진액'] > 0:
                return f"{(row['판매가'] / row['마진액'] * 100):.0f}%"
            else:
                return "🔴 적자 (광고불가)"
        
        edited_df['목표 ROAS'] = edited_df.apply(calc_roas, axis=1)
        
        # 마진 상태 평가 로직
        def eval_margin(margin):
            if margin >= 30: return "🟢 좋음"
            elif margin >= 15: return "🟡 보통"
            else: return "🔴 나쁨"
            
        edited_df['마진 판단'] = edited_df['마진율(%)'].apply(eval_margin)
        
        # 결과 출력용 데이터프레임 정리
        st.divider()
        st.subheader("📊 최종 분석 리포트")
        
        result_df = edited_df[['등록상품명', '판매가', '매입원가', '총 비용', '마진액', '마진율(%)', '목표 ROAS', '마진 판단']].copy()
        
        # 금액 데이터에 천 단위 콤마(,)와 '원' 붙이기
        money_cols = ['판매가', '매입원가', '총 비용', '마진액']
        for col in money_cols:
            result_df[col] = result_df[col].apply(lambda x: f"{int(x):,} 원")
        
        st.dataframe(result_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👈 왼쪽 사이드바에서 쿠팡 재고 건전성 리포트(CSV)를 업로드해 주세요.")
