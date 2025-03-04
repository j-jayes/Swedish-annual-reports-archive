import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def main():
    st.title("Swedish Firms Financial Explorer")

    # 1. Read the Excel data
    df = pd.read_excel("data/company_reports_smoothed_output.xlsx")

    # 2. Identify which columns end in "_smoothed"
    smoothed_cols = [col for col in df.columns if col.endswith("_smoothed")]

    # 3. Sidebar: Pick companies
    st.sidebar.header("Select Companies")
    all_companies = sorted(df["company_name"].unique())
    selected_companies = st.sidebar.multiselect(
        label="Choose one or more companies:",
        options=all_companies,
        default=all_companies[:3],  # Just a sample default
    )

    # 4. Sidebar: Pick smoothed variables to plot on the first page
    st.sidebar.header("Select Smoothed Variables")
    selected_vars = st.sidebar.multiselect(
        label="Choose smoothed variables:",
        options=smoothed_cols,
        default=["revenue_smoothed"],  # Default to just "revenue_smoothed"
    )

    # If no companies chosen, show a quick note
    if not selected_companies:
        st.warning("Please select at least one company to see the plots.")
        return

    # Filter data to only chosen companies
    df_filtered = df[df["company_name"].isin(selected_companies)].copy()
    df_filtered.sort_values(by=["fiscal_year"], inplace=True)

    # 5. Create tabs (two "sheets"): 
    tab1, tab2 = st.tabs(["Compare Smoothed Variables", "Custom Ratio"])

    # ------------------
    # TAB 1: Compare any smoothed variables over time
    # ------------------
    with tab1:
        st.subheader("Compare Selected Smoothed Variables Over Time")

        if selected_vars:
            for var in selected_vars:
                fig, ax = plt.subplots()
                for company in selected_companies:
                    subset = df_filtered[df_filtered["company_name"] == company]
                    ax.plot(
                        subset["fiscal_year"],
                        subset[var],
                        marker='o',
                        label=company
                    )
                ax.set_title(f"{var} Over Time")
                ax.set_xlabel("Fiscal Year")
                ax.set_ylabel(var)
                ax.legend()
                st.pyplot(fig)
        else:
            st.write("No smoothed variables selected.")

    # ------------------
    # TAB 2: Custom Ratio (e.g., revenue_smoothed / number_of_employees)
    # ------------------
    with tab2:
        st.subheader("Create a Custom Ratio and Plot Over Time")

        # Let user choose numerator and denominator from ALL columns or just smoothed ones
        # If you only want to use smoothed columns plus employees, you can adjust accordingly.
        columns_for_ratio = [col for col in df.columns if col not in ["fiscal_year", "company_name"]]
        
        st.markdown("Select any two variables to form a ratio: (numerator ÷ denominator).")
        numerator = st.selectbox(
            "Numerator (default = revenue_smoothed):",
            options=columns_for_ratio,
            index=columns_for_ratio.index("revenue_smoothed") if "revenue_smoothed" in columns_for_ratio else 0
        )
        denominator = st.selectbox(
            "Denominator (default = n_employees_smoothed):",
            options=columns_for_ratio,
            index=columns_for_ratio.index("n_employees_smoothed") if "n_employees_smoothed" in columns_for_ratio else 0
        )

        # Compute the ratio
        df_filtered["custom_ratio"] = df_filtered[numerator] / df_filtered[denominator]

        # Plot the ratio for each company
        fig_ratio, ax_ratio = plt.subplots()
        for company in selected_companies:
            subset = df_filtered[df_filtered["company_name"] == company]
            ax_ratio.plot(
                subset["fiscal_year"],
                subset["custom_ratio"],
                marker='o',
                label=company
            )
        ax_ratio.set_title(f"{numerator} ÷ {denominator}")
        ax_ratio.set_xlabel("Fiscal Year")
        ax_ratio.set_ylabel("Ratio Value")
        ax_ratio.legend()

        st.pyplot(fig_ratio)

if __name__ == "__main__":
    main()
