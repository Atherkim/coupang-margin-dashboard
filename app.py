import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 기본 설정
st.set_page_config(page_title="로켓그로스 마진 대시보드", layout="wide")
st.title("🚀 쿠팡 로켓그로스 마진 분석 대시보드 (최종 자동화 버전)")

# 2. 사이드바 설정 (일괄 적용 메뉴)
with st.sidebar:
    st.header("1. 데이터 업로드")
    uploaded_file = st.file_uploader("재고 건전성 리포트 (CSV) 업로드", type=['csv', 'xlsx'])
    
    st.divider()
    st.header("2. 일괄 비용 설정")
    # 부가세 포함 여부 유지 (수수료+보관료 합산 금액에 적용)
    add_vat = st.checkbox(
        "수수료+보관료 합산 금액에 부가세(10%) 별도 가산", 
        value=True, 
        help="체크 시, 아래 표에서 입력하신 '수수료+물류비 합산' 금액에 1.1배가 곱해져서 계산됩니다."
    )

if uploaded_file is not None:
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df_actual = pd.read_csv(uploaded_file)
        else:
            df_actual = pd.read_excel(uploaded_file)
            
        # 첫 번째 행이 헤더가 아닐 경우를 대비해 '등록상품명'이 있는 행을 찾음
        if '등록상품명' not in df_actual.columns:
            st.error("잘못된 파일 양식입니다. 쿠팡에서 다운받은 '재고 건전성 리포트' 원본을 올려주세요.")
            st.stop()

        # 필요한 컬럼 정제 및 오류 방지 (NaN 제거)
        df_filtered = df_actual.dropna(subset=['등록상품명', '옵션 ID']).copy()
        
        # 3. [핵심 로직] 매출과 판매수량으로 '자동 판매가' 역산하기
        # 쿠팡 리포트 특성상 7일/30일 매출과 수량 컬럼이 Unnamed로 분리되는 점 반영
        col_rev_7 = '최근 매출 (번들 매출 제외)'
        col_rev_30 = 'Unnamed: 11'
        col_qty_7 = '최근 판매수량'
        col_qty_30 = 'Unnamed: 13'
        
        # 숫자형 데이터로 변환
        for col in [col_rev_7, col_rev_30, col_qty_7, col_qty_30]:
            if col in df_filtered.columns:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)
            else:
                df_filtered[col] = 0
                
        # 30일 기준으로 우선 계산하되, 30일 데이터가 없으면 7일 기준 사용
        df_filtered['자동_판매가'] = np.where(
            df_filtered[col_qty_30] > 0, df_filtered[col_rev_30] / df_filtered[col_qty_30],
            np.where(df_filtered[col_qty_7] > 0, df_filtered[col_rev_7] / df_filtered[col_qty_7], 0)
        )
        
        # '이번달 누적보관료' 추출 (컬럼 이름 간소화)
        if '이번달 누적보관료(전일자 기준)' in df_filtered.columns:
            df_filtered['월 누적보관료'] = pd.to_numeric(df_filtered['이번달 누적보관료(전일자 기준)'], errors='coerce').fillna(0)
        else:
            df_filtered['월 누적보관료'] = 0

        st.info("💡 '판매가'는 매출/수량 데이터를 통해 자동으로 계산되었습니다. (필요시 더블클릭하여 수정 가능)\n빈칸인 '매입원가'와 '수수료+보관료 합산' 금액만 입력해 주세요!")
        
        # 4. 사용자 입력용 데이터 뼈대 만들기
        unique_items = df_filtered[['옵션 ID', '등록상품명', '자동_판매가', '월 누적보관료']].drop_duplicates().reset_index(drop=True)
        
        df_input = unique_items.copy()
        df_input['판매가'] = df_input['자동_판매가'].round(0).astype(int) # 역산된 판매가 기본 세팅
        df_input['매입원가'] = 0
        df_input['수수료_물류비_합산'] = 0 # 수수료와 개별 보관료를 한 번에 입력하는 칸
        
        # st.data_editor를 통해 화면에서 직접 데이터 입력받기
        edited_df = st.data_editor(
            df_input,
            column_config={
                "옵션 ID": st.column_config.TextColumn("옵션 ID", disabled=True),
                "등록상품명": st.column_config.TextColumn("상품명", disabled=True),
                "자동_판매가": None, # 숨김 처리
                "월 누적보관료": st.column_config.NumberColumn("이번달 총 누적보관료 (참고용)", format="%d 원", disabled=True),
                "판매가": st.column_config.NumberColumn("판매가 (원)", format="%d"),
                "매입원가": st.column_config.NumberColumn("매입원가 (원)", format="%d"),
                "수수료_물류비_합산": st.column_config.NumberColumn("수수료+개별물류비 (원)", format="%d", help="건당 발생하는 수수료와 물류비를 합쳐서 입력하세요."),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 5. 마진 분석 로직
        vat_mult = 1.1 if add_vat else 1.0
        
        # 입력된 합산 부대비용에 부가세 적용
        edited_df['실제 부대비용'] = edited_df['수수료_물류비_합산'] * vat_mult
        
        # 마진 계산
        edited_df['총 비용'] = edited_df['매입원가'] + edited_df['실제 부대비용']
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
        
        # 6. 최종 분석 리포트 출력
        st.divider()
        st.subheader("📊 최종 분석 리포트")
        
        # 결과에 보여줄 컬럼 선택
        result_df = edited_df[['등록상품명', '월 누적보관료', '판매가', '매입원가', '실제 부대비용', '총 비용', '마진액', '마진율(%)', '목표 ROAS', '마진 판단']].copy()
        
        # 금액 데이터에 천 단위 콤마(,)와 '원' 붙이기
        money_cols = ['월 누적보관료', '판매가', '매입원가', '실제 부대비용', '총 비용', '마진액']
        for col in money_cols:
            result_df[col] = result_df[col].apply(lambda x: f"{int(x):,} 원")
        
        st.dataframe(result_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👈 왼쪽 사이드바에서 쿠팡 재고 건전성 리포트(CSV)를 업로드해 주세요.")
