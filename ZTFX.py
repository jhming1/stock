import streamlit as st
import pywencai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
#涨停版分析
#需在Node中用‘E:\AKShare_test\.venv\Scripts\streamlit.exe run E:\AKShare_test\ZTFX.py’来运行

# Setting up pandas display options
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', 100)

def get_limit_up_data(date):
    param = f"非ST,{date.strftime('%Y%m%d')}涨停"
    df = pywencai.get(query=param, sort_key='成交金额', sort_order='desc', loop=True)
    return df

def get_yesterday_zhangting_data(previous_date , date):
    param = f"非ST,{previous_date.strftime('%Y%m%d')}涨停"
    df = pywencai.get(query=param, sort_key='成交金额', sort_order='desc', loop=True)
    return df


def get_poban(date):
    param = f"非ST,{date.strftime('%Y%m%d')}曾涨停"
    df = pywencai.get(query=param, sort_key='成交金额', sort_order='desc', loop=True)
    return df





def get_limit_down_data(date):
    param = f"非ST,{date.strftime('%Y%m%d')}跌停"
    df = pywencai.get(query=param, sort_key='成交金额', sort_order='desc', loop=True)
    return df


def analyze_continuous_limit_up(df, date):
    # 提取连续涨停天数列和涨停原因类别列
    continuous_days_col = f'连续涨停天数[{date.strftime("%Y%m%d")}]'
    reason_col = f'涨停原因类别[{date.strftime("%Y%m%d")}]'

    # 确保涨停原因类别列存在
    if reason_col not in df.columns:
        df[reason_col] = '未知'

    # 按连续涨停天数降序排序，然后按涨停原因类别排序
    df_sorted = df.sort_values([continuous_days_col, reason_col], ascending=[False, True])

    # 创建结果DataFrame
    result = pd.DataFrame(columns=['连续涨停天数', '股票代码', '股票简称', '涨停原因类别'])

    # 遍历排序后的DataFrame，为每只股票创建一行
    for _, row in df_sorted.iterrows():
        new_row = pd.DataFrame({
            '连续涨停天数': [row[continuous_days_col]],
            '股票代码': [row['股票代码']],
            '股票简称': [row['股票简称']],
            '涨停原因类别': [row[reason_col]]
        })
        result = pd.concat([result, new_row], ignore_index=True)

    return result


def get_concept_counts(df, date):
    concepts = df[f'涨停原因类别[{date.strftime("%Y%m%d")}]'].str.split('+').explode().reset_index(drop=True)
    #concepts = df[f'涨停原因类别[{date.strftime("%Y%m%d")}]'].str.split('+', n=1).str[0].reset_index(drop=True)
    concept_counts = concepts.value_counts().reset_index()
    concept_counts.columns = ['概念', '出现次数']
    return concept_counts


def calculate_promotion_rates(current_df, previous_df, current_date, previous_date):
    """计算晋级数据"""
    promotion_data = []

    if previous_df.empty or current_df.empty:
        return pd.DataFrame()

    # 动态列名
    current_days_col = f'连续涨停天数[{current_date.strftime("%Y%m%d")}]'
    previous_days_col = f'连续涨停天数[{previous_date.strftime("%Y%m%d")}]'
    current_reason_col = f'涨停原因类别[{current_date.strftime("%Y%m%d")}]'
    previous_reason_col = f'涨停原因类别[{previous_date.strftime("%Y%m%d")}]'

    max_days = max(
        current_df[current_days_col].max() if not current_df.empty else 0,
        previous_df[previous_days_col].max() if not previous_df.empty else 0
    )

    for days in range(1, int(max_days) + 1):
        # 获取前日数据（使用前日列名）
        prev_stocks = previous_df[
            (previous_df[previous_days_col] == days)
        ][['股票代码', '股票简称', previous_days_col, previous_reason_col]].copy()
        prev_stocks.rename(columns={previous_reason_col: '涨停原因'}, inplace=True)

        # 获取当日晋级成功数据（使用当日列名）
        success_stocks = current_df[
            (current_df[current_days_col] == days + 1)
        ][['股票代码', '股票简称', current_days_col, current_reason_col]].copy()
        success_stocks.rename(columns={current_reason_col: '涨停原因'}, inplace=True)

        # 获取失败案例
        failed_stocks = prev_stocks[~prev_stocks['股票代码'].isin(current_df['股票代码'])]

        total = len(prev_stocks)
        success = len(success_stocks)
        rate = f"{success}/{total}={success / total:.0%}"if total > 0 else"N/A"

        promotion_data.append({
            '连板层级': f"{days}进{days + 1}",
            '晋级率': rate,
            '成功案例': success_stocks,
            '失败案例': failed_stocks,
            '总案例数': total
        })

    return pd.DataFrame(promotion_data)



def app():
    st.title("A股涨停概念分析")
    st.markdown("""
        <style>
        .stock-card {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            background: #f8f9fa;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .success {
            border-left: 4px solid #28a745;
            background: #e8f5e9;
        }
        .fail {
            border-left: 4px solid #dc3545;
            background: #ffebee;
        }
        .progress {
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background: #4CAF50;
            transition: width 0.3s ease;
        }
        </style>
        """, unsafe_allow_html=True)

    # Date selection
    max_date = datetime.now().date()
    selected_date = st.date_input("选择分析日期", max_value=max_date, value=max_date)

    trade_date_range = ak.tool_trade_date_hist_sina()
    trade_date_range['trade_date'] = pd.to_datetime(trade_date_range['trade_date']).dt.date

    if selected_date not in trade_date_range['trade_date'].values:
        st.write("所选日期不是A股交易日，请选择其他日期。")
        return
    target_date = selected_date
    previous_dates =  trade_date_range[trade_date_range['trade_date'] < target_date]

    if previous_dates.empty:
        raise ValueError("No previous trading day found before the given date")

    # 获取最近的交易日
    previous_date = previous_dates['trade_date'].max()

    st.write(f"分析日期: {selected_date} 和 {previous_date} (前一交易日)")

    # 获取关键数据
    selected_df = get_limit_up_data(selected_date)  # 今日涨停
    previous_df = get_limit_up_data(previous_date)  # 昨日涨停
    poban_df = get_poban(selected_date)  # 今日曾涨停
    yesterdayZhangting = get_yesterday_zhangting_data(previous_date, selected_date)  # 昨日涨停股票

    # 计算关键指标 ----------------------------------------------------------
    # 昨日涨停股票列表
    yesterday_zt_stocks = yesterdayZhangting['股票代码'].tolist() if not yesterdayZhangting.empty else []

    # 今日涨停股票列表
    today_zt_stocks = selected_df['股票代码'].tolist() if not selected_df.empty else []

    # 连板率计算（昨日涨停今日继续涨停）
    lianban_molecule = len(set(yesterday_zt_stocks) & set(today_zt_stocks))
    lianban_denominator = len(yesterday_zt_stocks)
    lianban_rate = (lianban_molecule / lianban_denominator * 100) if lianban_denominator > 0 else 0

    # 破板率计算（曾涨停但未封板）
    poban_stocks = poban_df['股票代码'].tolist() if not poban_df.empty else []
    poban_molecule = len(poban_stocks)
    poban_denominator = len(poban_stocks) + len(today_zt_stocks)
    poban_rate = (poban_molecule / poban_denominator * 100) if poban_denominator > 0 else 0

    # 昨日涨停今日涨幅（获取实际涨幅数据）


    yesterday_today_pct = get_yesterday_zhangting_data(previous_date,selected_date)

    # 计算上涨比例

    yesterday_today_pct['最新涨跌幅'] = pd.to_numeric(yesterday_today_pct['最新涨跌幅'], errors='coerce')

    # Calculate up_count, ignoring NaN values
    up_count = np.sum(yesterday_today_pct['最新涨跌幅'] > 0)

    # Calculate total_count, excluding NaN values
    total_count = yesterday_today_pct['最新涨跌幅'].count()

    # Calculate up_rate
    up_rate = (up_count / total_count * 100) if total_count > 0 else 0

    # 展示关键指标 ----------------------------------------------------------
    st.subheader("情绪指标")
    col1, col2, col3 = st.columns(3)

    # 昨日涨停今日上涨率
    col1.metric(
        "昨日涨停今日上涨率",
        f"{up_count}/{total_count}={up_rate:.1f}%",
        help="昨日涨停的股票中今日上涨的比例"
    )

    # 连板率
    col2.metric(
        "连板晋级率",
        f"{lianban_molecule}/{lianban_denominator}={lianban_rate:.1f}%",
        help="昨日涨停股票今日继续涨停的比例"
    )

    # 破板率
    col3.metric(
        "涨停破板率",
        f"{poban_molecule}/{poban_denominator}={poban_rate:.1f}%",
        help="今日曾触及涨停但收盘未封板的比例"
    )

    # Fetch data for both days
    selected_df = get_limit_up_data(selected_date)
    previous_df = get_limit_up_data(previous_date)

    selected_limit_down_df = get_limit_down_data(selected_date)
    previous_limit_down_df = get_limit_down_data(previous_date)

    # Analyze continuous limit-up for both days
    selected_continuous = analyze_continuous_limit_up(selected_df, selected_date)
    previous_continuous = analyze_continuous_limit_up(previous_df, previous_date)

    # Get concept counts for both days
    selected_concepts = get_concept_counts(selected_df, selected_date)
    previous_concepts = get_concept_counts(previous_df, previous_date)

    # Merge concept counts
    merged_concepts = pd.merge(selected_concepts, previous_concepts, on='概念', how='outer',
                               suffixes=('_selected', '_previous'))
    merged_concepts = merged_concepts.fillna(0)

    # Calculate change
    merged_concepts['变化'] = merged_concepts['出现次数_selected'] - merged_concepts['出现次数_previous']

    # Sort by '出现次数_selected' in descending order
    sorted_concepts = merged_concepts.sort_values('出现次数_selected', ascending=False)

    # Display total limit-up and limit-down stocks for both days
    st.subheader("涨停和跌停股票数量变化")

    # 计算涨停和跌停数量
    selected_total = len(selected_continuous) if selected_continuous is not None else 0
    previous_total = len(previous_continuous) if previous_continuous is not None else 0
    change = selected_total - previous_total

    def get_safe_limit_down_total(limit_down_df):
        """安全地获取跌停股票数量，如果数据为 None 则返回 0"""
        return len(limit_down_df) if limit_down_df is not None else 0

    selected_limit_down_total = len(selected_limit_down_df) if selected_limit_down_df is not None else 0
    previous_limit_down_total = len(previous_limit_down_df) if previous_limit_down_df is not None else 0
    limit_down_change = selected_limit_down_total - previous_limit_down_total

    # 计算涨停环比百分比变化
    if previous_total != 0:
        percentage_change_limit_up = (change / previous_total) * 100
    else:
        percentage_change_limit_up = 0

    # 计算跌停环比百分比变化
    if previous_limit_down_total != 0:
        percentage_change_limit_down = (limit_down_change / previous_limit_down_total) * 100
    else:
        percentage_change_limit_down = 0


    # 显示合并后的涨停和跌停数量
    col1, col2, col3 = st.columns(3)
    col1.metric("上交易日涨跌停数", f"{previous_total} : {previous_limit_down_total}")
    col2.metric("选定日期涨跌停数", f"{selected_total} : {selected_limit_down_total}")
    col3.metric("涨停变化  ：  跌停变化", f"{change:+d} : {limit_down_change:+d}")


    # Display concept changes
    st.subheader("涨停概念变化")
    st.dataframe(sorted_concepts)

    # Create a bar chart for top 10 concepts
    top_10_concepts = sorted_concepts.head(10)


    # Display continuous limit-up analysis
    st.subheader("连续涨停天数分析")
    st.dataframe(selected_continuous)

    st.subheader("连板晋级率分析")
    promotion_rates = calculate_promotion_rates(selected_df, previous_df, selected_date, previous_date)

    # 将DataFrame转换为字典列表
    promotion_list = promotion_rates.to_dict('records')

    if not promotion_rates.empty:
        for _, row in promotion_rates.iterrows():
            if row['总案例数'] == 0:
                continue

            with st.expander(f"{row['连板层级']} ▪ 晋级率 {row['晋级率']}", expanded=True):
                # 进度条
                progress = row['成功案例'].shape[0] / row['总案例数'] if row['总案例数'] > 0 else 0
                st.markdown(f"""
                   <div class="progress">
                       <div class="progress-bar" style="width: {progress * 100}%"></div>
                   </div>
                   <div style="text-align: right; color: #666; margin: 0.5rem 0;">
                       成功率: {progress:.0%}
                   </div>
                   """, unsafe_allow_html=True)

                # 合并展示案例
                all_cases = []
                # 处理成功案例
                if not row['成功案例'].empty:
                    for _, s in row['成功案例'].iterrows():
                        all_cases.append({
                            '股票': s['股票简称'],
                            '代码': s['股票代码'],
                            '涨停原因': s.get('涨停原因', '未知'),
                            '状态': '成功'
                        })
                # 处理失败案例
                if not row['失败案例'].empty:
                    for _, f in row['失败案例'].iterrows():
                        all_cases.append({
                            '股票': f['股票简称'],
                            '代码': f['股票代码'],
                            '涨停原因': f.get('涨停原因', '未知'),
                            '状态': '失败'
                        })

                # 按状态排序：成功在前
                all_cases = sorted(all_cases, key=lambda x: x['状态'], reverse=True)

                # 统一展示
                for case in all_cases:
                    cls = "success" if case['状态'] == '成功' else 'fail'
                    st.markdown(f"""
                       <div class="stock-card {cls}">
                           <div style="display: flex; justify-content: space-between; align-items: center;">
                               <div style="font-weight: 500;">{case['股票']}</div>
                               <div style="color: #666;">{case['代码']}</div>
                               <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;"
                                    title="{case['涨停原因']}">{case['涨停原因']}</div>
                           </div>
                       </div>
                       """, unsafe_allow_html=True)
    else:
        st.info("当日无连板数据")




if __name__ == "__main__":
    st.set_page_config(layout="wide")
    app()

