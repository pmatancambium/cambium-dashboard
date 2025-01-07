import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import holidays
import calendar
from utils.ui_components import (
    setup_page_config,
    add_custom_css,
    init_session_state,
    check_authentication,
    redirect_page,
)


def get_required_hours(date, il_holidays):
    """Determine required work hours based on day and holiday status"""
    date_str = date.strftime("%Y-%m-%d")
    weekday = date.weekday()

    # Check if it's a holiday
    if date_str in il_holidays:
        return 0

    # Friday (4) and Saturday (5) - no work
    if weekday in {4, 5}:
        return 0

    # Check if it's a holiday eve
    next_day = date + timedelta(days=1)
    next_day_str = next_day.strftime("%Y-%m-%d")
    if next_day_str in il_holidays:
        return 7.5

    # Regular workday hours
    # Thursday (3)
    if weekday == 3:
        return 8

    # Sunday (6) to Wednesday (2)
    return 8.5


@st.cache_data(ttl=3600)
def get_israeli_holidays(year):
    """Fetch and cache Israeli holidays for a given year"""
    try:
        # Get both gregorian years that overlap with the Jewish year
        il_holidays = holidays.IL(years=year)

        # Convert to dictionary format with date strings as keys
        holiday_dict = {
            date.strftime("%Y-%m-%d"): name for date, name in il_holidays.items()
        }

        return holiday_dict
    except Exception as e:
        st.error(f"Failed to fetch holidays: {str(e)}")
        return {}


# Enhanced page config
st.set_page_config(
    page_title="TimeCamp Dashboard", layout="wide", initial_sidebar_state="expanded"
)

# Enhanced CSS with new metrics styling and animations
st.markdown(
    """
<style>
    .reportview-container {
        background-color: #f0f2f6;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .metric-container:hover {
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1f2937;
    }
    .metric-label {
        font-size: 14px;
        color: #6b7280;
    }
    .metric-target {
        font-size: 12px;
        color: #9ca3af;
    }
    .status-ok {
        color: #10b981;
    }
    .status-warning {
        color: #f59e0b;
    }
    .status-exceeded {
        color: #ef4444;
    }
    .holiday-list {
        background-color: #f3f4f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .holiday-item {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        border-bottom: 1px solid #e5e7eb;
    }
    .holiday-date {
        font-weight: 500;
        margin-right: 1rem;
    }
    .progress-bar-container {
        width: 100%;
        height: 4px;
        background-color: #e5e7eb;
        border-radius: 2px;
        margin-top: 0.5rem;
    }
    .progress-bar {
        height: 100%;
        border-radius: 2px;
        transition: width 0.3s ease;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_work_hours_and_tasks(api_key, date):
    """Enhanced version with better error handling and task aggregation"""
    url = "https://app.timecamp.com/third_party/api/entries"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    params = {
        "from": date.strftime("%Y-%m-%d"),
        "to": date.strftime("%Y-%m-%d"),
        "user_ids": "me",
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        entries = response.json()

        # Calculate total duration and handle potential overflow
        total_seconds = sum(int(entry["duration"]) for entry in entries)
        hours = min(total_seconds / 3600, 11.5)  # Cap at 11.5 hours like the extension

        # Aggregate tasks with durations
        tasks_with_duration = {}
        for entry in entries:
            task_name = entry["name"] or "Unnamed Task"
            duration = int(entry["duration"]) / 3600
            tasks_with_duration[task_name] = (
                tasks_with_duration.get(task_name, 0) + duration
            )

        return hours, tasks_with_duration

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None, {}


def process_timecamp_data(data, holidays_data, year, month):
    """Enhanced data processing with running balance and status tracking"""
    MAX_DAILY_HOURS = 11.5
    results = []
    running_balance = 0

    for entry in data:
        date = datetime.strptime(entry["date"], "%Y-%m-%d")
        required_hours = get_required_hours(date, holidays_data)
        actual_hours = min(entry["hours"], MAX_DAILY_HOURS)

        daily_difference = actual_hours - required_hours
        running_balance += daily_difference

        status = "OK"
        if entry["hours"] > MAX_DAILY_HOURS:
            status = "Exceeded"
        elif running_balance < 0:
            status = "Warning"

        results.append(
            {
                "date": entry["date"],
                "hours": actual_hours,
                "original_hours": entry["hours"],
                "required_hours": required_hours,
                "daily_difference": daily_difference,
                "running_balance": running_balance,
                "status": status,
                "tasks": entry["tasks"],
                "exceeded_limit": entry["hours"] > MAX_DAILY_HOURS,
                "hours_over_limit": max(0, entry["hours"] - MAX_DAILY_HOURS),
            }
        )

    return pd.DataFrame(results)


def display_metrics(df):
    """Enhanced metrics display with visual indicators"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_hours = df["hours"].sum()
        total_required = df["required_hours"].sum()
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-value">{total_hours:.1f}</div>
                <div class="metric-label">Total Hours</div>
                <div class="metric-target">Target: {total_required:.1f}</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {min(100, (total_hours/total_required)*100)}%;
                         background-color: {'#10b981' if total_hours >= total_required else '#f59e0b'};">
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        final_balance = df["running_balance"].iloc[-1]
        balance_color = "#10b981" if final_balance >= 0 else "#ef4444"
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-value" style="color: {balance_color}">
                    {final_balance:+.1f}
                </div>
                <div class="metric-label">Running Balance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        warning_days = len(df[df["status"] == "Warning"])
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-value">{warning_days}</div>
                <div class="metric-label">Warning Days</div>
                <div class="metric-target">
                    {(warning_days/len(df)*100):.1f}% of total days
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        avg_hours = df["hours"].mean()
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-value">{avg_hours:.1f}</div>
                <div class="metric-label">Average Hours/Day</div>
                <div class="metric-target">Target: 8.5</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def create_hours_chart(df):
    """Enhanced hours visualization with better interactivity"""
    fig = go.Figure()

    # Add actual hours bars
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["hours"],
            name="Actual Hours",
            marker_color=[
                (
                    "#10b981"
                    if status == "OK"
                    else "#f59e0b" if status == "Warning" else "#ef4444"
                )
                for status in df["status"]
            ],
            hovertemplate="<b>%{x}</b><br>"
            + "Hours: %{y:.1f}<br>"
            + "Required: %{customdata[0]:.1f}<br>"
            + "Balance: %{customdata[1]:+.1f}<br>"
            + "Status: %{customdata[2]}<extra></extra>",
            customdata=list(
                zip(df["required_hours"], df["running_balance"], df["status"])
            ),
        )
    )

    # Add required hours line
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["required_hours"],
            name="Required Hours",
            line=dict(color="rgba(0,0,0,0.5)", dash="dash"),
            hoverinfo="skip",
        )
    )

    # Update layout
    fig.update_layout(
        title="Daily Work Hours",
        xaxis_title="Date",
        yaxis_title="Hours",
        hovermode="x unified",
        showlegend=True,
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return fig


def main():

    init_session_state()

    if not check_authentication():
        st.warning("Please log in to access this page.")
        # redirect to home page
        redirect_page()
        # st.stop()

    # Initialize session state if needed
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "last_fetch_data" not in st.session_state:
        st.session_state.last_fetch_data = None
    if "last_fetch_time" not in st.session_state:
        st.session_state.last_fetch_time = None

    st.title("TimeCamp Dashboard")

    # Sidebar configuration
    with st.sidebar:
        st.header("Settings")

        # API Key input with toggle visibility
        api_key = st.text_input(
            "TimeCamp API Key",
            type=(
                "password"
                if "hide_api_key" not in st.session_state
                or st.session_state.hide_api_key
                else "default"
            ),
            value=st.session_state.api_key if st.session_state.api_key else "",
        )

        # Date selection
        current_year = datetime.now().year
        current_month = datetime.now().month

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            year = st.selectbox(
                "Year",
                range(current_year - 2, current_year + 3),
                index=2,
            )
        with date_col2:
            month = st.selectbox(
                "Month",
                range(1, 13),
                index=current_month - 1,
                format_func=lambda x: calendar.month_name[x],
            )

        # Quick date buttons
        quick_col1, quick_col2 = st.columns(2)
        with quick_col1:
            if st.button("This Month", use_container_width=True):
                year = current_year
                month = current_month
        with quick_col2:
            if st.button("Last Month", use_container_width=True):
                if current_month == 1:
                    year = current_year - 1
                    month = 12
                else:
                    year = current_year
                    month = current_month - 1

        # Fetch button
        if st.button("Fetch Data", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please enter your TimeCamp API key")
            else:
                st.session_state.api_key = api_key
                with st.spinner("Fetching data..."):
                    try:
                        # Fetch and process data
                        first_day = datetime(year, month, 1)
                        if (
                            year == datetime.now().year
                            and month == datetime.now().month
                        ):
                            last_day = datetime.now()
                        else:
                            if month == 12:
                                next_month = datetime(year + 1, 1, 1)
                            else:
                                next_month = datetime(year, month + 1, 1)
                            last_day = next_month - timedelta(days=1)

                        date_range = [
                            first_day + timedelta(days=i)
                            for i in range((last_day - first_day).days + 1)
                        ]

                        # Get holidays
                        il_holidays = get_israeli_holidays(year)

                        # Collect all data
                        results = []
                        for date in date_range:
                            required_hours = get_required_hours(date, il_holidays)
                            if required_hours > 0:  # Only fetch if work is required
                                hours, tasks_dict = get_work_hours_and_tasks(
                                    api_key, date
                                )
                                if hours is not None:  # Check if fetch was successful
                                    results.append(
                                        {
                                            "date": date.strftime("%Y-%m-%d"),
                                            "hours": hours,
                                            "tasks": tasks_dict,
                                            "required_hours": required_hours,
                                        }
                                    )

                        if results:
                            # Process the data
                            df = process_timecamp_data(
                                results, il_holidays, year, month
                            )
                            st.session_state.last_fetch_data = df
                            st.session_state.last_fetch_time = datetime.now()
                            st.success("Data fetched successfully!")
                        else:
                            st.error("No data found for the selected period")

                    except Exception as e:
                        st.error(f"Error fetching data: {str(e)}")

        # Show last fetch time if available
        if st.session_state.last_fetch_time:
            st.caption(
                f"Last updated: {st.session_state.last_fetch_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    # Main content area
    if st.session_state.last_fetch_data is not None:
        df = st.session_state.last_fetch_data

        # Display holidays if available
        holidays_df = df[df["required_hours"] == 0].copy()
        if not holidays_df.empty:
            with st.expander("Holidays and Non-Working Days", expanded=False):
                for _, row in holidays_df.iterrows():
                    st.markdown(f"🗓️ **{row['date']}**: Non-working day")

        # Display metrics
        display_metrics(df)

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["Hours Overview", "Task Analysis", "Detailed Log"])

        with tab1:
            # Hours chart
            st.plotly_chart(create_hours_chart(df), use_container_width=True)

            # Running balance chart
            fig_balance = go.Figure()
            fig_balance.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["running_balance"],
                    mode="lines+markers",
                    name="Running Balance",
                    line=dict(
                        color=(
                            "#10b981"
                            if df["running_balance"].iloc[-1] >= 0
                            else "#ef4444"
                        )
                    ),
                    hovertemplate="<b>%{x}</b><br>Balance: %{y:+.1f} hours<extra></extra>",
                )
            )
            fig_balance.update_layout(
                title="Running Balance Over Time",
                xaxis_title="Date",
                yaxis_title="Hours",
                hovermode="x unified",
                height=300,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_balance, use_container_width=True)

        with tab2:
            # Aggregate tasks across all days
            all_tasks = {}
            for idx, row in df.iterrows():
                for task, duration in row["tasks"].items():
                    all_tasks[task] = all_tasks.get(task, 0) + duration

            if all_tasks:
                # Create task distribution pie chart
                fig_tasks = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(all_tasks.keys()),
                            values=list(all_tasks.values()),
                            hole=0.4,
                            hovertemplate="<b>%{label}</b><br>%{value:.1f} hours<br>%{percent}<extra></extra>",
                        )
                    ]
                )
                fig_tasks.update_layout(
                    title="Task Distribution",
                    height=400,
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                st.plotly_chart(fig_tasks, use_container_width=True)

                # Task breakdown table
                st.subheader("Task Breakdown")
                task_df = pd.DataFrame(
                    [
                        {
                            "Task": task,
                            "Hours": hours,
                            "Percentage": (hours / sum(all_tasks.values())) * 100,
                        }
                        for task, hours in all_tasks.items()
                    ]
                ).sort_values("Hours", ascending=False)

                st.dataframe(
                    task_df.style.format({"Hours": "{:.1f}", "Percentage": "{:.1f}%"}),
                    hide_index=True,
                    use_container_width=True,
                )

        with tab3:
            # Detailed daily log
            st.subheader("Daily Time Log")

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=["OK", "Warning", "Exceeded"],
                    default=["OK", "Warning", "Exceeded"],
                )
            with col2:
                min_hours = st.slider(
                    "Minimum Hours", min_value=0.0, max_value=12.0, value=0.0, step=0.5
                )

            # Apply filters
            filtered_df = df[
                (df["status"].isin(status_filter)) & (df["hours"] >= min_hours)
            ].copy()

            # Prepare data for table display
            table_data = []
            for _, row in filtered_df.iterrows():
                date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
                table_data.append(
                    {
                        "Date": row["date"],
                        "Day": date_obj.strftime("%a"),
                        "Hours": row["hours"],
                        "Required": row["required_hours"],
                        "Difference": row["daily_difference"],
                        "Balance": row["running_balance"],
                        "Status": row["status"],
                        "Tasks": (
                            ", ".join(
                                f"{task} ({duration:.1f}h)"
                                for task, duration in row["tasks"].items()
                            )
                            if row["tasks"]
                            else ""
                        ),
                        "View": f"https://app.timecamp.com/app#/timesheets/timer/{row['date']}",
                    }
                )

            if table_data:
                table_df = pd.DataFrame(table_data)

                # Define style function for background colors
                def color_status(val):
                    if val == "Warning":
                        return "background-color: #fef9c3"
                    elif val == "Exceeded":
                        return "background-color: #fee2e2"
                    elif val == "OK":
                        return "background-color: #dcfce7"
                    return ""

                # Apply styling
                styled_df = table_df.style.apply(
                    lambda x: [color_status(v) for v in x], subset=["Status"]
                ).format(
                    {
                        "Hours": "{:.2f}",
                        "Required": "{:.2f}",
                        "Difference": "{:+.2f}",
                        "Balance": "{:+.2f}",
                    }
                )

                # Add custom CSS for the table
                st.markdown(
                    """
                <style>
                    .stDataFrame {
                        font-size: 14px;
                    }
                    .stDataFrame td {
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        max-width: 150px;
                    }
                    .stDataFrame td a {
                        color: #1a56db;
                        text-decoration: none;
                    }
                    .stDataFrame td a:hover {
                        text-decoration: underline;
                    }
                </style>
                """,
                    unsafe_allow_html=True,
                )

                # Display the table
                st.dataframe(
                    styled_df,
                    column_config={
                        "Date": st.column_config.DateColumn(
                            "Date",
                            width="medium",
                        ),
                        "Day": st.column_config.TextColumn(
                            "Day",
                            width="small",
                        ),
                        "Hours": st.column_config.NumberColumn(
                            "Hours",
                            format="%.2f",
                            width="small",
                        ),
                        "Required": st.column_config.NumberColumn(
                            "Required",
                            format="%.2f",
                            width="small",
                        ),
                        "Difference": st.column_config.NumberColumn(
                            "Diff",
                            format="%+.2f",
                            width="small",
                        ),
                        "Balance": st.column_config.NumberColumn(
                            "Balance",
                            format="%+.2f",
                            width="small",
                        ),
                        "Status": st.column_config.TextColumn(
                            "Status",
                            width="small",
                        ),
                        "Tasks": st.column_config.TextColumn(
                            "Tasks",
                            width="large",
                        ),
                        "View": st.column_config.LinkColumn(
                            "View",
                            width="small",
                            display_text="View",
                        ),
                    },
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No data matching the selected filters")

    else:
        # Show instructions for first-time users
        st.info(
            """
        👋 Welcome to the TimeCamp Dashboard!

        To get started:
        1. Enter your TimeCamp API key in the sidebar
        2. Select the year and month you want to analyze
        3. Click 'Fetch Data' to load your time entries

        Need help finding your API key?
        - Log in to TimeCamp
        - Go to your User Settings
        - Look for the 'API' section
        """
        )


if __name__ == "__main__":
    main()
