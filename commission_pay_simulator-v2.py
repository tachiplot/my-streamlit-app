import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="歩合給制度 シミュレーター v4",
    page_icon="📊",
    layout="wide"
)

st.title("📊 3等級以上 選択型歩合給制度 シミュレーター v4")
st.markdown("基本給設定、標準型月給目安、評価指標（**実測粗利・みなし粗利・純利益**）、および歩合還元モデル（**一律還元・超過分利益還元**）を任意に調整してシミュレーションできます。")

# ---------------------------------------------------------
# サイドバー：1. 基本条件設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 1. 基本給・標準給与設定")

base_salary = st.sidebar.number_input(
    "基本給 (円)", 
    value=206200, 
    step=1000, 
    help="ジャンクス・便利屋共通基本給 (例: 206,200円)"
)

standard_pay = st.sidebar.number_input(
    "標準型 月給目安 (円)", 
    value=302200, 
    step=1000, 
    help="3等級リーダー・資格有・固定残業代等含む標準型月給 (基本給20.62万+リーダー手当2.0万+通信手当0.5万+資格手当1.0万+能力手当3.0万+固定残業3.1万 = 約30.22万円)"
)

# ---------------------------------------------------------
# サイドバー：2. 評価指標の設定
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🎯 2. 評価指標の設定")

metric_type = st.sidebar.radio(
    "歩合給の評価指標",
    options=["実測粗利", "みなし粗利 (売上×想定粗利率)", "純利益 (粗利−販管費・固定費)"],
    index=0,
    help="歩合給の計算基礎となる金額の算定方法を選択します"
)

# みなし粗利率の設定
if metric_type == "みなし粗利 (売上×想定粗利率)":
    estimated_margin_rate = st.sidebar.slider(
        "想定粗利率 (%)",
        min_value=10.0,
        max_value=90.0,
        value=40.0,
        step=1.0,
        help="売上高に乗じる想定粗利率を入力・変更できます"
    ) / 100.0
else:
    estimated_margin_rate = 0.40

# 純利益設定時の固定費・販管費
if metric_type == "純利益 (粗利−販管費・固定費)":
    monthly_fixed_cost = st.sidebar.number_input(
        "月間店舗・担当分担固定費/販管費 (円)",
        value=300000,
        step=50000,
        help="粗利から控除する固定費用・販管費の目安金額"
    )
else:
    monthly_fixed_cost = 0

# ---------------------------------------------------------
# サイドバー：3. 還元モデルの設定
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("📈 3. 還元モデルの設定")

# モデル A: 一律還元モデル
st.sidebar.subheader("🚀 一律還元モデル")
m_flat_threshold = st.sidebar.number_input("一律還元 控除閾値 (円)", value=0, step=100000, help="全額対象の場合は0円")
m_flat_rate = st.sidebar.slider("一律還元率 (%)", min_value=0.0, max_value=40.0, value=15.0, step=0.5) / 100.0

st.sidebar.markdown("---")
# モデル B: 超過分利益還元モデル (累進歩合)
st.sidebar.subheader("📈 超過分利益還元モデル (累進歩合)")
m_prog_t1 = st.sidebar.number_input("控除閾値 (第1区間開始) (円)", value=1000000, step=100000, help="歩合が発生しない基準額")
m_prog_t2 = st.sidebar.number_input("第1区間上限 / 第2区間開始 (円)", value=2000000, step=100000, help="第1還元率の適用上限額")
m_prog_t3 = st.sidebar.number_input("第2区間上限 / 第3区間開始 (円)", value=3000000, step=100000, help="第2還元率の適用上限額")

label_tier1 = f"{m_prog_t1/10000:.0f}万〜{m_prog_t2/10000:.0f}万円部分 還元率 (%)"
label_tier2 = f"{m_prog_t2/10000:.0f}万〜{m_prog_t3/10000:.0f}万円部分 還元率 (%)"
label_tier3 = f"{m_prog_t3/10000:.0f}万円超過部分 還元率 (%)"

m_prog_r1 = st.sidebar.slider(label_tier1, min_value=0.0, max_value=30.0, value=10.0, step=0.5) / 100.0
m_prog_r2 = st.sidebar.slider(label_tier2, min_value=0.0, max_value=30.0, value=15.0, step=0.5) / 100.0
m_prog_r3 = st.sidebar.slider(label_tier3, min_value=0.0, max_value=40.0, value=20.0, step=0.5) / 100.0


# ---------------------------------------------------------
# 計算ロジック関数
# ---------------------------------------------------------
def calc_target_metric(input_val):
    """入力値から指定された評価指標のベース金額を計算"""
    if metric_type == "実測粗利":
        target_val = input_val
        gross_profit = input_val
    elif metric_type == "みなし粗利 (売上×想定粗利率)":
        target_val = input_val * estimated_margin_rate
        gross_profit = target_val
    else:  # 純利益
        gross_profit = input_val
        target_val = max(0.0, input_val - monthly_fixed_cost)
    return target_val, gross_profit

def calc_flat_model(target_val, gross_profit):
    """一律還元モデルの計算"""
    if target_val <= m_flat_threshold:
        comm = 0.0
    else:
        comm = (target_val - m_flat_threshold) * m_flat_rate
    total = base_salary + comm
    diff = total - standard_pay
    comp_rem = gross_profit - total
    labor_share = (total / gross_profit * 100.0) if gross_profit > 0 else 0.0
    return comm, total, diff, comp_rem, labor_share

def calc_prog_model(target_val, gross_profit):
    """超過分利益還元モデル (累進歩合) の計算"""
    if target_val <= m_prog_t1:
        comm = 0.0
    else:
        p1 = min(target_val, m_prog_t2) - m_prog_t1 if target_val > m_prog_t1 else 0.0
        p2 = min(target_val, m_prog_t3) - m_prog_t2 if target_val > m_prog_t2 else 0.0
        p3 = target_val - m_prog_t3 if target_val > m_prog_t3 else 0.0
        comm = p1 * m_prog_r1 + p2 * m_prog_r2 + p3 * m_prog_r3
    total = base_salary + comm
    diff = total - standard_pay
    comp_rem = gross_profit - total
    labor_share = (total / gross_profit * 100.0) if gross_profit > 0 else 0.0
    return comm, total, diff, comp_rem, labor_share


# ---------------------------------------------------------
# メイン画面：1. ピンポイント試算
# ---------------------------------------------------------
st.subheader("💡 任意実績 ピンポイントシミュレーション")

col_in1, col_in2 = st.columns([2, 2])

with col_in1:
    if metric_type == "実測粗利":
        input_amount = st.number_input("検証する 月間実測粗利額 (円)", value=1800000, step=100000)
    elif metric_type == "みなし粗利 (売上×想定粗利率)":
        input_amount = st.number_input("検証する 月間売上高 (円)", value=4500000, step=100000)
    else:
        input_amount = st.number_input("検証する 月間粗利額 (円)", value=1800000, step=100000)

with col_in2:
    selected_model_view = st.radio(
        "表示モデルの選択",
        options=["両モデルを比較", "一律還元モデルのみ", "超過分利益還元モデルのみ"],
        horizontal=True
    )

# 評価対象額の算出
target_val, gross_profit = calc_target_metric(input_amount)

# 計算実行
flat_comm, flat_tot, flat_diff, flat_comp, flat_share = calc_flat_model(target_val, gross_profit)
prog_comm, prog_tot, prog_diff, prog_comp, prog_share = calc_prog_model(target_val, gross_profit)

# 指標サマリー案内表示
st.caption("※標準型月給目安（3等級リーダー・資格有）：基本給20.62万 ＋ リーダー手当2.0万 ＋ 通信0.5万 ＋ 資格1.0万 ＋ 能力手当3.0万 ＋ 固定残業3.1万 ＝ **約30.22万円**")

if metric_type == "実測粗利":
    st.info(f"📌 **評価対象 (実測粗利)**: **{int(target_val):,} 円** ｜ **標準型 月給目安**: **{int(standard_pay):,} 円** （標準型選択時の会社残存粗利: {int(gross_profit - standard_pay):,} 円）")
elif metric_type == "みなし粗利 (売上×想定粗利率)":
    st.info(f"📌 **月間売上高**: {int(input_amount):,} 円 ➔ **評価対象 (みなし粗利 {estimated_margin_rate*100:.0f}%)**: **{int(target_val):,} 円** ｜ **標準型 月給目安**: **{int(standard_pay):,} 円**")
else:
    st.info(f"📌 **月間粗利**: {int(gross_profit):,} 円 − 固定費 {int(monthly_fixed_cost):,} 円 ➔ **評価対象 (純利益)**: **{int(target_val):,} 円** ｜ **標準型 月給目安**: **{int(standard_pay):,} 円**")


# カード結果表示
if selected_model_view == "両モデルを比較":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🚀 一律還元モデル")
        st.metric("支給総額", f"{int(flat_tot):,} 円", delta=f"{int(flat_diff):,} 円 (vs標準型)")
        st.metric("社員の受取差額 (vs標準型)", f"{'+' if flat_diff >= 0 else ''}{int(flat_diff):,} 円")
        st.metric("歩合給額", f"{int(flat_comm):,} 円")
        st.metric("会社残存粗利", f"{int(flat_comp):,} 円")
        st.metric("人件費率 (対粗利)", f"{flat_share:.1f} %")

    with col2:
        st.markdown("### 📈 超過分利益還元モデル (累進歩合)")
        st.metric("支給総額", f"{int(prog_tot):,} 円", delta=f"{int(prog_diff):,} 円 (vs標準型)")
        st.metric("社員の受取差額 (vs標準型)", f"{'+' if prog_diff >= 0 else ''}{int(prog_diff):,} 円")
        st.metric("歩合給額", f"{int(prog_comm):,} 円")
        st.metric("会社残存粗利", f"{int(prog_comp):,} 円")
        st.metric("人件費率 (対粗利)", f"{prog_share:.1f} %")

elif selected_model_view == "一律還元モデルのみ":
    st.markdown("### 🚀 一律還元モデル 詳細")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("支給総額", f"{int(flat_tot):,} 円")
    c2.metric("社員の受取差額 (vs標準型)", f"{'+' if flat_diff >= 0 else ''}{int(flat_diff):,} 円")
    c3.metric("会社残存粗利", f"{int(flat_comp):,} 円")
    c4.metric("人件費率", f"{flat_share:.1f} %")

else:
    st.markdown("### 📈 超過分利益還元モデル (累進歩合) 詳細")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("支給総額", f"{int(prog_tot):,} 円")
    c2.metric("社員の受取差額 (vs標準型)", f"{'+' if prog_diff >= 0 else ''}{int(prog_diff):,} 円")
    c3.metric("会社残存粗利", f"{int(prog_comp):,} 円")
    c4.metric("人件費率", f"{prog_share:.1f} %")

st.markdown("---")

# ---------------------------------------------------------
# メイン画面：2. 標準6区分 比較テーブル
# ---------------------------------------------------------
st.subheader("📋 実績区分別 比較一覧表")

# 実測粗利または粗利基準での6区分
base_profits = [400000, 800000, 1200000, 1800000, 2500000, 3500000]

table_data = []
for bp in base_profits:
    if metric_type == "みなし粗利 (売上×想定粗利率)":
        # 粗利相当額から売上高を逆算
        sales_val = bp / estimated_margin_rate
        t_val, g_prof = calc_target_metric(sales_val)
        label_col = f"売上 {sales_val/10000:.0f}万 (みなし粗利 {bp/10000:.0f}万)"
    else:
        t_val, g_prof = calc_target_metric(bp)
        label_col = f"粗利 {bp/10000:.0f}万円"

    fc, ft, fd, fr, fs = calc_flat_model(t_val, g_prof)
    pc, pt, pd_val, pr, ps = calc_prog_model(t_val, g_prof)

    row = {
        "実績区分": label_col,
        "評価対象額": f"{int(t_val):,}円",
        "標準型 月給目安": f"{int(standard_pay):,}円"
    }

    if selected_model_view in ["両モデルを比較", "一律還元モデルのみ"]:
        row["一律 支給総額"] = f"{int(ft):,}円"
        row["一律 受取差額"] = f"{'+' if fd >= 0 else ''}{int(fd):,}円"
        row["一律 会社残存"] = f"{int(fr):,}円"

    if selected_model_view in ["両モデルを比較", "超過分利益還元モデルのみ"]:
        row["超過 支給総額"] = f"{int(pt):,}円"
        row["超過 受取差額"] = f"{'+' if pd_val >= 0 else ''}{int(pd_val):,}円"
        row["超過 会社残存"] = f"{int(pr):,}円"

    table_data.append(row)

df_summary = pd.DataFrame(table_data)
st.dataframe(df_summary, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# メイン画面：3. グラフ分析
# ---------------------------------------------------------
st.subheader("📈 実績の伸びと支給額・会社利益の推移")

grid_base_profits = [p * 10000 for p in range(20, 401, 10)]

grid_inputs = []
grid_targets = []
grid_gross = []

for bp in grid_base_profits:
    if metric_type == "みなし粗利 (売上×想定粗利率)":
        s_val = bp / estimated_margin_rate
        t_val, g_prof = calc_target_metric(s_val)
    else:
        t_val, g_prof = calc_target_metric(bp)
    grid_targets.append(t_val)
    grid_gross.append(g_prof)

flat_totals = [calc_flat_model(t, g)[1] for t, g in zip(grid_targets, grid_gross)]
prog_totals = [calc_prog_model(t, g)[1] for t, g in zip(grid_targets, grid_gross)]
std_totals = [standard_pay for _ in grid_base_profits]

flat_comps = [calc_flat_model(t, g)[3] for t, g in zip(grid_targets, grid_gross)]
prog_comps = [calc_prog_model(t, g)[3] for t, g in zip(grid_targets, grid_gross)]
std_comps = [g - standard_pay for g in grid_gross]

x_axis = [p / 10000 for p in grid_base_profits]
x_title = "月間粗利相当額 (万円)" if metric_type != "みなし粗利 (売上×想定粗利率)" else f"みなし粗利額 ({estimated_margin_rate*100:.0f}%換算) (万円)"

fig = go.Figure()
fig.add_trace(go.Scatter(x=x_axis, y=std_totals, mode='lines', name='標準型 月給目安', line=dict(color='gray', dash='dash')))

if selected_model_view in ["両モデルを比較", "一律還元モデルのみ"]:
    fig.add_trace(go.Scatter(x=x_axis, y=flat_totals, mode='lines+markers', name='一律還元モデル 支給額', line=dict(color='#E26B00', width=3)))

if selected_model_view in ["両モデルを比較", "超過分利益還元モデルのみ"]:
    fig.add_trace(go.Scatter(x=x_axis, y=prog_totals, mode='lines+markers', name='超過分利益還元モデル 支給額', line=dict(color='#2F5496', width=3)))

fig.update_layout(
    title="評価実績 vs 月給支給額",
    xaxis_title=x_title,
    yaxis_title="支給総額 (円)",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=x_axis, y=std_comps, mode='lines', name='標準型 会社残存粗利', line=dict(color='gray', dash='dash')))

if selected_model_view in ["両モデルを比較", "一律還元モデルのみ"]:
    fig2.add_trace(go.Scatter(x=x_axis, y=flat_comps, mode='lines', name='一律還元モデル 会社残存粗利', line=dict(color='#E26B00', width=2)))

if selected_model_view in ["両モデルを比較", "超過分利益還元モデルのみ"]:
    fig2.add_trace(go.Scatter(x=x_axis, y=prog_comps, mode='lines', name='超過分利益還元モデル 会社残存粗利', line=dict(color='#2F5496', width=2)))

fig2.update_layout(
    title="評価実績 vs 会社残存粗利",
    xaxis_title=x_title,
    yaxis_title="会社残存粗利 (円)",
    hovermode="x unified"
)
st.plotly_chart(fig2, use_container_width=True)
