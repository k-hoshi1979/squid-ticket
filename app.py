import streamlit as st
import pandas as pd

st.set_page_config(page_title="売上集計ツール", layout="wide")

# タイトルを変更（反映確認用）
st.title("チケット売上集計ツール（確定版・計算ロジック修正済み）")

# --- 設定：表示順の定義 ---
FRAME_ORDER = ["一般販売枠", "インバウンド枠", "インナー枠", "電通福利厚生", "日本旅行用受付"]
TICKET_ORDER = [
    "一般（１９歳以上）", "こども（１９歳未満）", "ＶＩＰ一般", "ＶＩＰこども",
    "一般車いす", "こども車いす", "ＶＩＰ一般車いす", "ＶＩＰこども車いす",
    "ペア（２枚セット）", "家族（大人２子供２）", "学生（１９歳以上）", "学生車いす"
]

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding="cp932")
    
    # --- データ加工 ---
    df['販売区分名'] = df['販売区分名'].str.strip()
    df['受付名'] = df['受付名'].str.strip()

    def classify_frame(name):
        name = str(name)
        if "インバウンド" in name: return "インバウンド枠"
        if "インナー" in name: return "インナー枠"
        if "電通" in name: return "電通福利厚生"
        if "日本旅行" in name: return "日本旅行用受付"
        return "一般販売枠"

    df['販売枠'] = df['受付名'].apply(classify_frame)
    df['料金'] = pd.to_numeric(df['料金'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # 数量・売上の計算ロジック
    def process_row(row):
        ticket_name = str(row['販売区分名'])
        price = row['料金']
        original_count = row['購入確定数']
        
        revenue = original_count * price
        
        # 家族券の判定：5000円超なら4倍にする
        if ("家族" in ticket_name) and (price > 5000):
            adjusted_count = original_count * 4
        else:
            adjusted_count = original_count
            
        return pd.Series([adjusted_count, revenue])

    df[['集計用カウント', '売上金額']] = df.apply(process_row, axis=1)
    
    # --- 集計処理 ---
    actual_summary = df.groupby(['販売枠', '販売区分名']).agg({
        '集計用カウント': 'sum',
        '売上金額': 'sum'
    }).reset_index()

    master_rows = []
    for f in FRAME_ORDER:
        for t in TICKET_ORDER:
            master_rows.append({'販売枠': f, '販売区分名': t})
    master_df = pd.DataFrame(master_rows)
    master_df['販売区分名'] = master_df['販売区分名'].str.strip()
    
    final_summary = pd.merge(master_df, actual_summary, on=['販売枠', '販売区分名'], how='left').fillna(0)

    # --- 画面表示 ---
    total_people = final_summary['集計用カウント'].sum()
    total_sales = final_summary['売上金額'].sum()

    st.subheader("📊 全体合計")
    col1, col2 = st.columns(2)
    col1.metric("総参加人数（枚数）", f"{total_people:,.0f} 名")
    col2.metric("総売上金額", f"{total_sales:,.0f} 円")

    st.write("---")
    st.subheader("📋 詳細データ一覧")
    display_df = final_summary.rename(columns={'集計用カウント': '枚数（人数）'})
    
    st.dataframe(display_df.style.format({
        '枚数（人数）': '{:,.0f}',
        '売上金額': '{:,.0f}円'
    }), use_container_width=True, height=600)

    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("集計結果(CSV)をダウンロード", csv, "report.csv", "text/csv")
