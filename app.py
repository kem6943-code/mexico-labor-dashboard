# -*- coding: utf-8 -*-
"""
🇲🇽 멕시코 법인 인건비 분석 대시보드
"""

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from parsers import (
    parse_employee_catalog,
    load_all_payroll_files,
    merge_weekly_to_monthly,
    calculate_summary_stats,
    format_mxn,
    format_krw,
    MXN_TO_KRW_RATE,
)

# 사이드바 충돌을 막기 위해 애초에 collapsed 상태로 시작
st.set_page_config(page_title="멕시코 법인 인건비 분석", page_icon="🇲🇽", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* 전체 배경을 라이트 그레이(Soft UI)로 전환 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    
    .stApp, [data-testid="stAppViewContainer"], .main { background-color: #F7F9FC !important; }
    .stApp, p, h1, h2, h3, h4, h5, h6, label, table, th, td { 
        font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important; 
    }
    
    /* 1. Streamlit 순정 사이드바 및 햄버거 토글 영구 박멸 */
    [data-testid="stSidebar"] { display: none !important; width: 0 !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"], [data-testid="stHeader"] > header { background-color: transparent !important; }
    .stDeployButton, [data-testid="stToolbar"] { display: none !important; }
    .block-container { padding-top: 1.5rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100% !important; }
    
    /* 2. 2단 레이아웃 좌측 메뉴(첫 번째 컬럼) 너비 240px 보정 (option-menu 적용) */
    [data-testid="column"]:first-child {
        min-width: 240px !important;
        max-width: 240px !important;
        width: 240px !important;
        flex: 0 0 240px !important;
        border-right: 1px solid #EAEAEA;
        padding-right: 16px;
        margin-right: 24px;
        height: 100vh;
        position: sticky;
        top: 0;
    }
    
    /* ==========================================================
       사이드바 어드밴스드 미니멀리즘 커스텀 (Reference App Style)
       ========================================================== */
    [data-testid="column"]:nth-child(1) {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
        padding: 24px 16px 24px 8px !important;
    }
    
    div[data-testid="stExpander"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stExpander"] > details {
        border: none !important;
    }
    div[data-testid="stExpander"] summary {
        padding: 8px 12px !important;
        color: #4B5563 !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] summary:hover {
        background-color: #F9FAFB !important;
        border-radius: 6px !important;
    }
    div[data-testid="stExpander"] summary svg {
        color: #9CA3AF !important; 
    }
    .streamlit-expanderContent {
        padding-left: 0px !important; 
        border: none !important;
        padding-bottom: 0px !important;
    }

    .stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #6B7280 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 8px 12px 8px 36px !important; /* 들여쓰기 */
        width: 100% !important;
        display: flex !important;
        justify-content: flex-start !important;
        border-radius: 6px !important;
        min-height: 38px !important;
        transition: all 0.2s ease-in-out;
        margin-bottom: 2px !important;
    }
    .stButton > button:hover {
        background: #F9FAFB !important;
        color: #111827 !important;
    }
    
    /* Active State (선택된 메뉴) - 아주 연한 회색 배경, 굵은 텍스트 */
    .stButton > button[kind="primary"] {
        background: #F3F4F6 !important;
        color: #111827 !important;
        font-weight: 700 !important;
    }

    

    
    /* 우측 메인 대시보드 컨테이너 박스 섀도우 유지 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important; border-radius: 12px !important; border: 1px solid #F0F0F0 !important; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025) !important; padding: 32px !important; margin-bottom: 32px !important;
    }
    
    /* ==========================================================
       하단 데이터 표 (Custom HTML Table) 스타일링
       ========================================================== */
       
    .custom-table-wrapper {
        border-radius: 8px; border: 1px solid #EAEAEA; overflow: hidden;
    }
    table.custom-table { 
        width: 100%; border-collapse: collapse; font-size: 13px; text-align: right; 
    }
    table.custom-table th { 
        background-color: #FAFAFA; color: #595959; font-weight: 600; padding: 12px 16px; 
        border-bottom: 1px solid #EAEAEA; text-align: center; 
    }
    table.custom-table td { 
        padding: 12px 16px; border-bottom: 1px solid #F0F0F0; color: #262626; 
    }
    table.custom-table tbody tr:hover { background-color: #F8F9FA; }
    table.custom-table td:first-child, table.custom-table th:first-child { text-align: left; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data_fresh(data_dir: str):
    # Cache busted securely for v4 float NaN defense logic
    results = {}
    catalog_path = os.path.join(data_dir, 'Catalogo de Empleados.xlsx')
    results['employees'] = parse_employee_catalog(catalog_path) if os.path.exists(catalog_path) else pd.DataFrame()
    payroll_data = load_all_payroll_files(data_dir)
    results['monthly'] = merge_weekly_to_monthly(payroll_data)
    return results

def _find_data_dir() -> str:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    data_sub = os.path.join(app_dir, 'data')
    if os.path.isdir(data_sub): return data_sub
    parent = os.path.dirname(app_dir)
    if os.path.exists(os.path.join(parent, 'Catalogo de Empleados.xlsx')): return parent
    return app_dir

@st.fragment
def render_date_picker(valid_yms):
    if not valid_yms: return
    
    if 'start_ym' not in st.session_state: st.session_state.start_ym = valid_yms[0]
    if 'end_ym' not in st.session_state: st.session_state.end_ym = valid_yms[-1]
    
    if 'temp_start_ym' not in st.session_state: st.session_state.temp_start_ym = st.session_state.start_ym
    if 'temp_end_ym' not in st.session_state: st.session_state.temp_end_ym = str(st.session_state.end_ym)
    if 'picker_view_year' not in st.session_state: 
        safe_ym = str(st.session_state.end_ym)
        st.session_state.picker_view_year = int(safe_ym.split('-')[0]) if '-' in safe_ym else 2026

    btn_label = f"📅 {st.session_state.start_ym.replace('-','.')} ~ {st.session_state.end_ym.replace('-','.')}" if st.session_state.start_ym != st.session_state.end_ym else f"📅 {st.session_state.start_ym.replace('-','.')}"
    
    with st.popover(btn_label, use_container_width=True):
        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button("❮", key="pd_prev", use_container_width=True):
            st.session_state.picker_view_year -= 1
            st.rerun(scope="fragment")
        c2.markdown(f"<div style='text-align:center; font-weight:700; font-size:16px; padding-top:6px;'>{st.session_state.picker_view_year}년</div>", unsafe_allow_html=True)
        if c3.button("❯", key="pd_next", use_container_width=True):
            st.session_state.picker_view_year += 1
            st.rerun(scope="fragment")
            
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        
        for r in range(3):
            cols = st.columns(4)
            for c in range(4):
                m = r * 4 + c + 1
                ym = f"{st.session_state.picker_view_year}-{m:02d}"
                
                is_start = (ym == st.session_state.temp_start_ym)
                is_end = (ym == st.session_state.temp_end_ym)
                btn_type = "primary" if (is_start or is_end) else "secondary"
                
                if cols[c].button(f"{m}월", key=f"btn_{ym}", type=btn_type, use_container_width=True):
                    if st.session_state.temp_start_ym and st.session_state.temp_end_ym:
                        st.session_state.temp_start_ym = ym
                        st.session_state.temp_end_ym = None
                    elif st.session_state.temp_start_ym and not st.session_state.temp_end_ym:
                        if ym >= st.session_state.temp_start_ym:
                            st.session_state.temp_end_ym = ym
                        else:
                            st.session_state.temp_end_ym = st.session_state.temp_start_ym
                            st.session_state.temp_start_ym = ym
                    else:
                        st.session_state.temp_start_ym = ym
                    st.rerun(scope="fragment")
                    
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        if st.button("선택 적용", type="primary", use_container_width=True):
            if st.session_state.temp_start_ym:
                st.session_state.start_ym = st.session_state.temp_start_ym
                st.session_state.end_ym = st.session_state.temp_end_ym if st.session_state.temp_end_ym else st.session_state.temp_start_ym
            st.rerun()

def render_ceo_insight_panel(dept_name, monthly_df_full, cost_mxn, ot_mxn, ot_ratio):
    # CEO 용 분석 텍스트 생성기
    insight_text = ""
    
    if dept_name == '전체':
        # 부서별 OT비용 누수 분석
        if not monthly_df_full.empty and '초과근무수당' in monthly_df_full.columns and '총지급액' in monthly_df_full.columns:
            dept_ot = monthly_df_full.groupby('부서').agg(
                수당=('초과근무수당', 'sum'), 총지급액=('총지급액', 'sum')
            )
            dept_ot = dept_ot[dept_ot['총지급액'] > 0]
            if not dept_ot.empty:
                dept_ot['OT비율'] = dept_ot['수당'] / dept_ot['총지급액'] * 100
                max_ot_dept = dept_ot['OT비율'].idxmax()
                max_ot_val = dept_ot['OT비율'].max()
                
                insight_text = f"현재 멕시코 법인 평균 OT 비율은 <b>{ot_ratio:.1f}%</b> 수준입니다. 주목할 점은 <b>{max_ot_dept}</b> 부서에서 전례 없는 OT 비중(<b><span style='color:#CF1322'>{max_ot_val:.1f}%</span></b>)이 감지되었다는 것입니다. 해당 제조 공정의 생산량 목표와 실투입 인력 간의 불균형이 의심되니 확인이 필요합니다."
    else:
        if ot_ratio > 10.0:
            insight_text = f"🚨 <b>경고:</b> {dept_name} 부서의 최신 OT 비율이 <b><span style='color:#CF1322'>{ot_ratio:.1f}%</span></b>를 초과하여 임계치(10%)를 돌파했습니다! 단순 야근 결재를 넘어, 작업 프로세스 지연이나 특정 직군의 롤 플로(Role flow) 문제가 발생했는지 현장 리더를 통한 진단이 시급합니다."
        else:
             insight_text = f"✅ {dept_name} 부서의 현재 OT 비율은 <b>{ot_ratio:.1f}%</b>로 건전한 예산 효율성을 보이고 있습니다. 지난달과 비교하여 추가적인 인건비 지출 리스크는 발견되지 않았습니다."

    if not insight_text:
        insight_text = "데이터 수집 부족으로 브리핑을 제공할 수 없습니다."

    st.markdown(f"""
    <div style="background-color: #FFFFFF; border: 1px solid rgba(234, 238, 243, 0.8); box-shadow: 0 4px 16px rgba(29, 53, 87, 0.04); border-radius: 12px; padding: 24px; margin-bottom: 24px;">
        <h4 style="margin:0 0 12px 0; color: #1D3557; font-size: 16px; font-weight: 700; display:flex; align-items:center; gap:8px;">
            <span style="font-size:20px;">💡</span> CEO 인사이트 브리핑
        </h4>
        <p style="margin:0; font-size: 14.5px; color: #434343; line-height: 1.6; letter-spacing: -0.3px;">
            {insight_text}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_html(title, value, unit, target_text, var_text=""):
    # 경고 텍스트(*)가 있으면 경고색(#E76F51), 플러스는 초록(#2A9D8F)
    if "*" in var_text:
        var_color = "#E76F51" # Soft Red/Orange
    elif "+" in var_text:
        var_color = "#2A9D8F" # Soft Green
    elif "-" in var_text and var_text != "-":
        var_color = "#E76F51"
    else:
        var_color = "#BFBFBF" # 기본
        
    trend_html = f"<span style='color: {var_color}; font-weight: 600;'>{var_text}</span>" if var_text else ""
    pipe_html = "<span style='color:#EAEAEA; margin:0 6px;'>|</span>" if trend_html else ""
        
    return f"""<div style="background-color: white; border-radius: 12px; padding: 24px; border: 1px solid rgba(234, 238, 243, 0.8); box-shadow: 0 4px 16px rgba(29, 53, 87, 0.04); height: 100%;">
<div style="font-size: 13.5px; color: #8C8C8C; font-weight: 600; margin-bottom: 12px; letter-spacing: -0.2px;">{title}</div>
<div style="display: flex; align-items: baseline; gap: 6px;">
<div style="font-size: 26px; font-weight: 800; color: #1D3557; line-height: 1.1;">{value}</div>
<div style="font-size: 13.5px; color: #8C8C8C; font-weight: 500;">{unit}</div>
</div>
<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 18px; font-size: 13px; color: #8C8C8C; font-weight: 500;">
<div style="display:flex; align-items:center;">
<span>{target_text}</span>{pipe_html}
</div>{trend_html}
</div>
</div>"""

def render_kpi_dashboard(dept_name, monthly_df_full, employee_df_full):
    # NaN 결측치 처리 및 문자열 명시적 변환 (float 객체 split() 에러 원천 차단)
    if 'YearMonth' not in monthly_df_full.columns:
        monthly_df_full['YearMonth'] = '2026-01'
        
    # 데이터 상의 결측치를 2026-01로 채우고 전부 안전한 str형으로 캐스팅
    monthly_df_full['YearMonth'] = monthly_df_full['YearMonth'].fillna('2026-01').astype(str).str.strip()
    
    # 'Unknown'이나 'nan' 등 쓰레기 값을 pd.to_datetime을 통해 검증 후 통일된 포맷 변환
    monthly_df_full.loc[monthly_df_full['YearMonth'].str.lower().isin(['unknown', 'nan', 'nat', '']), 'YearMonth'] = '2026-01'
    temp_dates = pd.to_datetime(monthly_df_full['YearMonth'], errors='coerce')
    monthly_df_full['YearMonth'] = temp_dates.dt.strftime('%Y-%m').fillna('2026-01')
    
    valid_yms = sorted([y for y in monthly_df_full['YearMonth'].unique()])
    if not valid_yms:
        valid_yms = ['2026-01']
        
    # 캐시/세션에 남아있는 잘못된 과거 데이터('Unknown') 강제 리셋 (Auto-Heal)
    if st.session_state.get('start_ym') not in valid_yms: 
        st.session_state.start_ym = valid_yms[0]
    if st.session_state.get('end_ym') not in valid_yms: 
        st.session_state.end_ym = valid_yms[-1]
    
    start_ym = st.session_state.start_ym
    end_ym = st.session_state.end_ym

    # 선택된 범위 데이터 필터링
    start_ym = str(start_ym)
    end_ym = str(end_ym)
    mask = (monthly_df_full['YearMonth'] >= start_ym) & (monthly_df_full['YearMonth'] <= end_ym)
    df_period = monthly_df_full[mask].copy()
    
    dept_filter = '멕시코 전체' if dept_name == '전체' else dept_name
    
    if dept_filter == '멕시코 전체':
        df = df_period.copy()
        emp = employee_df_full.copy()
        hist_df = monthly_df_full.copy() # 차트는 전체 히스토리 보존
    else:
        df = df_period[df_period['부서'] == dept_filter].copy()
        emp = employee_df_full[employee_df_full['부서'] == dept_filter].copy() if '부서' in employee_df_full.columns else pd.DataFrame()
        hist_df = monthly_df_full[monthly_df_full['부서'] == dept_filter].copy()
        
    stats = calculate_summary_stats(df, emp)
    
    cost_mxn = stats.get('total_labor_cost', 0)
    earn_mxn = stats.get('total_earnings', 0)
    ot_mxn = df['초과근무수당'].sum() if '초과근무수당' in df.columns else 0
    fte_val = stats.get('total_fte', 0)
    
    # 평균화를 위해 선택된 개월 수 계산
    period_months = len(df['YearMonth'].unique()) if not df.empty and start_ym != 'Unknown' else 1
    period_months = max(1, period_months)
    
    # 인원수/FTE는 기간 전체를 합치면 뻥튀기 되므로 월평균으로 보정
    headcount = stats.get('total_headcount', 0) / period_months
    fte_val = fte_val / period_months
    
    ot_ratio = (ot_mxn / earn_mxn * 100) if earn_mxn > 0 else 0
    dummy_target = cost_mxn / 1.05 if cost_mxn > 0 else 1
    budget_ratio = (cost_mxn / dummy_target) * 100
    
    # 타이틀 라인 렌더링 (Streamlit columns 사용)
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
    c_title, c_picker = st.columns([3, 1])
    with c_title:
        st.markdown("<h1 style='margin: 0; font-size: 28px; font-weight: 800; color: #1D3557; letter-spacing: -0.5px;'>멕시코 법인 인건비 분석</h1>", unsafe_allow_html=True)
    with c_picker:
        # 여기서 Custom Date Picker Popover 주입
        render_date_picker(valid_yms)
        
    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
    
    render_ceo_insight_panel(dept_name, df_period, cost_mxn, ot_mxn, ot_ratio)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(render_kpi_html("부서 총 인원", f"{headcount:.1f}", "명", f"FTE: {fte_val:.1f}명"), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_html("부서 총 인건비", f"{int(cost_mxn/1000):,}", "천 MXN", f"~W{format_krw(cost_mxn * MXN_TO_KRW_RATE).replace('KRW','').strip()}", "+1.4%"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_html("평균 OT 비율", f"{ot_ratio:.1f}", "%", f"지출액: {int(ot_mxn):,} MXN"), unsafe_allow_html=True)
    with c4: st.markdown(render_kpi_html("OT 지출액", f"{int(ot_mxn/1000):,}", "천 MXN", "예산범위내"), unsafe_allow_html=True)
    with c5: st.markdown(render_kpi_html("목표 대비 인건비", f"{budget_ratio:.1f}", "%", f"목표: {int(dummy_target/1000):,} 천 MXN", "* 4.8%"), unsafe_allow_html=True)
    
    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        col_t, col_b, col_u = st.columns([6, 2, 1])
        with col_t: st.markdown("<div style='font-size: 16px; font-weight: 700; color: #1D3557; padding: 5px 0;'>📊 월별 인건비 및 OT 추이</div>", unsafe_allow_html=True)
        with col_b: st.markdown("<div style='display:flex; justify-content:flex-end;'><button style='background:#F7F9FC; border:1px solid rgba(234,238,243,0.8); padding:6px 16px; border-radius:6px; font-size:13px; color:#1D3557; font-weight:600;'>추이 보기</button></div>", unsafe_allow_html=True)
        with col_u: st.markdown("<div style='font-size: 12px; color: #8C8C8C; text-align:right; padding-top:8px;'>단위: 천 MXN / %</div>", unsafe_allow_html=True)
            
        if not hist_df.empty and 'YearMonth' in hist_df.columns:
            hist_valid = hist_df[hist_df['YearMonth'] != 'Unknown'].copy()
            if not hist_valid.empty:
                # 총지급액과 총회사부담금을 분리하여 없으면 0으로 처리, 합해서 총 인건비 계산
                hist_valid['기본합'] = hist_valid['총지급액'] if '총지급액' in hist_valid.columns else 0
                hist_valid['부담합'] = hist_valid['총회사부담금'] if '총회사부담금' in hist_valid.columns else 0
                hist_valid['수당합'] = hist_valid['초과근무수당'] if '초과근무수당' in hist_valid.columns else 0
                
                trend_grouped = hist_valid.groupby('YearMonth').agg(
                    총지급액=('기본합', 'sum'),
                    회사부담금=('부담합', 'sum'),
                    수당=('수당합', 'sum')
                ).reset_index()
                
                trend_grouped['총비용'] = trend_grouped['총지급액'] + trend_grouped['회사부담금']
                trend_grouped['OT비율'] = (trend_grouped['수당'] / trend_grouped['총지급액'] * 100).fillna(0)
                trend_grouped['총비용(천)'] = trend_grouped['총비용'] / 1000
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                # 네이비 블루 모던 바 차트
                fig.add_trace(go.Bar(x=trend_grouped['YearMonth'], y=trend_grouped['총비용(천)'], name="총 인건비 (MXN)", width=0.15, marker=dict(color="#1D3557")), secondary_y=False)
                # 부드러운 오렌지/레드 트렌드 라인
                fig.add_trace(go.Scatter(x=trend_grouped['YearMonth'], y=trend_grouped['OT비율'], name="OT 비율 (%)", mode='lines+markers', line=dict(color="#E76F51", width=2), marker=dict(size=6, color="#E76F51", line=dict(width=1.5, color="white"))), secondary_y=True)
                
                fig.update_layout(height=400, margin=dict(t=40, b=30, l=40, r=40), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=13, color="#595959")), barmode='group')
                fig.update_yaxes(showgrid=True, gridcolor="rgba(234, 238, 243, 0.8)", tickfont=dict(size=12, color="#8C8C8C"), secondary_y=False)
                fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color="#E76F51"), secondary_y=True, ticksuffix="%")
                fig.update_xaxes(showline=True, linecolor="rgba(234, 238, 243, 0.8)", tickfont=dict(size=13, color="#8C8C8C"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("<div style='padding: 40px; text-align: center; color: #8C8C8C; font-size: 14px;'>과거 누적 트렌드 데이터가 존재하지 않습니다.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding: 40px; text-align: center; color: #8C8C8C; font-size: 14px;'>과거 누적 트렌드 데이터가 존재하지 않습니다.</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    # 하단 컨트롤 바 영역
    with st.container():
        c_btn, c_chk, c_unit = st.columns([2, 5, 3])
        with c_btn:
            st.button("📥 엑셀 파일 연동", use_container_width=True)
        with c_chk:
            chk1, chk2 = st.columns(2)
            chk1.checkbox("TD목표 대비 보기", value=True)
            chk2.checkbox("'25년 대비 보기", value=True)
        with c_unit:
            st.markdown("<div style='text-align:right; padding-top:8px; font-size:13px; color:#8C8C8C; font-weight:500;'>단위: 백만 MXN</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        t1, t2 = st.columns([8, 2])
        with t1: st.markdown(f"<div style='font-size: 16px; font-weight: 700; color: #262626; padding-top:4px;'>📋 {dept_name} 직위별 인건비 상세 분포 (레드라인 알럿)</div>", unsafe_allow_html=True)
        with t2: st.markdown("<div style='font-size: 13px; color: #BFBFBF; text-align:right; padding-top:8px;'>단위: MXN</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:16px 0 24px 0; border:none; border-top:1px solid #F0F0F0;'>", unsafe_allow_html=True)
        
        if not df.empty:
            if '직위' in emp.columns and '사원번호' in df.columns:
                emp_dedup = emp[['사원번호', '직위']].drop_duplicates(subset=['사원번호']).copy()
                df_merge = df.copy()
                df_merge['사원번호'] = df_merge['사원번호'].astype(str)
                emp_dedup['사원번호'] = emp_dedup['사원번호'].astype(str)
                
                tbl_df = df_merge.merge(emp_dedup, on='사원번호', how='left')
                tbl_df['직위'] = tbl_df['직위'].fillna('미분류')
            else:
                tbl_df = df.copy()
                tbl_df['직위'] = '미분류'
                
            tbl_df['기본급'] = tbl_df['기본급'] if '기본급' in tbl_df.columns else 0
            tbl_df['초과근무수당'] = tbl_df['초과근무수당'].fillna(0) if '초과근무수당' in tbl_df.columns else 0
            tbl_df['합계'] = tbl_df['총인건비'] if '총인건비' in tbl_df.columns else tbl_df['총지급액']
            
            grouped = tbl_df.groupby('직위').agg(
                인원=('사원번호', 'count'), 기본급=('기본급', 'sum'), 수당=('초과근무수당', 'sum'), 총합계=('합계', 'sum')
            ).reset_index()
            
            grouped['1인 평균합계'] = grouped['총합계'] / grouped['인원']
            grouped['수당_raw'] = grouped['수당'] # heatmap 계산용
            
            avg_ot = grouped['수당_raw'].mean()
            if str(avg_ot) == 'nan' or avg_ot == 0:
                avg_ot = float('inf')
            
            display_cols = ['직위', '인원', '기본급', '수당', '총합계', '1인 평균합계']
            
            # 포맷팅 적용
            for c in ['기본급', '수당', '총합계', '1인 평균합계']:
                grouped[c] = grouped[c].apply(lambda x: format_mxn(int(x)) if pd.notnull(x) else "0")
                
            # HTML 테이블 렌더링 (경영진 Heatmap 적용)
            th_html = "".join([f"<th>{col}</th>" for col in display_cols])
            tr_html = ""
            for _, row in grouped.iterrows():
                tds = ""
                for col in display_cols:
                    if col == '수당' and row['수당_raw'] > avg_ot and row['수당_raw'] > 1000:
                        # 경고 수준 초과 시 셀 배경 빨간색 하이라이트
                        bg_style = "background-color: #FFF1F0; color: #CF1322; font-weight: 700;"
                    else:
                        bg_style = ""
                    tds += f"<td style='{bg_style}'>{row[col]}</td>"
                tr_html += f"<tr>{tds}</tr>"
            
            table_html = f"""
            <div class="custom-table-wrapper">
                <table class="custom-table">
                    <thead><tr>{th_html}</tr></thead>
                    <tbody>{tr_html}</tbody>
                </table>
            </div>
            """
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding: 40px; text-align: center; color: #8C8C8C; font-size: 14px;'>선택하신 부서에 해당하는 급여 데이터가 존재하지 않습니다.</div>", unsafe_allow_html=True)

def main():
    data_dir = _find_data_dir()
    data = load_data_fresh(data_dir)
    monthly_df = data.get('monthly', pd.DataFrame())
    employee_df = data.get('employees', pd.DataFrame())
    
    col_menu, col_main = st.columns([2, 8])
    
    with col_menu:
        st.markdown("""
        <div style='margin-bottom: 32px; padding-left: 8px; display:flex; align-items:center; gap:8px;'>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D3557" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
            <h2 style='font-size:20px; font-weight:800; color:#1a1a1a; margin:0; letter-spacing: -0.5px;'>동진테크윈</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # 메인 대시보드(전사 전체) 연결용 a 태그
        st.markdown("""
        <a href='http://localhost:8502' target='_self' style='color:#4B5563; font-size:15px; font-weight:600; display:flex; align-items:center; gap:12px; padding: 10px 12px; text-decoration:none; border-radius:6px; transition: background 0.2s;'>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
            메인 대시보드
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='color:#1D3557; font-size:15px; font-weight:700; display:flex; align-items:center; gap:12px; padding: 10px 12px; background:#F3F4F6; border-radius:6px; margin-bottom:8px; margin-top:4px;'>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            사업부별 손익 분석
        </div>
        """, unsafe_allow_html=True)
        
        # 계층형(Accordion) 네비게이션 상태 초기화
        if 'selected_dept' not in st.session_state:
            st.session_state.selected_dept = '전체'
            
        def set_dept(dept_name):
            st.session_state.selected_dept = dept_name
            
        def nav_btn(label, target_dept):
            is_active = (st.session_state.selected_dept == target_dept)
            btn_type = "primary" if is_active else "secondary"
            st.button(f"{label}", key=f"nav_{target_dept}", on_click=set_dept, args=(target_dept,), type=btn_type, use_container_width=True)

        st.markdown('<div style="margin-bottom: 12px;">', unsafe_allow_html=True)
        
        # 최상단
        nav_btn("전체보기", "전체")
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        
        # 메인 그룹 1: 직접부서 (생산)
        with st.expander("직접부서 (생산)", expanded=True):
            nav_btn("사출", "사출")
            nav_btn("조립", "조립")
            
        # 메인 그룹 2: 간접부서 (지원/품질)
        with st.expander("간접부서 (지원/품질)", expanded=True):
            nav_btn("품질", "품질")
            nav_btn("사출유지보수", "사출유지보수")
            nav_btn("일반유지보수", "일반유지보수")
            nav_btn("자재/창고", "자재/창고")
            nav_btn("출하", "출하")
            
        # 메인 그룹 3: 간접부서 (경영지원)
        with st.expander("경영지원 (관리/인사)", expanded=True):
            nav_btn("인사", "인사")
            nav_btn("관리", "관리")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        selected_dept = st.session_state.selected_dept

        st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)

    with col_main:
        render_kpi_dashboard(selected_dept, monthly_df, employee_df)

if __name__ == "__main__":
    main()
