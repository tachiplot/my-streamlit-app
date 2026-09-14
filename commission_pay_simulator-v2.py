import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="歩合給制度 シミュレーター v2",
    page_icon="📊",
    layout="wide"
)

st.title("📊 3等級以上 選択型歩合給制度 シミュレーター")
st.markdown("基本給・各種手当設定や創出粗利額、歩合還元率をインタラクティブに変更して、**標準型月給目安**との比較、**社員受取差額**、**給与支給額**、**会社残存粗利**を検証できます。")

# ---------------------------------------------------------
# サイドバー：基本設定パラメータ
# ---------------------------------------------------------
st.sidebar.header("⚙️ 基本条件設定")

base_salary = st.sidebar.number_input("基本給 (円)", value=206200, step=1000, help="ジャンクス・便利屋共通基本給")
standard_pay = st.sidebar.number_input("標準型 月給目安 (円)", value=271200, step=1000, help="3等級リーダー・資格1つ保有時の標準型給与")

st.sidebar.markdown("---")
st.sidebar.header("📈 モデル1：累進歩合型 設定")

# 閾値を任意入力可能に
m1_t1 = st.sidebar.number_input("控除閾値 (第1区間開始) (円)", value=1000000, step=100000, help="歩合給が発生しない基準額（例: 1,000,000円）")
m1_t2 = st.sidebar.number_input("第1区間上限 / 第2区間開始 (円)", value=2000000, step=100000, help="第1還元率が適用される上限額（例: 2,000,000円）")
m1_t3 = st.sidebar.number_input("第2区間上限 / 第3区間開始 (円)", value=3000000, step=100000, help="第2還元率が適用される上限額（例: 3,000,000円）")

# 閾値に基づくラベル動的生成
label_tier1 = f"{m1_t1/10000:.0f}万〜{m1_t2/10000:.0f}万円部分 還元率 (%)"
label_tier2 = f"{m1_t2/10000:.0f}万〜{m1_t3/10000:.0f}万円部分 還元率 (%)"
label_tier3 = f"{m1_t3/10000:.0f}万円超過部分 還元率 (%)"

m1_rate1 = st.sidebar.slider(label_tier1, min_value=0.0, max_value=30.0, value=10.0, step=0.5) / 100.0
m1_rate2 = st.sidebar.slider(label_tier2, min_value=0.0, max_value=30.0, value=15.0, step=0.5) / 100.0
m1_rate3 = st.sidebar.slider(label_tier3, min_value=0.0, max_value=40.0, value=20.0, step=0.5) / 100.0

st.sidebar.markdown("---")
st.sidebar.header("🚀 モデル2：一律還元型 設定")
m2_threshold = st.sidebar.number_input("モデル2 控除閾値 (円)", value=0, step=100000, help="全額対象の場合は0円")
m2_rate = st.sidebar.slider("一律還元率 (%)", min_value=0.0, max_value=30.0, value=15.0, step=0.5) / 100.0

# ---------------------------------------------------------
# ロジック関数
# ---------------------------------------------------------
def calc_m1(profit):
    if profit <= m1_t1:
        comm = 0.0
    else:
        p1 = min(profit, m1_t2) - m1_t1 if profit > m1_t1 else 0.0
        p2 = min(profit, m1_t3) - m1_t2 if profit > m1_t2 else 0.0
        p3 = profit - m1_t3 if profit > m1_t3 else 0.0
        comm = p1 * m1_rate1 + p2 * m1_rate2 + p3 * m1_rate3
    total = base_salary + comm
    diff = total - standard_pay
    comp_rem = profit - total
    labor_share = (total / profit * 100.0) if profit > 0 else 0.0
    return comm, total, diff, comp_rem, labor_share

def calc_m2(profit):
    if profit <= m2_threshold:
        comm = 0.0
    else:
        comm = (profit - m2_threshold) * m2_rate
    total = base_salary + comm
    diff = total - standard_pay
    comp_rem = profit - total
    labor_share = (total / profit * 100.0) if profit > 0 else 0.0
    return comm, total, diff, comp_rem, labor_share

# ---------------------------------------------------------
# メイン画面：1. 任意粗利ピンポイント試算
# ---------------------------------------------------------
st.subheader("💡 任意粗利 ピンポイントシミュレーション")

col_input1, col_input2 = st.columns([2, 2])

with col_input1:
    selected_profit = st.number_input("検証したい月間創出粗利額を入力 (円)", value=1800000, step=100000)

with col_input2:
    selected_model_view = st.radio(
        "検証・表示モデルの選択",
        options=["両モデルを比較", "モデル1（累進歩合型）のみ", "モデル2（一律還元型）のみ"],
        horizontal=True
    )

m1_comm, m1_tot, m1_diff, m1_comp, m1_share = calc_m1(selected_profit)
m2_comm, m2_tot, m2_diff, m2_comp, m2_share = calc_m2(selected_profit)

# 標準型情報の表示枠
st.info(f"📌 **標準型 月給目安**: **{int(standard_pay):,} 円** （創出粗利: {int(selected_profit):,} 円 時の会社残存粗利: {int(selected_profit - standard_pay):,} 円）")

if selected_model_view == "両モデルを比較":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📈 モデル1：累進歩合型")
        st.metric("支給総額", f"{int(m1_tot):,} 円", delta=f"{int(m1_diff):,} 円 (vs標準型月給)")
        st.metric("社員の受取差額 (vs標準型)", f"{'+' if m1_diff >= 0 else ''}{int(m1_diff):,} 円")
        st.metric("歩合給額", f"{int(m1_comm):,} 円")
        st.metric("会社残存粗利", f"{int(m1_comp):,} 円")
        st.metric("人件費率 (労働分配率)", f"{m1_share:.1f} %")

    with col2:
        st.markdown("### 🚀 モデル2：一律還元型")
        st.metric("支給総額", f"{int(m2_tot):,} 円", delta=f"{int(m2_diff):,} 円 (vs標準型月給)")
        st.metric("社員の受取差額 (vs標準型)", f"{'+' if m2_diff >= 0 else ''}{int(m2_diff):,} 円")
        st.metric("歩合給額", f"{int(m2_comm):,} 円")
        st.metric("会社残存粗利", f"{int(m2_comp):,} 円")
        st.metric("人件費率 (労働分配率)", f"{m2_share:.1f} %")

elif selected_model_view == "モデル1（累進歩合型）のみ":
    st.markdown("### 📈 モデル1：累進歩合型 詳細")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("支給総額", f"{int(m1_tot):,} 円")
    c2.metric("社員の受取差額 (vs標準型)", f"{'+' if m1_diff >= 0 else ''}{int(m1_diff):,} 円")
    c3.metric("会社残存粗利", f"{int(m1_comp):,} 円")
    c4.metric("人件費率", f"{m1_share:.1f} %")

else:
    st.markdown("### 🚀 モデル2：一律還元型 詳細")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("支給総額", f"{int(m2_tot):,} 円")
    c2.metric("社員の受取差額 (vs標準型)", f"{'+' if m2_diff >= 0 else ''}{int(m2_diff):,} 円")
    c3.metric("会社残存粗利", f"{int(m2_comp):,} 円")
    c4.metric("人件費率", f"{m2_share:.1f} %")

st.markdown("---")

# ---------------------------------------------------------
# メイン画面：2. 標準6区分 比較テーブル
# ---------------------------------------------------------
st.subheader("📋 粗利区分別 比較一覧表")

profits = [400000, 800000, 1200000, 1800000, 2500000, 3500000]

table_data = []
for p in profits:
    c1, t1, d1, r1, s1 = calc_m1(p)
    c2, t2, d2, r2, s2 = calc_m2(p)
    
    row = {
        "創出粗利": f"{p//10000}万円",
        "標準型 月給目安": f"{int(standard_pay):,}円"
    }
    
    if selected_model_view in ["両モデルを比較", "モデル1（累進歩合型）のみ"]:
        row["モデル1 支給総額"] = f"{int(t1):,}円"
        row["モデル1 受取差額"] = f"{'+' if d1 >= 0 else ''}{int(d1):,}円"
        row["モデル1 会社残存"] = f"{int(r1):,}円"
        
    if selected_model_view in ["両モデルを比較", "モデル2（一律還元型）のみ"]:
        row["モデル2 支給総額"] = f"{int(t2):,}円"
        row["モデル2 受取差額"] = f"{'+' if d2 >= 0 else ''}{int(d2):,}円"
        row["モデル2 会社残存"] = f"{int(r2):,}円"
        
    table_data.append(row)

df_summary = pd.DataFrame(table_data)
st.dataframe(df_summary, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# メイン画面：3. グラフ分析
# ---------------------------------------------------------
st.subheader("📈 創出粗利の伸びと支給額・会社利益の推移")

grid_profits = [p * 10000 for p in range(20, 401, 10)]

m1_totals = [calc_m1(p)[1] for p in grid_profits]
m2_totals = [calc_m2(p)[1] for p in grid_profits]
std_totals = [standard_pay for p in grid_profits]

m1_comps = [calc_m1(p)[3] for p in grid_profits]
m2_comps = [calc_m2(p)[3] for p in grid_profits]
std_comps = [p - standard_pay for p in grid_profits]

fig = go.Figure()

fig.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=std_totals, mode='lines', name='標準型 月給目安', line=dict(color='gray', dash='dash')))

if selected_model_view in ["両モデルを比較", "モデル1（累進歩合型）のみ"]:
    fig.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=m1_totals, mode='lines+markers', name='モデル1 (累進歩合型) 支給額', line=dict(color='#2F5496', width=3)))

if selected_model_view in ["両モデルを比較", "モデル2（一律還元型）のみ"]:
    fig.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=m2_totals, mode='lines+markers', name='モデル2 (一律還元型) 支給額', line=dict(color='#E26B00', width=3)))

fig.update_layout(
    title="創出粗利 vs 月給支給額 (比較)",
    xaxis_title="月間創出粗利 (万円)",
    yaxis_title="支給総額 (円)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

fig2 = go.Figure()

fig2.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=std_comps, mode='lines', name='標準型 会社残存粗利', line=dict(color='gray', dash='dash')))

if selected_model_view in ["両モデルを比較", "モデル1（累進歩合型）のみ"]:
    fig2.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=m1_comps, mode='lines', name='モデル1 会社残存粗利', line=dict(color='#2F5496', width=2)))

if selected_model_view in ["両モデルを比較", "モデル2（一律還元型）のみ"]:
    fig2.add_trace(go.Scatter(x=[p/10000 for p in grid_profits], y=m2_comps, mode='lines', name='モデル2 会社残存粗利', line=dict(color='#E26B00', width=2)))

fig2.update_layout(
    title="創出粗利 vs 会社残存粗利 (比較)",
    xaxis_title="月間創出粗利 (万円)",
    yaxis_title="会社残存粗利 (円)",
    hovermode="x unified"
)

st.plotly_chart(fig2, use_container_width=True)
