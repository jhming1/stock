#!/user/bin/env python3
# -*- coding: utf-8 -*-

# 利用akshare获取实时板块资金流向热力图
#需在CMD中用‘E:\AKShare_test\.venv\Scripts\streamlit.exe run E:\AKShare_test\ZJLX.py’来运行
import streamlit as st
import akshare as ak
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta


# 缓存数据获取函数（减少重复请求）
@st.cache_data(ttl=3600)
def get_board_data():
    board_df = ak.stock_board_industry_name_em()

    data_list = []
    for index, row in board_df.iterrows():
        try:
            df = ak.stock_board_industry_hist_em(
                symbol=row["板块名称"],
                start_date=(datetime.now() - timedelta(days=1)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust=""
            )
            latest = df.iloc[-1].to_dict()
            latest["板块名称"] = row["板块名称"]
            data_list.append(latest)
        except Exception as e:
            continue

    return pd.DataFrame(data_list)


# 数据处理函数
def process_data(df):
    numeric_cols = ['开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '换手率']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    df['量价强度'] = df['涨跌幅'] * df['换手率']
    df['成交额（亿）'] = df['成交额'] / 1e8
    df['成交量（万手）'] = df['成交量'] / 10000
    df['涨跌幅'] = df['涨跌幅']   # 确保为百分比值

    return df.dropna(subset=['涨跌幅'])


# 主程序
def main():
    st.set_page_config(
        page_title="板块资金热力图",
        page_icon="  ",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("   实时板块资金流向热力图")
    st.markdown("""
    **数据说明：**
    - 颜色映射：绿色表示下跌，红色表示上涨
    - 数据更新：{} 
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")))

    # 侧边栏控件
    with st.sidebar:
        st.header("参数设置")
        color_metric = st.selectbox(
            "颜色指标",
            options=['涨跌幅', '换手率', '量价强度'],
            index=0
        )
        size_metric = st.selectbox(
            "板块大小指标",
            options=['成交额（亿）', '成交量（万手）', '换手率'],
            index=0
        )
        date_range = st.slider(
            "回溯天数",
            min_value=1,
            max_value=30,
            value=7
        )
        color_scale = st.selectbox(
            "配色方案",
            options=['RdYlGn_r', 'BrBG_r', 'PiYG_r', 'RdBu_r'],  # 全部使用反转色阶
            index=0
        )

    # 数据加载
    with st.spinner('正在获取最新行情数据...'):
        raw_df = get_board_data()
        processed_df = process_data(raw_df)

    # 数据过滤
    filtered_df = processed_df[
        processed_df['日期'] >= (datetime.now() - timedelta(days=date_range)).strftime("%Y-%m-%d")
        ]

    # 创建可视化
    fig = px.treemap(
        filtered_df,
        path=['板块名称'],
        values=size_metric,
        color=color_metric,
        color_continuous_scale=color_scale,
        range_color=[filtered_df[color_metric].min(), filtered_df[color_metric].max()],
        hover_data={
            '涨跌幅': ':.2f%',
            '换手率': ':.2f%',
            '成交额（亿）': ':.2f',
            '量价强度': ':.2f'
        },
        height=800
    )

    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        coloraxis_colorbar=dict(
            title=dict(  # 修改此处结构
                text=color_metric + (" (%)" if color_metric == "涨跌幅" else ""),
                side="right"  # 位置参数放在 title 对象中
            ),
            tickformat="+.1%" if color_metric == "涨跌幅" else ".1f",
            thickness=15
        )
    )

    fig.update_traces(
        texttemplate='%{label} %{customdata[0]: .2f} % ',
    hovertemplate = ('<b>%{label}</b>'
        f'{color_metric}: %{{color:.2f}}{"%" if color_metric == "涨跌幅" else ""}'
        '换手率: %{customdata[1]:.2f}%'
        '成交额: %{customdata[2]:.2f}亿'
    )
    )

    st.plotly_chart(fig, use_container_width=True)

    # 数据表格
    with st.expander("查看原始数据"):
        st.dataframe(
            filtered_df.sort_values(by='涨跌幅', ascending=False),
            column_config={
                "日期": "日期",
                "板块名称": st.column_config.TextColumn(),
                "涨跌幅": st.column_config.NumberColumn(format="▁%.2f%%",
                                                        help="颜色映射："),
                "换手率": st.column_config.NumberColumn(format="%.2f%%"),
                "成交额（亿）": st.column_config.NumberColumn(format="%.1f 亿")
            },
            height=300,
            hide_index=True
        )


if __name__ == "__main__":
    main()

