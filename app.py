import streamlit as st
import pandas as pd

st.set_page_config(page_title="売上集計ツール", layout="wide")

st.title("チケット売上集計ツール（項目固定版）")

# --- 設定：表示順の定義 ---
# 1. 販売枠の並び順
FRAME_ORDER = [
    "一般販売枠",
    "インバウンド枠",
    "インナー枠",
    "電通福利厚生",
    "日本旅行用受付"
]

# 2. 券種の並び順
TICKET_ORDER = [
    "一般（１９歳以上）",
    "こども（１９歳未満）",
    "ＶＩＰ一般",
    "ＶＩＰこども",
    "一般車いす",
    "こども車いす",
    "ＶＩＰ一般車いす",
    "ＶＩＰこども車いす",
    "ペア（２枚セット）",
    "家族（大人２子供２）",
    "学生（１９歳以上）",
    "学生車いす"
]

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding="cp932")
    
    # --- データ加工 ---
    # 販売枠の判定ロジック（キーワードで分類）
    def classify_frame(name):
        name = str(name)
        if "インバウンド" in name: return "インバウンド枠"
        if "インナー" in name: return "インナー枠"
        if "電通" in name: return "電通福利厚生"
        if "日本旅行" in name: return "日本旅行用受付"
        return "一般販売枠"

    df['販売枠'] = df['受付名'].apply(classify_frame)
    df['料金'] = pd.to_numeric(df['料金'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['参加人数'] = df.apply(lambda x: x['購入確定数'] * 4 if "家族" in str(x['販売区分名']) else x['購入確定数'], axis=1)
    df['売上金額'] = df['料金'] * df['購入確定数']
    
    # 1. 実際に存在するデータを集計
    actual_summary = df.groupby(['販売枠', '販売区分名']).agg({
        '購入確定数': 'sum',
        '参加人数': 'sum',
        '売上金額': 'sum'
    }).reset_index()

    # 2. 固定順のマスターテーブルを作成（すべての組み合わせを作る）
    # これにより、売上0の項目も表に強制的に出せるようになります
    master_rows = []
    for f in FRAME_ORDER:
        for t in TICKET_ORDER:
            master_rows.append({'販売枠': f, '販売区分名': t})
    master_df = pd.DataFrame(master_rows)

    # 3. マスターと実データを結合
    final_summary = pd.merge(master_df, actual_summary, on=['販売枠', '販売区分名'], how='left').fillna(0)

    # --- 画面表示 ---
    # 全体合計
    total_confirmed = final_summary['購入確定数'].sum()
    total_participants = final_summary['参加人数'].sum()
    total_sales = final_summary['売上金額'].sum()

    st.subheader("📊 全体合計")
    col1, col2, col3 = st.columns(3)
    col1.metric("総購入確定数", f"{total_confirmed:,.0f} 件")
    col2.metric("総参加人数", f"{total_participants:,.0f} 人")
    col3.metric("総売上金額", f"{total_sales:,.0f} 円")

    # 販売枠ごとのクイックサマリー
    st.write("---")
    st.subheader("🏢 枠別売上")
    frame_sales = final_summary.groupby('販売枠', sort=False)['売上金額'].sum()
    cols = st.columns(len(FRAME_ORDER))
    for i, frame_name in enumerate(FRAME_ORDER):
        val = frame_sales.get(frame_name, 0)
        cols[i].metric(frame_name, f"{val:,.0f} 円")

    # 詳細表
    st.subheader("📋 詳細データ一覧（項目固定）")
    
    # 表示用のスタイル適用
    st.dataframe(final_summary.style.format({
        '購入確定数': '{:,.0f}',
        '参加人数': '{:,.0f}人',
        '売上金額': '{:,.0f}円'
    }), use_container_width=True, height=600)

    # ダウンロード
    csv = final_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button("集計結果(CSV)をダウンロード", csv, "fixed_report.csv", "text/csv")