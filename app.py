import streamlit as st
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="로켓그로스 마진 대시보드", layout="wide")
st.title("🚀 쿠팡 로켓그로스 마진 분석 대시보드 (Pro 버전)")

# 사이드바 설정
with st.sidebar:
    st.header("1. 데이터 업로드")
    uploaded_file = st.file_uploader("재고 건전성 리포트 (CSV) 업로드", type=['csv', 'xlsx'])
    
    st.divider()
    st.header("2. 비용 상세 설정")
    # 부가세(10%) 포함 여부 선택 (체크박스)
    add_vat = st.checkbox(
        "수수료 및 보관료에 부가세(10%) 별도 가산하기", 
        value=True, 
        help="쿠팡은 보통 부가세 별도로 비용을 청구합니다. 체크 시 입력하신 수수료율과 보관료에 1.1이 곱해져서 계산됩니다."
    )

if uploaded_file is not None:
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df_actual = pd.read_csv(uploaded_file)
        else:
            df_actual = pd.read_excel(uploaded_file)
            
        # 1. 파일에서 필수 데이터(옵션 ID, 상품명)만 추출하여 중복 제거
        if '옵션 ID' in df_actual.columns and '등록상품명' in df_actual.columns:
            unique_items = df_actual[['옵션 ID', '등록상품명']].drop_duplicates().reset_index(drop=True)
        else:
            st.error("업로드한 파일에 '옵션 ID' 또는 '등록상품명' 열이 없습니다.")
            st.stop()
        
        st.info("💡 아래 표의 빈칸(판매가, 원가, 수수료율, 보관료)을 더블 클릭하여 엑셀처럼 직접 숫자를 입력해 주세요.")
        
        # 2. 사용자 입력용 데이터 뼈대 만들기 (초기값 0 세팅)
        df_input = unique_items.copy()
        df_input['판매가'] = 0
        df_input['매입원가'] = 0
        df_input['판매수수료율(%)'] = 10.8
        df_input['예상 보관료'] = 0
        
        # st.data_editor를 통해 화면에서 직접 데이터 입력받기
        edited_df = st.data_editor(
            df_input,
            column_config={
                "옵션 ID": st.column_config.TextColumn("옵션 ID", disabled=True),
                "등록상품명": st.column_config.TextColumn("상품명", disabled=True),
                "판매가": st.column_config.NumberColumn("판매가", format="%d"),
                "매입원가": st.column_config.NumberColumn("매입원가", format="%d"),
                "판매수수료율(%)": st.column_config.NumberColumn("수수료율(%)", format="%.1f"),
                "예상 보관료": st.column_config.NumberColumn("보관료", format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 3. 마진 및 분석 지표 계산 로직
        # 부가세 옵션에 따른 배수 (체크 시 1.1, 해제 시 1.0)
        vat_mult = 1.1 if add_vat else 1.0
        
        # 실제 청구될 수수료 및 보관료 계산
        edited_df['실수수료'] = edited_df['판매가'] * (edited_df['판매수수료율(%)'] / 100) * vat_mult
        edited_df['실보관료'] = edited_df['예상 보관료'] * vat_mult
        
        # 총 비용 및 마진액
        edited_df['총 비용'] = edited_df['매입원가'] + edited_df['실수수료'] + edited_df['실보관료']
        edited_df['마진액'] = edited_df['판매가'] - edited_df['총 비용']
        
        # 마진율 계산
        edited_df['마진율(%)'] = np.where(edited_df['판매가'] > 0, 
                                        (edited_df['마진액'] / edited_df['판매가']) * 100, 
                                        0).round(1)
        
        # 목표 ROAS (손익분기점) = (판매가 / 마진액) * 100
        def calc_roas(row):
            if row['마진액'] > 0:
                return f"{(row['판매가'] / row['마진액'] * 100):.0f}%"
            else:
                return "🔴 적자 (광고불가)"
        
        edited_df['목표 ROAS'] = edited_df.apply(calc_roas, axis=1)
        
        # 마진 상태 평가 로직 (30% 이상: 좋음, 15% 이상: 보통, 그 미만: 나쁨)
        def eval_margin(margin):
            if margin >= 30: return "🟢 좋음"
            elif margin >= 15: return "🟡 보통"
            else: return "🔴 나쁨"
            
        edited_df['마진 판단'] = edited_df['마진율(%)'].apply(eval_margin)
        
        # 4. 결과 출력용 데이터프레임 정리 (단위금액 원화 콤마 처리)
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
