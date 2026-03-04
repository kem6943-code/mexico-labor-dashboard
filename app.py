# -*- coding: utf-8 -*-
"""
🇲🇽 멕시코 인건비 분석 대시보드
===================================
DONGJIN TECHWIN 멕시코 법인 인건비 & 인원 분석 프로그램

실행방법: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from io import BytesIO

from parsers import (
    parse_employee_catalog,
    load_all_payroll_files,
    merge_weekly_to_monthly,
    calculate_summary_stats,
    classify_payroll_columns,
    format_mxn,
    mxn_to_krw,
    format_krw,
    MXN_TO_KRW_RATE,
)

# ===================================================================
# 페이지 설정
# ===================================================================
st.set_page_config(
    page_title="🇲🇽 멕시코 인건비 대시보드",
    page_icon="🇲🇽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================================================================
# 커스텀 CSS 스타일
# ===================================================================
st.markdown("""
<style>
    /* 메인 타이틀 영역 */
    .main-header {
        background: linear-gradient(135deg, #006847 0%, #CE1126 50%, #FFFFFF 100%);
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: white;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        margin: 5px 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }

    /* KPI 카드 */
    .kpi-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #006847;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .kpi-label {
        font-size: 0.82rem;
        color: #666;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 2px;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #999;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
    }

    /* 구분선 */
    .section-divider {
        border-top: 2px solid #eee;
        margin: 15px 0;
    }

    /* 데이터프레임 스타일 */
    .dataframe-container {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ===================================================================
# 데이터 로드 (캐싱)
# ===================================================================
@st.cache_data
def load_data(data_dir: str):
    """모든 데이터를 로드하고 처리합니다."""
    results = {}
    
    # 1. 직원 카탈로그
    catalog_path = os.path.join(data_dir, 'Catalogo de Empleados.xlsx')
    if os.path.exists(catalog_path):
        results['employees'] = parse_employee_catalog(catalog_path)
    else:
        results['employees'] = pd.DataFrame()
    
    # 2. 급여대장 로드 및 월간 합산
    payroll_data = load_all_payroll_files(data_dir)
    results['payroll_raw'] = payroll_data
    results['monthly'] = merge_weekly_to_monthly(payroll_data)
    
    # 3. KPI 계산
    if not results['monthly'].empty:
        results['stats'] = calculate_summary_stats(results['monthly'], results['employees'])
        results['col_groups'] = classify_payroll_columns(results['monthly'])
    else:
        results['stats'] = {}
        results['col_groups'] = {}
    
    return results


# ===================================================================
# 데이터 폴더 자동 탐색 (로컬 + 클라우드 호환)
# ===================================================================
def _find_data_dir() -> str:
    """
    우선순위: data/ 폴더 → 부모 폴더 → 현재 폴더
    Streamlit Cloud에서는 data/ 폴더를 사용하고,
    로컬에서는 부모 폴더(멕시코 원본 데이터)를 사용합니다.
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1순위: app 폴더 내 data/ 하위폴더 (클라우드 배포용)
    data_sub = os.path.join(app_dir, 'data')
    if os.path.isdir(data_sub):
        return data_sub
    
    # 2순위: 부모 폴더 (로컬 실행 시 mexico_dashboard 상위 = 멕시코 폴더)
    parent = os.path.dirname(app_dir)
    if os.path.exists(os.path.join(parent, 'Catalogo de Empleados.xlsx')):
        return parent
    
    # 3순위: 현재 폴더
    return app_dir


# ===================================================================
# 사이드바
# ===================================================================
def render_sidebar():
    """사이드바 설정 영역."""
    with st.sidebar:
        st.markdown("### ⚙️ 설정")
        
        # 환율 설정
        exchange_rate = st.number_input(
            "💱 환율 (1 MXN → KRW)",
            value=MXN_TO_KRW_RATE,
            min_value=1.0,
            max_value=200.0,
            step=1.0,
            help="멕시코 페소 → 한국 원 환율"
        )
        
        # 통화 표시 설정
        show_krw = st.toggle("🇰🇷 원화 환산 표시", value=True)
        
        st.markdown("---")
        st.markdown("### 📌 참고사항")
        st.markdown("""
        - **주급(Semanal)**: 생산직 (주 1회)
        - **격주급(Quincenal)**: 사무직 (월 2회)  
        - **월급(Mensual)**: 임원급 (월 1회)
        - 모든 금액은 **MXN(멕시코 페소)** 기준
        """)
        
        # 데이터 경로 자동 탐색
        data_dir = _find_data_dir()
        
        return data_dir, exchange_rate, show_krw


# ===================================================================
# KPI 카드 렌더링
# ===================================================================
def render_kpi_card(label, value, sub_text="", icon="📊"):
    """하나의 KPI 카드를 HTML로 렌더링합니다."""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{icon} {label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


# ===================================================================
# 탭 1: 종합 대시보드
# ===================================================================
def render_overview_tab(data: dict, exchange_rate: float, show_krw: bool):
    """종합 대시보드 탭."""
    stats = data.get('stats', {})
    monthly_df = data.get('monthly', pd.DataFrame())
    
    if monthly_df.empty:
        st.warning("급여대장 데이터가 없습니다.")
        return
    
    # KPI 카드 (상단)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_kpi_card(
            "총 인원",
            f"{stats.get('total_headcount', 0):,}명",
            "급여 지급 인원 기준",
            "👥"
        )
    
    with col2:
        total_cost = stats.get('total_labor_cost', 0)
        sub = f"≈ {format_krw(total_cost * exchange_rate)}" if show_krw else ""
        render_kpi_card(
            "총 인건비",
            format_mxn(total_cost),
            sub,
            "💰"
        )
    
    with col3:
        earnings = stats.get('total_earnings', 0)
        sub = f"≈ {format_krw(earnings * exchange_rate)}" if show_krw else ""
        render_kpi_card(
            "총 지급액",
            format_mxn(earnings),
            sub,
            "💵"
        )
    
    with col4:
        obligations = stats.get('total_obligations', 0)
        sub = f"≈ {format_krw(obligations * exchange_rate)}" if show_krw else ""
        render_kpi_card(
            "총 회사부담금",
            format_mxn(obligations),
            sub,
            "🏢"
        )
    
    with col5:
        avg_cost = stats.get('avg_cost_per_person', 0)
        sub = f"≈ {format_krw(avg_cost * exchange_rate)}/인" if show_krw else ""
        render_kpi_card(
            "인당 평균 인건비",
            format_mxn(avg_cost),
            sub,
            "👤"
        )
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 차트 영역
    dept_summary = stats.get('dept_summary', pd.DataFrame())
    
    if not dept_summary.empty:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 📊 부서별 인원 분포")
            fig_pie = px.pie(
                dept_summary,
                names='부서',
                values='인원수',
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4,
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='label+value+percent',
                textfont_size=11,
            )
            fig_pie.update_layout(
                height=400,
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=-0.3,
                    xanchor="center", x=0.5,
                    font=dict(size=10)
                )
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_right:
            st.markdown("#### 💰 부서별 총 인건비 (MXN)")
            if '총인건비' in dept_summary.columns:
                fig_bar = px.bar(
                    dept_summary.sort_values('총인건비', ascending=True).tail(10),
                    x='총인건비',
                    y='부서',
                    orientation='h',
                    color='총인건비',
                    color_continuous_scale='Greens',
                    text='총인건비',
                )
                fig_bar.update_traces(
                    texttemplate='$%{text:,.0f}',
                    textposition='outside',
                    textfont_size=10,
                )
                fig_bar.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=80),
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis_title="총 인건비 (MXN)",
                    yaxis_title="",
                )
                st.plotly_chart(fig_bar, use_container_width=True)
    
    # 비용 구조 분해 차트
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("#### 📈 인건비 구조 분해")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        # 지급 vs 공제 vs 회사부담 구성
        cost_breakdown = {
            '총 지급액 (실수령 + 공제)': stats.get('total_earnings', 0),
            '총 회사부담금': stats.get('total_obligations', 0),
        }
        fig_donut = px.pie(
            names=list(cost_breakdown.keys()),
            values=list(cost_breakdown.values()),
            color_discrete_sequence=['#006847', '#CE1126'],
            hole=0.5,
            title="회사 총 부담 구성"
        )
        fig_donut.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
        fig_donut.update_layout(height=380, margin=dict(t=40, b=20), showlegend=False)
        st.plotly_chart(fig_donut, use_container_width=True)
    
    with col_b:
        # 직원 입장: 지급액 중 실수령 vs 공제
        employee_breakdown = {
            '실수령액': stats.get('total_net', 0),
            '총 공제': stats.get('total_deductions', 0),
        }
        fig_emp = px.pie(
            names=list(employee_breakdown.keys()),
            values=list(employee_breakdown.values()),
            color_discrete_sequence=['#2ecc71', '#e74c3c'],
            hole=0.5,
            title="직원 지급액 구성 (실수령 vs 공제)"
        )
        fig_emp.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
        fig_emp.update_layout(height=380, margin=dict(t=40, b=20), showlegend=False)
        st.plotly_chart(fig_emp, use_container_width=True)


# ===================================================================
# 탭 2: 인원 분석
# ===================================================================
def render_headcount_tab(data: dict):
    """인원 분석 탭."""
    emp_df = data.get('employees', pd.DataFrame())
    monthly_df = data.get('monthly', pd.DataFrame())
    
    if emp_df.empty:
        st.warning("직원 카탈로그 데이터가 없습니다.")
        return
    
    # 헤더 KPI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("총 활성 인원", f"{len(emp_df):,}명", "Catalogo 기준", "👥")
    with col2:
        if '노조가입(한)' in emp_df.columns:
            union_cnt = (emp_df['노조가입(한)'] == '조합원').sum()
            render_kpi_card("조합원", f"{union_cnt:,}명", f"비조합원 {len(emp_df)-union_cnt}명", "🤝")
    with col3:
        if '급여주기(한)' in emp_df.columns:
            weekly_cnt = (emp_df['급여주기(한)'] == '주급').sum()
            render_kpi_card("주급 직원", f"{weekly_cnt:,}명", "생산직 위주", "📅")
    with col4:
        if '급여주기(한)' in emp_df.columns:
            monthly_cnt = (emp_df['급여주기(한)'] == '월급').sum()
            render_kpi_card("월급 직원", f"{monthly_cnt:,}명", "임원/관리직", "📆")
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 차트 영역
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 🏢 부서별 인원 (급여주기별)")
        if '부서' in emp_df.columns and '급여주기(한)' in emp_df.columns:
            dept_period = emp_df.groupby(['부서', '급여주기(한)']).size().reset_index(name='인원')
            fig = px.bar(
                dept_period,
                x='부서',
                y='인원',
                color='급여주기(한)',
                barmode='stack',
                color_discrete_map={'주급': '#006847', '격주급': '#CE1126', '월급': '#FFD700'},
                text='인원',
            )
            fig.update_traces(textposition='inside', textfont_size=10)
            fig.update_layout(
                height=450,
                xaxis_tickangle=-45,
                margin=dict(t=20, b=80),
                legend_title="급여주기",
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("#### 👔 직위별 인원 분포 (TOP 15)")
        if '직위' in emp_df.columns:
            pos_cnt = emp_df['직위'].value_counts().head(15).reset_index()
            pos_cnt.columns = ['직위', '인원']
            fig_pos = px.bar(
                pos_cnt.sort_values('인원', ascending=True),
                x='인원',
                y='직위',
                orientation='h',
                color='인원',
                color_continuous_scale='RdYlGn',
                text='인원',
            )
            fig_pos.update_traces(textposition='outside', textfont_size=10)
            fig_pos.update_layout(
                height=450,
                margin=dict(t=20, b=20, l=20, r=40),
                coloraxis_showscale=False,
                xaxis_title="인원 수",
                yaxis_title="",
            )
            st.plotly_chart(fig_pos, use_container_width=True)
    
    # 추가 차트 행
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown("#### 🤝 노조 가입 현황")
        if '노조가입(한)' in emp_df.columns:
            union_dist = emp_df['노조가입(한)'].value_counts().reset_index()
            union_dist.columns = ['구분', '인원']
            fig_u = px.pie(
                union_dist, names='구분', values='인원',
                color_discrete_sequence=['#006847', '#CE1126', '#999'],
                hole=0.4,
            )
            fig_u.update_traces(textinfo='label+value+percent')
            fig_u.update_layout(height=300, margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig_u, use_container_width=True)
    
    with col_b:
        st.markdown("#### ⏰ 근무 교대 분포")
        if '근무교대(한)' in emp_df.columns:
            shift_dist = emp_df['근무교대(한)'].value_counts().reset_index()
            shift_dist.columns = ['교대', '인원']
            fig_s = px.pie(
                shift_dist, names='교대', values='인원',
                color_discrete_sequence=['#3498db', '#2c3e50', '#e67e22', '#1abc9c'],
                hole=0.4,
            )
            fig_s.update_traces(textinfo='label+value+percent')
            fig_s.update_layout(height=300, margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig_s, use_container_width=True)
    
    with col_c:
        st.markdown("#### 📅 급여주기 분포")
        if '급여주기(한)' in emp_df.columns:
            period_dist = emp_df['급여주기(한)'].value_counts().reset_index()
            period_dist.columns = ['주기', '인원']
            fig_p = px.pie(
                period_dist, names='주기', values='인원',
                color_discrete_map={'주급': '#006847', '격주급': '#CE1126', '월급': '#FFD700'},
                hole=0.4,
            )
            fig_p.update_traces(textinfo='label+value+percent')
            fig_p.update_layout(height=300, margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)
    
    # 부서별 상세 테이블
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("#### 📋 부서별 인원 상세")
    if '부서' in emp_df.columns:
        display_cols = ['부서']
        if '급여주기(한)' in emp_df.columns:
            # 피벗 테이블 생성
            pivot = emp_df.groupby(['부서', '급여주기(한)']).size().unstack(fill_value=0)
            pivot['합계'] = pivot.sum(axis=1)
            pivot = pivot.sort_values('합계', ascending=False)
            st.dataframe(pivot, use_container_width=True)


# ===================================================================
# 탭 3: 인건비 분석
# ===================================================================
def render_cost_tab(data: dict, exchange_rate: float, show_krw: bool):
    """인건비 분석 탭."""
    monthly_df = data.get('monthly', pd.DataFrame())
    stats = data.get('stats', {})
    col_groups = data.get('col_groups', {})
    
    if monthly_df.empty:
        st.warning("급여대장 데이터가 없습니다.")
        return
    
    # 급여 항목별 비중 분석
    st.markdown("#### 📊 급여 지급항목 비중 분석")
    
    earning_cols = col_groups.get('earnings', [])
    if earning_cols:
        # 각 지급 항목의 총합 계산
        earning_totals = {}
        for col in earning_cols:
            total = monthly_df[col].sum()
            if total > 0:
                earning_totals[col] = total
        
        if earning_totals:
            col_l, col_r = st.columns([3, 2])
            
            with col_l:
                # 가로 막대 차트
                earning_df = pd.DataFrame({
                    '항목': list(earning_totals.keys()),
                    '금액': list(earning_totals.values()),
                }).sort_values('금액', ascending=True)
                
                fig_earn = px.bar(
                    earning_df,
                    x='금액',
                    y='항목',
                    orientation='h',
                    color='금액',
                    color_continuous_scale='Greens',
                    text='금액',
                )
                fig_earn.update_traces(
                    texttemplate='$%{text:,.0f}',
                    textposition='outside',
                    textfont_size=10,
                )
                fig_earn.update_layout(
                    height=max(300, len(earning_totals) * 35),
                    margin=dict(t=10, b=10, r=80),
                    coloraxis_showscale=False,
                    xaxis_title="총액 (MXN)",
                    yaxis_title="",
                )
                st.plotly_chart(fig_earn, use_container_width=True)
            
            with col_r:
                # 파이차트 (상위 5개 + 기타)
                sorted_items = sorted(earning_totals.items(), key=lambda x: -x[1])
                top5 = dict(sorted_items[:5])
                others = sum(v for _, v in sorted_items[5:])
                if others > 0:
                    top5['기타'] = others
                
                fig_pie = px.pie(
                    names=list(top5.keys()),
                    values=list(top5.values()),
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.4,
                    title="지급항목 비중"
                )
                fig_pie.update_traces(textinfo='label+percent')
                fig_pie.update_layout(height=400, margin=dict(t=40, b=10), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 부서별 인건비 상세
    st.markdown("#### 🏢 부서별 인건비 분석")
    dept_summary = stats.get('dept_summary', pd.DataFrame())
    if not dept_summary.empty:
        # 표시용 DataFrame
        display_df = dept_summary.copy()
        
        # 금액 컬럼 포맷팅
        money_cols = ['총지급액', '총공제액', '실수령액', '총회사부담금', '총인건비', '인당평균']
        for col in money_cols:
            if col in display_df.columns:
                if show_krw:
                    display_df[f'{col}(KRW)'] = display_df[col].apply(lambda x: format_krw(x * exchange_rate))
                display_df[col] = display_df[col].apply(format_mxn)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # TOP 10 고비용 직원
    st.markdown("#### 🏆 TOP 10 인건비 직원")
    if '총지급액' in monthly_df.columns:
        top10_cols = ['사원번호', '직원명', '부서']
        available_cols = [c for c in top10_cols if c in monthly_df.columns]
        money_display = ['총지급액']
        if '총회사부담금' in monthly_df.columns:
            money_display.append('총회사부담금')
        if '실수령액' in monthly_df.columns:
            money_display.append('실수령액')
        
        top10 = monthly_df.nlargest(10, '총지급액')[available_cols + money_display].copy()
        top10.index = range(1, len(top10) + 1)
        top10.index.name = '순위'
        
        for col in money_display:
            if show_krw:
                top10[f'{col}(KRW)'] = top10[col].apply(lambda x: format_krw(x * exchange_rate))
            top10[col] = top10[col].apply(format_mxn)
        
        st.dataframe(top10, use_container_width=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 부서별 인건비 비교 차트 (Treemap)
    st.markdown("#### 🗺️ 부서별 인건비 구성 (Treemap)")
    if '부서' in monthly_df.columns and '총지급액' in monthly_df.columns:
        treemap_data = monthly_df.groupby('부서').agg({
            '총지급액': 'sum',
            '사원번호': 'count'
        }).reset_index()
        treemap_data = treemap_data.rename(columns={'사원번호': '인원'})
        treemap_data['라벨'] = treemap_data.apply(
            lambda r: f"{r['부서']}\n{r['인원']}명\n${r['총지급액']:,.0f}", axis=1
        )
        
        fig_tree = px.treemap(
            treemap_data,
            path=['부서'],
            values='총지급액',
            color='총지급액',
            color_continuous_scale='RdYlGn_r',
            custom_data=['인원', '총지급액'],
        )
        fig_tree.update_traces(
            texttemplate='%{label}<br>%{customdata[0]}명<br>$%{customdata[1]:,.0f}',
            textfont_size=12,
        )
        fig_tree.update_layout(height=500, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_tree, use_container_width=True)


# ===================================================================
# 탭 4: 회사 부담금 분석
# ===================================================================
def render_obligations_tab(data: dict, exchange_rate: float, show_krw: bool):
    """회사 부담금 분석 탭."""
    monthly_df = data.get('monthly', pd.DataFrame())
    col_groups = data.get('col_groups', {})
    stats = data.get('stats', {})
    
    if monthly_df.empty:
        st.warning("급여대장 데이터가 없습니다.")
        return
    
    # 설명 박스
    st.info("""
    🇲🇽 **멕시코 회사 부담금(Obligaciones Patronales)이란?**  
    한국의 4대보험(국민연금, 건보, 고용, 산재)에 해당하지만 **항목이 훨씬 많습니다.**  
    IMSS(사회보험), Infonavit(주택기금 5%), SAR(퇴직기금 2%), 지방세(3%), 산재보험, 보육비(1%) 등이 포함됩니다.  
    이 금액은 직원 급여 외에 **회사가 추가로 부담**하는 비용입니다.
    """)
    
    # KPI
    total_obligations = stats.get('total_obligations', 0)
    total_earnings = stats.get('total_earnings', 0)
    headcount = stats.get('total_headcount', 0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sub = f"≈ {format_krw(total_obligations * exchange_rate)}" if show_krw else ""
        render_kpi_card("총 회사부담금", format_mxn(total_obligations), sub, "🏢")
    with col2:
        ratio = (total_obligations / total_earnings * 100) if total_earnings > 0 else 0
        render_kpi_card("지급액 대비 비율", f"{ratio:.1f}%", "지급액 대비 추가 부담", "📊")
    with col3:
        per_person = total_obligations / headcount if headcount > 0 else 0
        sub = f"≈ {format_krw(per_person * exchange_rate)}" if show_krw else ""
        render_kpi_card("인당 회사부담금", format_mxn(per_person), sub, "👤")
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 항목별 분해
    obligation_cols = col_groups.get('obligations', [])
    if obligation_cols:
        st.markdown("#### 📊 회사 부담금 항목별 분해")
        
        ob_totals = {}
        for col in obligation_cols:
            total = monthly_df[col].sum()
            if total > 0:
                ob_totals[col] = total
        
        if ob_totals:
            col_l, col_r = st.columns(2)
            
            with col_l:
                ob_df = pd.DataFrame({
                    '항목': list(ob_totals.keys()),
                    '금액(MXN)': list(ob_totals.values()),
                }).sort_values('금액(MXN)', ascending=True)
                
                fig = px.bar(
                    ob_df, x='금액(MXN)', y='항목',
                    orientation='h',
                    color='금액(MXN)',
                    color_continuous_scale='Reds',
                    text='금액(MXN)',
                )
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig.update_layout(
                    height=max(300, len(ob_totals) * 40),
                    margin=dict(t=10, b=10, r=80),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_r:
                fig_pie = px.pie(
                    names=list(ob_totals.keys()),
                    values=list(ob_totals.values()),
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    hole=0.4,
                    title="부담금 비중"
                )
                fig_pie.update_traces(textinfo='label+percent')
                fig_pie.update_layout(height=400, margin=dict(t=40, b=10), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 부서별 회사부담금
    st.markdown("#### 🏢 부서별 회사부담금 비교")
    if '부서' in monthly_df.columns and '총회사부담금' in monthly_df.columns:
        dept_ob = monthly_df.groupby('부서').agg({
            '총회사부담금': 'sum',
            '사원번호': 'count',
        }).reset_index()
        dept_ob['인당부담금'] = dept_ob['총회사부담금'] / dept_ob['사원번호']
        dept_ob = dept_ob.rename(columns={'사원번호': '인원'})
        dept_ob = dept_ob.sort_values('총회사부담금', ascending=False)
        
        fig_dept = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_dept.add_trace(
            go.Bar(
                x=dept_ob['부서'], y=dept_ob['총회사부담금'],
                name='총 회사부담금', marker_color='#CE1126',
                text=dept_ob['총회사부담금'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside', textfont_size=9,
            ),
            secondary_y=False,
        )
        fig_dept.add_trace(
            go.Scatter(
                x=dept_ob['부서'], y=dept_ob['인당부담금'],
                name='인당 부담금', mode='lines+markers',
                marker=dict(size=8, color='#006847'),
                line=dict(width=2, color='#006847'),
            ),
            secondary_y=True,
        )
        
        fig_dept.update_layout(
            height=450,
            margin=dict(t=20, b=80),
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_dept.update_yaxes(title_text="총 회사부담금 (MXN)", secondary_y=False)
        fig_dept.update_yaxes(title_text="인당 부담금 (MXN)", secondary_y=True)
        
        st.plotly_chart(fig_dept, use_container_width=True)


# ===================================================================
# 탭 5: 상세 데이터
# ===================================================================
def render_detail_tab(data: dict, exchange_rate: float, show_krw: bool):
    """상세 급여 데이터 탭."""
    monthly_df = data.get('monthly', pd.DataFrame())
    emp_df = data.get('employees', pd.DataFrame())
    
    if monthly_df.empty:
        st.warning("데이터가 없습니다.")
        return
    
    st.markdown("#### 🔍 급여 데이터 상세 조회")
    
    # 필터 영역
    filter_cols = st.columns(3)
    
    with filter_cols[0]:
        dept_list = ['전체'] + sorted(monthly_df['부서'].unique().tolist()) if '부서' in monthly_df.columns else ['전체']
        selected_dept = st.selectbox("🏢 부서 필터", dept_list)
    
    with filter_cols[1]:
        search_name = st.text_input("🔎 직원명 검색", "")
    
    with filter_cols[2]:
        sort_col = st.selectbox(
            "📊 정렬 기준",
            ['총지급액', '실수령액', '총회사부담금', '사원번호'],
            index=0
        )
    
    # 필터 적용
    filtered = monthly_df.copy()
    if selected_dept != '전체' and '부서' in filtered.columns:
        filtered = filtered[filtered['부서'] == selected_dept]
    if search_name and '직원명' in filtered.columns:
        filtered = filtered[filtered['직원명'].str.contains(search_name, case=False, na=False)]
    
    # 정렬
    if sort_col in filtered.columns:
        filtered = filtered.sort_values(sort_col, ascending=False)
    
    # 표시할 핵심 컬럼 선택
    display_priority = [
        '사원번호', '직원명', '부서', '급여유형',
        '기본급', '주휴수당', '초과근무수당', '총지급액',
        '소득세(ISR)', '사회보험(IMSS)', '총공제액',
        '실수령액', '총회사부담금',
    ]
    display_cols = [c for c in display_priority if c in filtered.columns]
    
    # 추가 컬럼 토글
    show_all = st.toggle("📋 전체 컬럼 표시", value=False)
    if show_all:
        display_cols = filtered.columns.tolist()
    
    st.markdown(f"**{len(filtered):,}건** 조회됨")
    
    # 데이터 표시
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        height=500,
    )
    
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # Excel 다운로드
    st.markdown("#### 📥 데이터 다운로드")
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered[display_cols].to_excel(writer, sheet_name='급여상세', index=False)
        
        st.download_button(
            label="📥 현재 조회 데이터 (Excel)",
            data=buffer.getvalue(),
            file_name="멕시코_급여상세.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    with col_dl2:
        if not emp_df.empty:
            buffer2 = BytesIO()
            emp_display = emp_df.copy()
            display_emp_cols = [c for c in ['사원번호', '직원명', '부서', '직위', '급여주기(한)', '일급', 
                                             '노조가입(한)', '근무교대(한)', '입사일'] if c in emp_display.columns]
            with pd.ExcelWriter(buffer2, engine='openpyxl') as writer:
                emp_display[display_emp_cols].to_excel(writer, sheet_name='직원명부', index=False)
            
            st.download_button(
                label="📥 직원 명부 (Excel)",
                data=buffer2.getvalue(),
                file_name="멕시코_직원명부.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ===================================================================
# 메인 앱
# ===================================================================
def main():
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>🇲🇽 멕시코 인건비 분석 대시보드</h1>
        <p>DONGJIN TECHWIN México | 2026년 1월 급여 분석</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    data_dir, exchange_rate, show_krw = render_sidebar()
    
    # 데이터 존재 확인
    if not os.path.isdir(data_dir):
        st.error(f"❌ 데이터 폴더를 찾을 수 없습니다: {data_dir}")
        return
    
    # 데이터 로드
    with st.spinner("📊 데이터 로딩 중..."):
        data = load_data(data_dir)
    
    if data['monthly'].empty and data['employees'].empty:
        st.error("❌ 로드된 데이터가 없습니다. 데이터 폴더 경로를 확인해주세요.")
        return
    
    # 데이터 요약 (사이드바)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 데이터 현황")
        st.markdown(f"- 👥 직원 카탈로그: **{len(data['employees']):,}명**")
        st.markdown(f"- 💰 급여 데이터: **{len(data['monthly']):,}건**")
        
        payroll_raw = data.get('payroll_raw', {})
        for ptype, entries in payroll_raw.items():
            st.markdown(f"  - {ptype}: {len(entries)}개 파일")
    
    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 종합 대시보드",
        "👥 인원 분석",
        "💰 인건비 분석",
        "🏢 회사 부담금",
        "📋 상세 데이터",
    ])
    
    with tab1:
        render_overview_tab(data, exchange_rate, show_krw)
    with tab2:
        render_headcount_tab(data)
    with tab3:
        render_cost_tab(data, exchange_rate, show_krw)
    with tab4:
        render_obligations_tab(data, exchange_rate, show_krw)
    with tab5:
        render_detail_tab(data, exchange_rate, show_krw)


if __name__ == "__main__":
    main()
